import ast
from pathlib import Path
import unittest

from pydantic import ValidationError
from prompts import GeneratedLesson
from samples import SAMPLES
from validation import validate_code
from geometry import center_tangent_lines

ROOT = Path(__file__).resolve().parents[1]


class LessonContractTests(unittest.TestCase):
    def test_tick_helper_is_inspected_and_tex_numbers_are_rejected(self):
        source = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')
        validate_code(source)
        with self.assertRaises(ValueError):
            validate_code(source.replace('numbers = VGroup()', 'numbers = open("secret")'))
        with self.assertRaisesRegex(ValueError, 'include_numbers'):
            validate_code(source.replace("'include_numbers': False", "'include_numbers': True"))
        with self.assertRaises(ValueError):
            validate_code(source.replace('Text(str(val)', 'DecimalNumber(val'))

    def test_timing_and_geometry_find_construct_with_module_helper(self):
        from timing import retime_scene
        source = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')
        fixed = retime_scene(source, 6)
        old_helper = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef))
        new_helper = next(node for node in ast.parse(fixed).body if isinstance(node, ast.FunctionDef))
        self.assertEqual(ast.dump(old_helper), ast.dump(new_helper))
        self.assertIn('self.wait(1.5)', fixed)
        self.assertEqual(center_tangent_lines(source), (source, False))

    def test_long_formula_cannot_be_attached_to_graph(self):
        prefix = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        slope = -4\n        intercept = 17\n        '
        with self.assertRaisesRegex(ValueError, 'info_panel'):
            validate_code(prefix + 'label = Text(f"y = {slope:g}x {intercept:+g}").next_to(tangent_line, UP)')
        with self.assertRaisesRegex(ValueError, 'info_panel'):
            validate_code(prefix + 'label = Text(f"y = {slope:g}x {intercept:+g}")\n        label.next_to(tangent_line, UP)')
        validate_code(prefix + 'x0 = 1\n        y0 = 13\n        label = Text(f"({x0:g}, {y0:g})").next_to(point, DOWN)')

    def test_asymmetric_tangent_is_centered_without_changing_slope(self):
        code = '''from manim import *
class GeneratedScene(Scene):
    def construct(self):
        axes = Axes()
        f = lambda x: 15 - 2*x**2
        point = Dot(axes.c2p(1, f(1)))
        tangent = Line(axes.c2p(-1.5, 23), axes.c2p(2.5, 7))
'''
        fixed, changed = center_tangent_lines(code)
        self.assertTrue(changed)
        self.assertIn('c2p(-0.5, 19.0)', fixed)
        self.assertIn('c2p(2.5, 7.0)', fixed)
        self.assertFalse(center_tangent_lines(fixed)[1])

    def test_reference_tangents_already_symmetric(self):
        source = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')
        self.assertEqual(center_tangent_lines(source), (source, False))

    def test_all_samples_have_complete_walkthroughs(self):
        for category, sample in SAMPLES.items():
            with self.subTest(category=category):
                lesson = GeneratedLesson.model_validate({**sample,
                    'manim_code': (ROOT / 'templates' / f'{category}.py').read_text(encoding='utf-8')})
                self.assertGreaterEqual(len(lesson.solution_steps), 3)
                self.assertLessEqual(len(lesson.solution_steps), 5)
                self.assertTrue(lesson.final_answer)

    def test_tutor_step_requires_formula_reason_and_multiline_calculation(self):
        from prompts import SolutionStep
        step = dict(SAMPLES['derivative_tangent']['solution_steps'][0])
        self.assertEqual(set(SolutionStep.model_fields), {'step_number', 'action_title', 'formula_used',
                                                         'why_this_formula', 'detailed_walkthrough'})
        for field in ['formula_used', 'why_this_formula', 'detailed_walkthrough']:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SolutionStep.model_validate({key: value for key, value in step.items() if key != field})
        with self.assertRaises(ValidationError):
            SolutionStep.model_validate({**step, 'detailed_walkthrough': 'm = 4'})

    def test_raw_latex_and_nonconsecutive_steps_rejected(self):
        sample = {**SAMPLES['derivative_tangent'], 'manim_code': 'scene'}
        with self.assertRaises(ValidationError):
            GeneratedLesson.model_validate({**sample, 'problem_title': 'f(x)=x^{2}'})
        steps = [dict(step) for step in sample['solution_steps']]
        steps[1]['step_number'] = 4
        with self.assertRaises(ValidationError):
            GeneratedLesson.model_validate({**sample, 'solution_steps': steps})

    def test_named_math_lambda_calls_are_allowed(self):
        code = '''from manim import *
class GeneratedScene(Scene):
    def construct(self):
        func = lambda x: 15 - 2*x**2
        point = Dot(Axes().c2p(1, func(1)))
'''
        validate_code(code)
        with self.assertRaises(ValueError):
            validate_code(code.replace('15 - 2*x**2', 'open("secret")'))
        with self.assertRaises(ValueError):
            validate_code(code.replace('point = Dot', 'func = Text\n        point = Dot'))

    def test_axis_labels_require_both_explicit_text_objects(self):
        prefix = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        axes = Axes()\n        '
        validate_code(prefix + 'labels = axes.get_axis_labels(x_label=Text("x"), y_label=Text("y"))')
        for call in ['axes.get_axis_labels()', 'axes.get_axis_labels("x", "y")', 'axes.get_axis_labels(x_label=Text("x"))']:
            with self.subTest(call=call), self.assertRaises(ValueError):
                validate_code(prefix + 'labels = ' + call)

    def test_reference_labels_avoid_bottom_edge_and_latex(self):
        for path in (ROOT / 'templates').glob('*.py'):
            code = path.read_text(encoding='utf-8')
            validate_code(code)
            self.assertNotIn('.to_edge(DOWN)', code)
            self.assertIn('get_axis_labels', code)
            self.assertNotIn('^2', code)

    def test_symmetric_secant_endpoints_and_slopes(self):
        # Sample secants are centered on x0=2 and pass through (2,4).
        for dx in [1, 0.7, 0.4, 0.2, 0.05]:
            m = ((2 + dx)**2 - 4) / dx
            self.assertAlmostEqual(m, 4 + dx)
            left = (0.5, 4 - m * 1.5)
            right = (3.5, 4 + m * 1.5)
            self.assertAlmostEqual((left[0] + right[0])/2, 2)
            self.assertAlmostEqual((left[1] + right[1])/2, 4)

    def test_text_latex_is_rejected(self):
        prefix = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        '
        with self.assertRaises(ValueError):
            validate_code(prefix + 'title = Text("f(x)=x^{2}")')
