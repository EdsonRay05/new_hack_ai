import ast
import unittest

from timing import retime_scene
from validation import validate_code

SHORT = '''from manim import *
class GeneratedScene(Scene):
    def construct(self):
        curve = Axes().plot(lambda x: 15 - 2*x**2)
        value = -4
        label = Text(f'Slope = {value:g}')
        self.play(Create(curve), run_time=1)
        self.play(Write(label), run_time=1.5)
        self.wait(1.5)
'''


class TimingTests(unittest.TestCase):
    def test_short_scene_extends_animations_and_preserves_math_and_pause(self):
        fixed = retime_scene(SHORT, 4)
        validate_code(fixed)
        tree = ast.parse(fixed)
        plays = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'play']
        durations = [next(k.value.value for k in p.keywords if k.arg == 'run_time') for p in plays]
        self.assertAlmostEqual(sum(durations) + 1.5, 12)
        self.assertIn('15 - 2 * x ** 2', fixed)
        self.assertIn("Text(f'Slope = {value:g}')", fixed)
        self.assertIn('self.wait(1.5)', fixed)

    def test_long_scene_shortens(self):
        fixed = retime_scene(SHORT, 24)
        self.assertIn('run_time=0.466667', fixed)

    def test_default_play_and_keyword_wait(self):
        code = SHORT.replace('run_time=1)', 'run_time=1)').replace('self.play(Write(label), run_time=1.5)',
            'self.play(Write(label))\n        self.wait(duration=1)')
        fixed = retime_scene(code, 4.5)
        self.assertIn('duration=3.5', fixed)
        self.assertIn('run_time=3.5', fixed)

    def test_invalid_scene_cannot_bypass_validation(self):
        with self.assertRaises(ValueError):
            retime_scene(SHORT.replace("Text(f'Slope = {value:g}')", 'open("secret")'), 4)

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            retime_scene(SHORT, 0)
