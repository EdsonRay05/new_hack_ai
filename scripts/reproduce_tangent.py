"""Live end-to-end regression for the reported tangent problem; no credentials printed."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')
from pydantic import ValidationError
from pipeline import generate_lesson, render_with_repair, user_error

problem = 'Find the tangent line to f(x) = 15 - 2x^2 at x = 1.'
try:
    lesson = generate_lesson(problem, 'derivative_tangent', [])
    output = ROOT / 'media' / 'tangent-regression'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'lesson.json').write_text(json.dumps(lesson, indent=2), encoding='utf-8')
    result = render_with_repair(lesson, problem, 'tangent-regression',
                               lambda state, message: print(state, message, flush=True))
    print(json.dumps({'success': True, 'title': result['title'], 'steps': result['steps'],
                      'video_url': result['video_url'], 'repairs': result['repairs']}))
except ValidationError as exc:
    print(json.dumps({'success': False, 'type': type(exc).__name__,
                      'fields': [{'location': e['loc'], 'type': e['type']} for e in exc.errors()]}))
    sys.exit(1)
except Exception as exc:
    print(json.dumps({'success': False, 'type': type(exc).__name__, 'message': user_error(exc)}))
    sys.exit(1)
