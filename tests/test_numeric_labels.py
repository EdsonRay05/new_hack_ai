import ast
import math
from pathlib import Path
import unittest

from validation import validate_code

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'from manim import *\nclass GeneratedScene(Scene):\n    def construct(self):\n        '


class NumericLabelTests(unittest.TestCase):
    def test_hardcoded_evaluated_labels_rejected(self):
        for label in ['Point: (5, 35)', '(5, 35)', 'Slope = 15', 'y = 15x - 65', 'Range = 9.796 m', 'Magnitude = 5']:
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, 'computed variables'):
                validate_code(PREFIX + f'label = Text({label!r})')
        validate_code(PREFIX + 'x0 = 5\n        y0 = 10\n        label = Text(f"Point: ({x0:g}, {y0:.4g})")')

    def test_pure_function_is_allowed_but_not_io_or_extra_statements(self):
        body = '\nclass GeneratedScene(Scene):\n    def construct(self):\n        y0 = f(5)\n'
        validate_code('from manim import *\ndef f(x):\n    return x**3 - 6*x**2 + 35\n' + body)
        for function in ['def f(x):\n    return open("secret")',
                         'def f(x):\n    return np.load(x)',
                         'def f(x):\n    value = x\n    return value',
                         'def f(x):\n    return f(x)']:
            with self.subTest(function=function), self.assertRaises(ValueError):
                validate_code('from manim import *\n' + function + '\n' + body)

    def test_cubic_arithmetic_regression(self):
        code = 'from manim import *\ndef f(x):\n    return x**3 - 6*x**2 + 35\ndef derivative(x):\n    return 3*x**2 - 12*x\nclass GeneratedScene(Scene):\n    def construct(self):\n        x0 = 5\n        y0 = f(x0)\n        slope = derivative(x0)\n        label = Text(f"Point: ({x0:g}, {y0:.4g})")\n'
        validate_code(code)
        tree = ast.parse(code)
        functions = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef)], type_ignores=[])
        namespace = {}
        exec(compile(functions, '<validated-numeric-regression>', 'exec'), namespace)
        terms = [125, -150, 35]
        self.assertEqual(namespace['f'](5), sum(terms))
        self.assertEqual(namespace['f'](5), 10)
        self.assertEqual(namespace['derivative'](5), 75 - 60)
        self.assertEqual(namespace['f'](5) - namespace['derivative'](5)*5, -65)

    def test_references_use_pure_numeric_functions_and_dynamic_values(self):
        for path in (ROOT / 'templates').glob('*.py'):
            code = path.read_text(encoding='utf-8')
            validate_code(code)
            tree = ast.parse(code)
            self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name != 'add_plain_axis_numbers' for node in tree.body))
