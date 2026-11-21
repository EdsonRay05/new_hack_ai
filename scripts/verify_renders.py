"""Render all five known examples and cache their verified MP4s for offline demos."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from renderer import probe_video, render_scene
from samples import SAMPLES, verify_sample_math

verify_sample_math()
report = {}
for category in SAMPLES:
    code = (ROOT / 'templates' / f'{category}.py').read_text(encoding='utf-8')
    cached = ROOT / 'static' / 'outputs' / f'sample-{category}.mp4'
    marker = cached.with_suffix('.source.py')
    if '--reuse-existing' in sys.argv and cached.exists() and marker.exists() and marker.read_text(encoding='utf-8') == code:
        report[category] = {'video_url': f'/static/outputs/{cached.name}', **probe_video(cached)}
    else:
        report[category] = render_scene(code, f'sample-{category}')
        marker.write_text(report[category]['code'], encoding='utf-8')
    report[category].pop('code', None)
    print(category, json.dumps(report[category]), flush=True)
(ROOT / 'media' / 'render-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
