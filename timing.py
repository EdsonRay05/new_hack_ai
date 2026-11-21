"""Adjust animation pacing without changing equations, geometry, or labels."""
import ast

from validation import validate_code


def retime_scene(code: str, measured_duration: float, target: float = 12.0) -> str:
    validate_code(code)
    if measured_duration <= 0:
        raise ValueError('Cannot adjust an empty video.')
    tree = ast.parse(code)
    scene = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'GeneratedScene')
    method = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'construct')
    final_wait = None
    # Preserve the requested final reading pause when it is a simple literal.
    last = method.body[-1]
    if isinstance(last, ast.Expr) and isinstance(last.value, ast.Call):
        call = last.value
        if (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
                and call.func.value.id == 'self' and call.func.attr == 'wait'
                and len(call.args) == 1 and isinstance(call.args[0], ast.Constant)
                and call.args[0].value == 1.5):
            final_wait = call
    fixed_pause = 1.5 if final_wait is not None else 0
    if measured_duration <= fixed_pause:
        raise ValueError('Scene contains no adjustable animation time.')
    factor = (target - fixed_pause) / (measured_duration - fixed_pause)

    def scaled(value):
        if isinstance(value, ast.Constant) and type(value.value) in (int, float):
            return ast.Constant(round(value.value * factor, 6))
        return ast.BinOp(left=value, op=ast.Mult(), right=ast.Constant(factor))

    for node in ast.walk(method):
        if not isinstance(node, ast.Call) or node is final_wait:
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == 'self' and func.attr in {'play', 'wait'}):
            continue
        keyword = 'run_time' if func.attr == 'play' else 'duration'
        duration = next((kw for kw in node.keywords if kw.arg == keyword), None)
        if duration is not None:
            duration.value = scaled(duration.value)
        elif func.attr == 'wait' and node.args:
            node.args[0] = scaled(node.args[0])
        else:
            node.keywords.append(ast.keyword(arg=keyword, value=ast.Constant(factor)))
    result = ast.unparse(ast.fix_missing_locations(tree)) + '\n'
    validate_code(result)
    return result
