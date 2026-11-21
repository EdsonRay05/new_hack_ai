"""Conservative rejection checks, NOT a security sandbox."""
import ast
import re


ALLOWED_CALLS = set('''Text MarkupText Scene VGroup Group VMobject Mobject
Axes NumberPlane NumberLine Dot Line Arrow DoubleArrow DashedLine Circle Square
Rectangle Polygon Arc Angle BraceBetweenPoints SurroundingRectangle RoundedRectangle
ValueTracker always_redraw Create Write FadeIn FadeOut Transform ReplacementTransform
TransformFromCopy MoveAlongPath GrowArrow GrowFromCenter DrawBorderThenFill
Indicate Circumscribe AnimationGroup LaggedStart Succession Wait
range enumerate zip len float int str abs min max round list tuple
linear smooth rush_into rush_from there_and_back interpolate
'''.split())
ALLOWED_METHODS = set('''construct play wait add remove clear animate copy become
move_to next_to to_edge to_corner shift scale rotate stretch set_color set_fill
set_stroke set_opacity set_z_index set_width set_height arrange arrange_in_grid
get_center get_start get_end get_top get_bottom get_left get_right get_x get_y
set_x set_y set_value get_value add_updater clear_updaters c2p p2c plot
get_secant_slope_group get_riemann_rectangles get_area get_tangent_line get_axis_labels
point_from_proportion put_start_and_end_on set_points_as_corners
set_points_smoothly add_points_as_corners set_length set_angle append
sin cos tan arctan2 sqrt square array linspace clip dot norm exp log abs
'''.split())
FORBIDDEN_NAMES = {'Tex', 'MathTex', 'Typst', 'MathTypst', 'DecimalNumber', 'Integer', 'TexTemplate', 'open',
                   'exec', 'eval', 'compile', 'getattr', 'setattr', 'globals',
                   'locals', 'vars', 'input', 'help', 'breakpoint', '__import__'}


def validate_code(code: str) -> None:
    if not code or len(code) > 30000:
        raise ValueError('Scene code is empty or too large.')
    tree = ast.parse(code)
    scenes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(scenes) != 1 or scenes[0].name != 'GeneratedScene':
        raise ValueError('Exactly one GeneratedScene class is required.')
    scene = scenes[0]
    if len(scene.bases) != 1 or not isinstance(scene.bases[0], ast.Name) or scene.bases[0].id != 'Scene':
        raise ValueError('GeneratedScene must inherit Scene directly.')
    if scene.decorator_list or scene.keywords:
        raise ValueError('Scene decorators and metaclasses are prohibited.')
    if len(scene.body) != 1 or not isinstance(scene.body[0], ast.FunctionDef) or scene.body[0].name != 'construct':
        raise ValueError('Only the construct method is allowed in the scene.')
    method = scene.body[0]
    if method.decorator_list or method.args.defaults or method.args.kw_defaults or method.returns:
        raise ValueError('Method decorators, defaults and annotations are prohibited.')
    if len(method.args.args) != 1 or method.args.args[0].arg != 'self' or method.args.args[0].annotation:
        raise ValueError('construct must take self only.')
    helpers = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(helpers) > 8 or len({node.name for node in helpers}) != len(helpers):
        raise ValueError('Use at most eight uniquely named numeric/helper functions.')
    for helper in helpers:
        args = helper.args
        if (helper.decorator_list or helper.returns or args.defaults or args.kw_defaults
                or args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs
                or any(arg.annotation for arg in args.args)):
            raise ValueError('Helper functions must use plain positional arguments with no decorators or defaults.')
        if helper.name == 'add_plain_axis_numbers':
            if [arg.arg for arg in args.args] != ['axes', 'x_vals', 'y_vals']:
                raise ValueError('Use add_plain_axis_numbers(axes, x_vals, y_vals).')
            continue
        if (helper.name in ALLOWED_CALLS | FORBIDDEN_NAMES or helper.name.startswith('_')
                or not 1 <= len(args.args) <= 4 or len(helper.body) != 1
                or not isinstance(helper.body[0], ast.Return)):
            raise ValueError('Numeric functions must contain one return expression and 1–4 arguments.')
        numeric_calls = {'abs', 'min', 'max', 'round', 'float', 'int'}
        names = {arg.arg for arg in args.args} | numeric_calls | {'np', 'PI', 'TAU', 'E'}
        allowed_nodes = (ast.Return, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Attribute,
                         ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
                         ast.Mod, ast.FloorDiv, ast.USub, ast.UAdd)
        for node in ast.walk(helper.body[0]):
            if not isinstance(node, allowed_nodes):
                raise ValueError('Numeric functions may only evaluate arithmetic expressions.')
            if isinstance(node, ast.Name) and node.id not in names:
                raise ValueError(f'Unsupported numeric-function name: {node.id}.')
            if isinstance(node, ast.Constant) and type(node.value) not in (int, float):
                raise ValueError('Numeric functions may not contain text or other nonnumeric constants.')
            if isinstance(node, ast.Attribute) and not (isinstance(node.value, ast.Name)
                    and node.value.id == 'np' and node.attr in {'sin', 'cos', 'tan', 'sqrt', 'exp', 'log', 'arctan2', 'square', 'abs', 'pi', 'e'}):
                raise ValueError('Numeric functions may only access approved NumPy math operations.')
            if isinstance(node, ast.Call) and not ((isinstance(node.func, ast.Name) and node.func.id in numeric_calls)
                    or isinstance(node.func, ast.Attribute)):
                raise ValueError('Numeric functions may only call approved numeric operations.')
    roots = [method, *helpers]
    imports = 0
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == 'manim' and node.level == 0 and len(node.names) == 1 and node.names[0].name == '*' and node.names[0].asname is None:
            imports += 1
        elif node is not scene and node not in helpers:
            raise ValueError('Only the Manim import, numeric-label helper, and scene class are allowed at module level.')
    if imports != 1:
        raise ValueError('Use exactly one `from manim import *` import.')
    # Calls to locally bound math lambdas are safe only after inspecting their
    # full bodies under the same rules. Do not permit arbitrary callable aliases.
    bindings = {}
    for node in ast.walk(method):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bindings.setdefault(node.id, []).append(node)
    lambda_calls = set()
    text_bindings = {}

    def text_call(value):
        if isinstance(value, ast.Name):
            return text_bindings.get(value.id)
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and value.func.id in {'Text', 'MarkupText'}:
                return value
            if isinstance(value.func, ast.Attribute):
                return text_call(value.func.value)
        return None

    for node in ast.walk(method):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Lambda)
                and len(bindings[node.targets[0].id]) == 1):
            lambda_calls.add(node.targets[0].id)
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            label = text_call(node.value)
            if label is not None:
                text_bindings[node.targets[0].id] = label
    for node in (node for root in roots for node in ast.walk(root)):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.While, ast.With, ast.Try,
                             ast.AsyncFunctionDef, ast.Global, ast.Nonlocal,
                             ast.Delete, ast.ClassDef)):
            raise ValueError(f'Unsupported scene construct: {type(node).__name__}.')
        if isinstance(node, ast.FunctionDef) and node not in roots:
            raise ValueError('Nested functions are not allowed.')
        if isinstance(node, ast.keyword) and node.arg == 'include_numbers' and not (isinstance(node.value, ast.Constant) and node.value.value is False):
            raise ValueError('Use plain Text tick labels; include_numbers must be False.')
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == 'include_numbers' and not (isinstance(value, ast.Constant) and value.value is False):
                    raise ValueError('Use plain Text tick labels; include_numbers must be False.')
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith('_')):
            raise ValueError(f'Prohibited name: {node.id}.')
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('_') or node.attr in FORBIDDEN_NAMES:
                raise ValueError(f'Prohibited attribute: {node.attr}.')
            if isinstance(node.ctx, ast.Store):
                raise ValueError('Attribute assignment is prohibited.')
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute) and target.attr == 'next_to':
                label = text_call(target.value)
                if label is not None and label.args:
                    fragments = ''.join(part.value for part in ast.walk(label.args[0])
                                        if isinstance(part, ast.Constant) and isinstance(part.value, str))
                    if '=' in fragments or len(fragments) > 18:
                        raise ValueError('Formulas and long labels must be arranged inside the right info_panel, never attached with next_to. Only minimal coordinate labels may sit beside a graph point.')
            if isinstance(target, ast.Name) and target.id in {'Text', 'MarkupText'} and node.args:
                value = node.args[0]
                fragments = ''.join(part.value for part in ast.walk(value)
                                    if isinstance(part, ast.Constant) and isinstance(part.value, str))
                evaluated = (re.search(r'(?i)\b(point|slope|magnitude|flight|range|exact area|period)\b', fragments)
                             or re.fullmatch(r'\s*\(\s*[-+\d.]+\s*,\s*[-+\d.]+\s*\)\s*', fragments)
                             or re.match(r'^\s*(?:y|V)\s*=\s*[-+]?\d', fragments))
                if evaluated and re.search(r'\d', fragments) and not any(isinstance(part, ast.FormattedValue) for part in ast.walk(value)):
                    raise ValueError('Evaluated numeric labels must use computed variables in f-strings, never hardcoded point/slope/result values.')
                for part in ast.walk(node.args[0]):
                    if isinstance(part, ast.Constant) and isinstance(part.value, str) and re.search(
                            r'\\(?:frac|dfrac|sqrt|theta|pi|left|right|[()\[\]])|\^\{?|_\{', part.value):
                        raise ValueError('Text labels must use clean Unicode math, never LaTeX or caret exponents.')
            if isinstance(target, ast.Name) and target.id not in ALLOWED_CALLS | lambda_calls | {helper.name for helper in helpers}:
                raise ValueError(f'Unsupported function: {target.id}.')
            if isinstance(target, ast.Attribute) and target.attr not in ALLOWED_METHODS:
                raise ValueError(f'Unsupported method: {target.attr}.')
            if not isinstance(target, (ast.Name, ast.Attribute)):
                raise ValueError('Indirect calls are prohibited.')
            if isinstance(target, ast.Attribute) and target.attr == 'get_axis_labels':
                labels = list(node.args) + [kw.value for kw in node.keywords if kw.arg in {'x_label', 'y_label'}]
                if len(labels) != 2 or any(not (isinstance(label, ast.Call)
                    and isinstance(label.func, ast.Name) and label.func.id in {'Text', 'MarkupText'}) for label in labels):
                    raise ValueError('Axis labels must be explicit Text objects for both x and y; bare strings require LaTeX.')
