"""Re-render a saved lesson locally, without spending AI requests."""
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import render_with_repair

if len(sys.argv) != 2:
    raise SystemExit('Usage: python scripts/recover_lesson.py media/<job-id>/lesson.json')
lesson = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
job_id = 'recovered-' + uuid.uuid4().hex[:12]
result = render_with_repair(lesson, lesson.get('learning_question', ''), job_id,
                          lambda state, message: print(state, message, flush=True), allow_repair=False)
(ROOT / 'media' / job_id / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({key: result[key] for key in ['video_url', 'duration', 'width', 'height', 'repairs', 'timing_adjusted']}))
