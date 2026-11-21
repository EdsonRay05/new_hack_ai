"""Live provider regression: the reported tangent problem with the new schema."""
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from pipeline import generate_lesson, render_with_repair, user_error

problem = 'Find the slope and equation of the tangent line to f(x) = 15 - 2x² at x = 1. Show why the line is tangent.'
job_id = 'visual-regression-' + uuid.uuid4().hex[:10]
try:
    lesson = generate_lesson(problem, 'derivative_tangent', [])
    result = render_with_repair(lesson, problem, job_id,
                              lambda state, message: print(state, message, flush=True))
    destination = ROOT / 'media' / job_id / 'result.json'
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: result[key] for key in ['problem_title', 'final_answer', 'video_url', 'duration', 'repairs']}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({'error_type': type(exc).__name__, 'message': user_error(exc)}))
    raise SystemExit(1)
