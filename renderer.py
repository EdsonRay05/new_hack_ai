import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

from validation import validate_code
from timing import retime_scene
from geometry import center_tangent_lines

ROOT = Path(__file__).resolve().parent
log = logging.getLogger('intuitionlens.render')


class RenderError(RuntimeError):
    pass


def render_scene(code: str, job_id: str, attempt: int = 0, _timing_pass: int = 0) -> dict:
    validate_code(code)
    code, geometry_adjusted = center_tangent_lines(code)
    work = ROOT / 'media' / job_id / str(attempt)
    if _timing_pass:
        work = work / 'timing-adjusted'
    work.mkdir(parents=True, exist_ok=True)
    script = work / 'scene.py'
    script.write_text(code, encoding='utf-8')
    # Manim runs without application credentials. This is not an OS sandbox.
    allowed_env = {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
                   'LOCALAPPDATA', 'APPDATA', 'HOME', 'LANG', 'FONTCONFIG_PATH'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed_env}
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    command = [sys.executable, '-m', 'manim', '-ql', '--disable_caching',
               '--media_dir', str(work / 'render'), str(script), 'GeneratedScene']
    log.info('job=%s attempt=%s rendering', job_id, attempt + 1)
    try:
        process = subprocess.run(command, cwd=work, env=env, capture_output=True,
                                 text=True, encoding='utf-8', errors='replace',
                                 timeout=int(os.getenv('RENDER_TIMEOUT', '120')))
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError('Rendering exceeded the time limit. Try a simpler scene.') from exc
    trace = process.stderr + '\n' + process.stdout
    (work / 'render.log').write_text(trace, encoding='utf-8')
    if process.returncode:
        raise RenderError(trace[-14000:])
    videos = list((work / 'render' / 'videos').rglob('GeneratedScene.mp4'))
    if len(videos) != 1:
        raise RenderError('Renderer did not produce exactly one final GeneratedScene.mp4.')
    metadata = probe_video(videos[0])
    (work / 'video-metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    if not 8 <= metadata['duration'] <= 15:
        if not _timing_pass:
            log.info('job=%s duration=%.2fs adjusting pacing locally', job_id, metadata['duration'])
            adjusted = retime_scene(code, metadata['duration'])
            result = render_scene(adjusted, job_id, attempt, _timing_pass=1)
            result['geometry_adjusted'] = result.get('geometry_adjusted', False) or geometry_adjusted
            return result
        raise RenderError(f"Video duration {metadata['duration']:.2f}s is outside the 8-15 second limit. Adjust run_time values.")
    outputs = ROOT / 'static' / 'outputs'
    outputs.mkdir(parents=True, exist_ok=True)
    destination = outputs / f'{job_id}.mp4'
    shutil.copy2(videos[0], destination)
    return {'video_url': f'/static/outputs/{job_id}.mp4', **metadata,
            'code': code, 'timing_adjusted': bool(_timing_pass), 'geometry_adjusted': geometry_adjusted}


def probe_video(path: Path) -> dict:
    ffmpeg = shutil.which('ffmpeg')
    ffprobe = shutil.which('ffprobe')
    if not ffprobe and ffmpeg:
        sibling = Path(ffmpeg).with_name('ffprobe.exe' if os.name == 'nt' else 'ffprobe')
        if sibling.exists():
            ffprobe = str(sibling)
    if not ffprobe:
        raise RuntimeError('FFprobe is required to verify rendered videos. Install the FFmpeg tools.')
    result = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0',
                             '-show_entries', 'stream=width,height,codec_name:format=duration',
                             '-of', 'json', str(path)], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError('The rendered video could not be verified.')
    data = json.loads(result.stdout)
    stream = data['streams'][0]
    if stream['codec_name'] != 'h264':
        raise RenderError('Expected H.264 video for browser playback.')
    return {'duration': float(data['format']['duration']), 'width': stream['width'], 'height': stream['height']}
