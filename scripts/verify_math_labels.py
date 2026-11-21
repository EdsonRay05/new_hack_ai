"""Local regression for V(t)=t³-6t²+35 at t=5, using the derivative reference."""
import ast
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from manim import Text, tempconfig
from renderer import render_scene
from validation import validate_code

source = (ROOT / 'templates' / 'derivative_tangent.py').read_text(encoding='utf-8')


class CubicProblem(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        if node.name == 'f':
            node.body = [ast.Return(ast.parse('x**3 - 6*x**2 + 35', mode='eval').body)]
        elif node.name == 'derivative':
            node.body = [ast.Return(ast.parse('3*x**2 - 12*x', mode='eval').body)]
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'x0':
            node.value = ast.Constant(5)
        return self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'Axes':
            for keyword in node.keywords:
                if keyword.arg == 'x_range':
                    keyword.value = ast.parse('[0, 8, 2]', mode='eval').body
                elif keyword.arg == 'y_range':
                    keyword.value = ast.parse('[-40, 60, 20]', mode='eval').body
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'plot':
            for keyword in node.keywords:
                if keyword.arg == 'x_range':
                    keyword.value = ast.parse('[2, 6.5]', mode='eval').body
        if isinstance(node.func, ast.Name) and node.func.id == 'add_plain_axis_numbers':
            node.args[1:] = [ast.parse('[2, 4, 5, 6, 8]', mode='eval').body,
                             ast.parse('[-40, -20, 10, 20, 40, 60]', mode='eval').body]
        if isinstance(node.func, ast.Name) and node.func.id == 'Text' and node.args:
            if isinstance(node.args[0], ast.Constant):
                replacements = {'A derivative is a limiting slope': None,
                                'Function:\nf(x) = x²': 'Function:\nV(t) = t³ - 6t²\n+ 35', 'x': 't', 'y': 'V'}
                text = node.args[0].value
                if text in replacements:
                    node.args[0] = ast.parse("f'Slope of V(t) at t = {x0:g}'", mode='eval').body if replacements[text] is None else ast.Constant(replacements[text])
            elif isinstance(node.args[0], ast.JoinedStr):
                for part in node.args[0].values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        part.value = part.value.replace('y = ', 'V = ').replace('x ', 't ')
        return self.generic_visit(node)


tree = ast.fix_missing_locations(CubicProblem().visit(ast.parse(source)))
code = ast.unparse(tree) + '\n'
validate_code(code)
original_init = Text.__init__
texts = []


def observe(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    texts.append(self)


construct = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'construct')
construct.body.append(ast.parse("self.verified_values = {'x0': x0, 'y0': y0, 'slope': slope, 'intercept': intercept, 'dot': axes.p2c(point.get_center()).tolist()}").body[0])
namespace = {'__name__': 'cubic_label_regression'}
with tempconfig({'dry_run': True, 'verbosity': 'ERROR', 'media_dir': str(ROOT / 'media' / 'cubic-label-check')}), patch.object(Text, '__init__', observe):
    exec(compile(ast.fix_missing_locations(tree), '<trusted-cubic-reference>', 'exec'), namespace)
    scene = namespace['GeneratedScene'](skip_animations=True)
    scene.render()
assert scene.verified_values['y0'] == 10
assert scene.verified_values['slope'] == 15
assert scene.verified_values['intercept'] == -65
assert abs(scene.verified_values['dot'][1] - 10) < 1e-8
assert any(text.text.replace(' ', '') == 'Point:(5,10)' for text in texts)
assert not any(text.text.replace(' ', '') == 'Point:(5,35)' for text in texts)
result = render_scene(code, 'cubic-numeric-regression')
print(json.dumps({'values': scene.verified_values, 'video_url': result['video_url'],
                  'duration': result['duration'], 'label_check': 'Point: (5, 10)'}, indent=2))
