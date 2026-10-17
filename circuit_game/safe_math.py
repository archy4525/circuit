"""僅允許四則、次方與少數數學函數的公式求值，供題庫交叉檢查。"""

from __future__ import annotations

import ast
import math
from typing import Mapping

_FUNCS = {
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "abs": abs,
    "hypot": math.hypot,
}
_CONST = {"pi": math.pi, "e": math.e}


class FormulaError(ValueError):
    """公式無法安全求值。"""


def evaluate(formula: str, variables: Mapping[str, float] | None = None) -> float:
    if not isinstance(formula, str) or not formula.strip():
        raise FormulaError("公式是空的")
    if len(formula) > 200:
        raise FormulaError("公式過長")
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError("公式語法無法解析") from exc
    names = dict(_CONST)
    if variables:
        for key, value in variables.items():
            if not isinstance(key, str) or not key.isidentifier():
                raise FormulaError(f"變數名稱不合法：{key}")
            names[key] = float(value)
    result = _eval_node(tree.body, names)
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise FormulaError("公式結果不是數字")
    if not math.isfinite(float(result)):
        raise FormulaError("公式結果不是有限數")
    return float(result)


def _eval_node(node: ast.AST, names: dict) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError("只允許數字常數")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in names:
            raise FormulaError(f"未知名稱：{node.id}")
        return float(names[node.id])
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand, names)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
    ):
        left = _eval_node(node.left, names)
        right = _eval_node(node.right, names)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise FormulaError("除以零")
            return left / right
        if abs(right) > 8:
            raise FormulaError("次方過大")
        return left**right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None or node.keywords:
            raise FormulaError("不允許這個函式")
        args = [_eval_node(arg, names) for arg in node.args]
        try:
            return float(fn(*args))
        except (TypeError, ValueError) as exc:
            raise FormulaError("函式無法計算") from exc
    raise FormulaError("公式含有不允許的寫法")
