"""Center numerically resolvable tangent/secant Line segments on their fixed point.

This is a layout correction, not a symbolic derivative verifier. Unknown
expressions are left alone rather than executed or guessed.
"""
import ast
import math
import operator

from validation import validate_code

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Pow: operator.pow}


def center_tangent_lines(code: str) -> tuple[str, bool]:
    validate_code(code)
    tree = ast.parse(code)
    scene = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'GeneratedScene')
    method = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'construct')
    values = {}
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and len(node.body) == 1 and isinstance(node.body[0], ast.Return)}

    def number(node, scope=None):
        scope = values if scope is None else scope
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.Name):
            value = scope[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = number(node.operand, scope) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            left, right = number(node.left, scope), number(node.right, scope)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError('Exponent not suitable for layout inspection.')
            value = OPS[type(node.op)](left, right)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions:
            function = functions[node.func.id]
            if len(function.args.args) != 1 or len(node.args) != 1 or node.keywords:
                raise ValueError('Not a one-argument math function.')
            scope = {**scope, function.args.args[0].arg: number(node.args[0], scope)}
            expression = function.body if isinstance(function, ast.Lambda) else function.body[0].value
            value = number(expression, scope)
        else:
            raise ValueError('Unknown numeric expression.')
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e9:
            raise ValueError('Value not suitable for layout inspection.')
        return float(value)

    def point_coordinates(node):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'c2p' and len(node.args) >= 2):
            raise ValueError('Unknown point construction.')
        return number(node.args[0]), number(node.args[1])

    fixed = None
    for statement in method.body:
        if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            continue
        name, value = statement.targets[0].id, statement.value
        if isinstance(value, ast.Lambda):
            functions[name] = value
        else:
            try:
                values[name] = number(value)
            except (ValueError, KeyError, ArithmeticError, OverflowError):
                pass
        if name in {'point', 'fixed_point', 'tangency_point'} and isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name) and value.func.id == 'Dot' and value.args:
                try:
                    fixed = point_coordinates(value.args[0])
                except (ValueError, KeyError, ArithmeticError, OverflowError):
                    pass
    if fixed is None:
        return code, False
    changed = False
    x0, y0 = fixed
    for node in ast.walk(method):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and any(word in node.targets[0].id.lower() for word in ('tangent', 'secant'))):
            continue
        line = node.value
        if not (isinstance(line, ast.Call) and isinstance(line.func, ast.Name)
                and line.func.id == 'Line' and len(line.args) >= 2):
            continue
        try:
            x1, y1 = point_coordinates(line.args[0])
            x2, y2 = point_coordinates(line.args[1])
            slope = (y2 - y1) / (x2 - x1)
        except (ValueError, KeyError, ArithmeticError, OverflowError):
            continue
        if math.isclose(x1, x0 - 1.5) and math.isclose(x2, x0 + 1.5) and math.isclose((y1 + y2)/2, y0, abs_tol=1e-8):
            continue
        for endpoint, x, y in [(line.args[0], x0 - 1.5, y0 - 1.5*slope),
                               (line.args[1], x0 + 1.5, y0 + 1.5*slope)]:
            endpoint.args[:2] = [ast.Constant(x), ast.Constant(y)]
        changed = True
    if not changed:
        return code, False
    result = ast.unparse(ast.fix_missing_locations(tree)) + '\n'
    validate_code(result)
    return result, True
