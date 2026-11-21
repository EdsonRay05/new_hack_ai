import asyncio
from contextlib import asynccontextmanager
import importlib.metadata
import io
import logging
import os
from pathlib import Path
import shutil
import time
import uuid
import warnings

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from prompts import Category
from samples import SAMPLES, verify_sample_math
from providers import provider, provider_label, key_variable, active_model

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
log = logging.getLogger('intuitionlens')
MAX_IMAGE = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000
jobs: dict[str, dict] = {}
tasks: set[asyncio.Task] = set()
queue_limit = asyncio.Semaphore(1)
analysis_limit = asyncio.Semaphore(1)


@asynccontextmanager
async def lifespan(app):
    verify_sample_math()
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title='IntuitionLens', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.middleware('http')
async def local_only(request: Request, call_next):
    # Host/origin checks reduce browser-driven access to a localhost execution service.
    host = request.headers.get('host', '').split(':')[0].lower()
    if host not in {'127.0.0.1', 'localhost', 'testserver'}:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'This application is for localhost use only.'}, status_code=403)
    if request.method == 'POST':
        origin = request.headers.get('origin')
        if origin and origin not in {f'http://{request.headers.get("host")}', f'https://{request.headers.get("host")}'}:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Cross-origin requests are not permitted.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health')
def health():
    try:
        manim = importlib.metadata.version('manim')
    except importlib.metadata.PackageNotFoundError:
        manim = None
    return {'api_key_configured': bool(os.getenv(key_variable(), '').strip()),
            'provider': provider(), 'provider_label': provider_label(),
            'model': active_model(), 'vision_model': active_model(vision=True),
            'manim': manim, 'ffmpeg': bool(shutil.which('ffmpeg')),
            'ffprobe': bool(shutil.which('ffprobe')),
            'execution_mode': 'personal localhost; code validation is not a sandbox'}


@app.get('/api/samples')
def samples():
    return [{'id': key, **{k: v for k, v in lesson.items() if k in {'title', 'problem_title', 'problem', 'learning_question'}}}
            for key, lesson in SAMPLES.items()]


def normalize_image(data: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('Use a JPEG, PNG, or WebP image.')
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((1024, 1024))
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=85)
                return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('The image is unreadable or too large in pixel dimensions.') from exc


@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...)):
    from pipeline import analyze_image, user_error
    data = await file.read(MAX_IMAGE + 1)
    await file.close()
    if len(data) > MAX_IMAGE:
        raise HTTPException(413, 'Image must be 10 MB or smaller.')
    try:
        image = await asyncio.to_thread(normalize_image, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if analysis_limit.locked():
        raise HTTPException(429, 'A problem is already being read. Please wait.')
    try:
        async with analysis_limit:
            return await asyncio.to_thread(analyze_image, image)
    except Exception as exc:
        log.warning('analysis failed type=%s', type(exc).__name__)
        raise HTTPException(503, user_error(exc)) from exc


class GenerateRequest(BaseModel):
    problem: str = Field(min_length=5, max_length=5000)
    category: Category = 'general'
    assumptions: list[str] = Field(default_factory=list, max_length=8)


def new_job(mode: str, problem: str) -> str:
    now = time.time()
    for key in list(jobs):
        if now - jobs[key]['created'] > 3600 and jobs[key]['status'] in {'complete', 'error'}:
            del jobs[key]
    if sum(j['status'] not in {'complete', 'error'} for j in jobs.values()) >= 4:
        raise HTTPException(429, 'The render queue is full. Please wait for a job to finish.')
    job_id = uuid.uuid4().hex
    jobs[job_id] = {'id': job_id, 'created': now, 'status': 'queued', 'message': 'Waiting for the renderer.',
                    'mode': mode, 'problem': problem, 'events': []}
    return job_id


def schedule(coro):
    task = asyncio.create_task(coro)
    tasks.add(task)
    task.add_done_callback(tasks.discard)


async def execute_job(job_id: str, request: GenerateRequest | None = None, sample_id: str | None = None):
    from pipeline import generate_lesson, render_with_repair, user_error
    loop = asyncio.get_running_loop()

    def apply_update(status, message):
        jobs[job_id].update(status=status, message=message)
        jobs[job_id]['events'].append({'status': status, 'message': message})

    def update(status, message):
        loop.call_soon_threadsafe(apply_update, status, message)

    try:
        async with queue_limit:
            if sample_id:
                lesson = dict(SAMPLES[sample_id])
                lesson['code'] = (ROOT / 'templates' / f'{sample_id}.py').read_text(encoding='utf-8')
                lesson['manim_code'] = lesson['code']
                cached = ROOT / 'static' / 'outputs' / f'sample-{sample_id}.mp4'
                source_marker = cached.with_suffix('.source.py')
                if cached.exists() and source_marker.exists() and source_marker.read_text(encoding='utf-8') == lesson['code']:
                    from renderer import probe_video
                    video = await asyncio.to_thread(probe_video, cached)
                    result = {**lesson, **video, 'video_url': f'/static/outputs/{cached.name}', 'repairs': 0}
                else:
                    result = await asyncio.to_thread(render_with_repair, lesson, lesson['problem'], job_id, update, False)
                    shutil.copy2(ROOT / 'static' / 'outputs' / f'{job_id}.mp4', cached)
                    source_marker.write_text(result['manim_code'], encoding='utf-8')
                result['verification'] = 'Known sample: scalar calculations checked independently. Visual review is still recommended.'
            else:
                apply_update('generating', 'Creating a scene for your reviewed problem.')
                lesson = await asyncio.to_thread(generate_lesson, request.problem, request.category, request.assumptions, update)
                result = await asyncio.to_thread(render_with_repair, lesson, request.problem, job_id, update)
                result['verification'] = 'AI-generated lesson: rendering was checked; mathematical correctness has not been independently verified.'
            jobs[job_id]['result'] = result
            apply_update('complete', 'Your animation is ready.')
    except Exception as exc:
        log.warning('job=%s failed type=%s', job_id, type(exc).__name__)
        apply_update('error', user_error(exc))


@app.post('/api/generate', status_code=202)
async def generate(request: GenerateRequest):
    if not os.getenv(key_variable(), '').strip():
        raise HTTPException(503, f'Add {key_variable()} to .env and restart, or try a sample without a key.')
    job_id = new_job('custom', request.problem)
    schedule(execute_job(job_id, request=request))
    return {'job_id': job_id}


@app.post('/api/samples/{sample_id}', status_code=202)
async def generate_sample(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(404, 'Sample not found.')
    job_id = new_job('sample', SAMPLES[sample_id]['problem'])
    schedule(execute_job(job_id, sample_id=sample_id))
    return {'job_id': job_id}


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, 'Job not found. Jobs are cleared when the server restarts.')
    return jobs[job_id]
