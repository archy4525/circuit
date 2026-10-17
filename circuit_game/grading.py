"""選擇題與數值題的作答解析與計分。"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


class AnswerFormatError(ValueError):
    """玩家輸入無法當成數字。"""


def parse_number(text: str) -> float:
    if not isinstance(text, str):
        raise AnswerFormatError("請輸入數字")
    raw = (
        text.strip()
        .replace(" ", "")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("。", ".")
    )
    if not raw:
        raise AnswerFormatError("請輸入數字")
    if raw.count(",") == 1 and "." not in raw:
        raw = raw.replace(",", ".")
    else:
        raw = raw.replace(",", "")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", raw):
        raise AnswerFormatError("請輸入數字，例如 12.5、-1.6 或 3.2e-3")
    return float(raw)


def within_tolerance(user: float, value: float, abs_tol: float, rel_tol: float) -> bool:
    diff = abs(user - value)
    if diff <= abs_tol:
        return True
    scale = abs(value)
    if scale == 0:
        return False
    return diff / scale <= rel_tol


def first_number(text: str) -> float | None:
    match = _NUMBER.search(text.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def format_tolerance(answer: dict[str, Any]) -> str:
    unit = answer.get("unit") or ""
    unit_bit = f" {unit}" if unit and unit != "—" else ""
    rel = float(answer["rel_tol"]) * 100
    return (
        f"與正解相差不超過 ±{answer['abs_tol']:g}{unit_bit}"
        f"，或相對誤差不超過 {rel:g}%，即算答對。"
    )


def grade_choice(selected: int | None, answer: dict[str, Any]) -> bool:
    if selected is None:
        raise AnswerFormatError("請先選擇一個選項")
    return int(selected) == int(answer["correct_index"])


def grade_numeric(user: float, answer: dict[str, Any]) -> bool:
    return within_tolerance(
        user, float(answer["value"]), float(answer["abs_tol"]), float(answer["rel_tol"])
    )
