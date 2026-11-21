"""Render templates without movie output and check every created Text's bounds."""
import importlib.util
import ast
import json
import re
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from manim import Text, tempconfig

original_init = Text.__init__
report = {}
for path in (ROOT / 'templates').glob('*.py'):
    texts = []

    def track(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        texts.append(self)

    with tempconfig({'dry_run': True, 'skip_animations': True, 'verbosity': 'ERROR',
                     'media_dir': str(ROOT / 'media' / 'layout-check')}), patch.object(Text, '__init__', track):
        spec = importlib.util.spec_from_file_location('layout_scene', path)
        module = importlib.util.module_from_spec(spec)
        tree = ast.parse(path.read_text(encoding='utf-8'))
        construct = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'construct')
        # Instrument only trusted reference scripts for QA; production sources
        # remain unchanged and still undergo the normal execution checks.
        construct.body.append(ast.parse('self.layout_objects = {"title": title, "axes": axes, "info_panel": info_panel, "panel_border": panel_border, "info_box": info_box, "axes_group": axes_group, "canvas": canvas, "axis_numbers": axis_numbers, "guides": guides}').body[0])
        exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), module.__dict__)
        scene = module.GeneratedScene(skip_animations=True)
        scene.render()
    failures = []
    objects = scene.layout_objects
    title = objects['title']
    panel = objects['info_panel']
    axes = objects['axes']
    border = objects['panel_border']
    canvas = objects['canvas']
    gap = border.get_left()[0] - axes.get_right()[0]
    if not math.isclose(gap, 0.65, abs_tol=1e-6):
        failures.append({'gap': float(gap), 'expected': 0.65})
    if abs(canvas.get_center()[0]) > 1e-6 or abs(canvas.get_center()[1] + 0.25) > 1e-6:
        failures.append({'canvas_center': canvas.get_center().tolist(), 'expected': [0, -0.25, 0]})
    for number in objects['axis_numbers']:
        if number.text == '0' or not isinstance(number, Text) or abs(number.font_size - 16) > 1e-5:
            failures.append({'tick': 'Numeric ticks must be 16-point Text and omit zero.'})
    guides = objects['guides']
    vertical_end = axes.p2c(guides[0].get_end())
    horizontal_end = axes.p2c(guides[1].get_end())
    if abs(vertical_end[1]) > 1e-6 or abs(horizontal_end[0]) > 1e-6:
        failures.append({'guides': 'Guides do not end on their corresponding axes.'})
    if panel.width > 4.4 or panel.height > 5.2 or panel.get_left()[0] < 0.8 or panel.get_top()[1] > 2.9:
        failures.append({'info_panel': 'Sidebar exceeds its dedicated zone.', 'width': panel.width, 'height': panel.height})
    if border.get_top()[1] >= title.get_bottom()[1] - 0.15:
        failures.append({'overlap': 'Panel border intrudes into the title strip.'})
    if axes.get_right()[0] >= panel.get_left()[0] - 0.5:
        failures.append({'overlap': 'Graph and sidebar lack a clear gutter.'})
    allowed_graph_labels = {'x', 'y', 'x(m)', 'y(m)', 'θ', 'value', '(2,4)'}
    for text in texts:
        compact_text = text.text.replace(' ', '')
        graph_label = compact_text in allowed_graph_labels or re.fullmatch(r'-?\d+(?:\.\d+)?', compact_text)
        left, right = float(text.get_left()[0]), float(text.get_right()[0])
        bottom, top = float(text.get_bottom()[1]), float(text.get_top()[1])
        if left < -6.86 or right > 6.86 or bottom < -3.21 or top > 3.66:
            failures.append({'text': text.text, 'bounds': [left, right, bottom, top]})
        if text is not title and top > 2.9:
            failures.append({'text': text.text, 'overlap': 'Non-title text enters title zone.'})
        if text is not title and not graph_label and left < 0.8:
            failures.append({'text': text.text, 'overlap': 'Equation/readout is outside the right sidebar.'})
        if text is not title and not graph_label:
            if left < border.get_left()[0] or right > border.get_right()[0] or bottom < border.get_bottom()[1] or top > border.get_top()[1]:
                failures.append({'text': text.text, 'overlap': 'Sidebar row escapes the panel border.'})
    report[path.stem] = {'text_objects': len(texts), 'numeric_ticks': len(objects['axis_numbers']),
                         'graph_box_gap': float(gap), 'failures': failures}
print(json.dumps(report, indent=2, ensure_ascii=False))
(ROOT / 'media' / 'layout-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
assert all(not entry['failures'] for entry in report.values()), 'Some labels exceed the safe frame.'
