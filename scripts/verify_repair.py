"""Exercise a real failing Manim subprocess with a deterministic repair substitute.

This verifies traceback plumbing and subsequent real rendering, not Gemini access.
"""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import render_with_repair

broken = '''from manim import *
class GeneratedScene(Scene):
    def construct(self):
        self.add(Text('Controlled failure', font_size='invalid'))
'''
fixed = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')
tracebacks = []


def repair(code, error, problem):
    assert code == broken
    assert 'Traceback' in error
    tracebacks.append(error)
    return fixed


with patch('pipeline.repair_code', side_effect=repair):
    result = render_with_repair({'code': broken}, 'Derivative of x^2 at x=2', 'repair-integration',
                                lambda state, message: print(state, message, flush=True))
assert result['repairs'] == 1
assert len(tracebacks) == 1
print('Real failure, captured traceback, deterministic repair, and real MP4 verified.', result['video_url'])
