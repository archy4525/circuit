"""純資料的對局流程，不依賴 Streamlit。"""

from __future__ import annotations

import random
from typing import Any

from circuit_game.generate import TemplateError, generate_round, templates_for
from circuit_game.grading import AnswerFormatError, grade_choice, grade_numeric, parse_number

DIFFICULTY_LABELS = {
    "easy": "入門",
    "medium": "進階",
    "hard": "挑戰",
    "mixed": "混合難度",
}

THINKING_LABELS = {
    "forward": "正向計算",
    "reverse": "反向求解",
    "compare": "比較電路",
    "error": "找解題錯誤",
    "predict": "預測變化",
    "fault": "故障判斷",
}


class GameError(ValueError):
    """這個操作和目前進度不合。"""


def blank_state() -> dict[str, Any]:
    return {
        "phase": "home",
        "topic_id": "ohm_power",
        "difficulty": "easy",
        "requested_n": 5,
        "queue": [],
        "index": 0,
        "revealed": False,
        "results": {},
        "responses": {},
        "mode": "normal",
        "pool_size": 0,
        "title_override": "",
        "items": {},
    }


def list_topics(bank) -> list[dict[str, Any]]:
    topics = list(bank.topics.values())
    return sorted(topics, key=lambda item: item.get("order", 0))


def open_brief(
    state: dict[str, Any],
    bank,
    topic_id: str,
    difficulty: str,
    count: int,
    rng: random.Random,
) -> dict[str, Any]:
    if count < 1:
        raise GameError("題數至少要 1 題")
    try:
        pool = templates_for(bank, topic_id, difficulty)
        instances = generate_round(bank, topic_id, difficulty, count, rng)
    except TemplateError as exc:
        raise GameError(str(exc)) from exc
    items = {item["question"]["id"]: item for item in instances}
    new = dict(state)
    new.update(
        phase="brief",
        topic_id=topic_id,
        difficulty=difficulty,
        requested_n=count,
        queue=[item["question"]["id"] for item in instances],
        index=0,
        revealed=False,
        results={},
        responses={},
        mode="normal",
        pool_size=len(pool),
        title_override="",
        items=items,
    )
    return new


def start_play(state: dict[str, Any]) -> dict[str, Any]:
    if state["phase"] != "brief" or not state["queue"]:
        raise GameError("請先完成開場說明")
    new = dict(state)
    new["phase"] = "play"
    new["index"] = 0
    new["revealed"] = False
    return new


def current_id(state: dict[str, Any]) -> str:
    if state["phase"] != "play":
        raise GameError("目前不是作答中")
    return state["queue"][state["index"]]


def submit_answer(state: dict[str, Any], user: Any) -> tuple[dict[str, Any], str | None]:
    if state["phase"] != "play":
        raise GameError("目前不是作答中")
    if state["revealed"]:
        raise GameError("這題已經送出")
    qid = current_id(state)
    item = state["items"][qid]
    question = item["question"]
    answer = item["answer"]
    try:
        if question["type"] == "choice":
            if user is None:
                return state, "請先選擇一個選項。"
            selected = int(user)
            if not 0 <= selected < len(question["choices"]):
                return state, "請選擇列出的選項。"
            correct = grade_choice(selected, answer)
            shown = question["choices"][selected]
        elif question["type"] == "numeric":
            number = parse_number("" if user is None else str(user))
            correct = grade_numeric(number, answer)
            unit = question.get("unit") or ""
            shown = _trim_number(number) + (f" {unit}" if unit and unit != "—" else "")
        else:
            raise GameError("不支援的題型")
    except AnswerFormatError as exc:
        return state, str(exc)
    new = dict(state)
    new["revealed"] = True
    new["results"] = {**state["results"], qid: correct}
    new["responses"] = {**state["responses"], qid: shown}
    return new, None


def advance(state: dict[str, Any]) -> dict[str, Any]:
    if state["phase"] != "play" or not state["revealed"]:
        raise GameError("看完這一題的解析後才能繼續")
    new = dict(state)
    if state["index"] + 1 >= len(state["queue"]):
        new["phase"] = "summary"
        return new
    new["index"] = state["index"] + 1
    new["revealed"] = False
    return new


def retry_wrong(state: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    if state["phase"] != "summary":
        raise GameError("本輪還未結束")
    wrong = [qid for qid in state["queue"] if not state["results"].get(qid)]
    if not wrong:
        raise GameError("沒有錯題可以重做")
    rng.shuffle(wrong)
    new = dict(state)
    new.update(
        phase="brief",
        queue=wrong,
        index=0,
        revealed=False,
        results={},
        responses={},
        mode="retry",
        pool_size=len(wrong),
        title_override="錯題再練",
    )
    return new


def score(state: dict[str, Any]) -> tuple[int, int]:
    total = len(state["queue"])
    correct = sum(1 for qid in state["queue"] if state["results"].get(qid))
    return correct, total


def _trim_number(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if text in {"-0", ""}:
        return "0"
    return text
