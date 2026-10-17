"""讀取並檢查分開存放的固定題庫。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from circuit_game.generate import check_template
from circuit_game.grading import first_number, grade_numeric
from circuit_game.safe_math import FormulaError, evaluate

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "bank"

FORBIDDEN_QUESTION_KEYS = {
    "answer",
    "answers",
    "correct",
    "correct_index",
    "value",
    "steps",
    "substitution",
    "unit_check",
    "common_mistakes",
    "explanation",
}
DIAGRAM_KINDS = {
    "series",
    "divider",
    "parallel",
    "series_parallel",
    "nested",
    "node",
    "rc",
    "rl",
    "impedance",
    "opamp",
    "diode",
    "zener",
    "bjt",
    "thevenin",
}
DAMPING_WORDS = {
    "overdamped": "過阻尼",
    "critical": "臨界阻尼",
    "underdamped": "欠阻尼",
}


class BankError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


@dataclass
class Bank:
    topics: dict[str, dict[str, Any]]
    questions: list[dict[str, Any]]
    by_id: dict[str, dict[str, Any]]
    answers: dict[str, dict[str, Any]]
    explanations: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    templates: list[dict[str, Any]]


def load_bank(directory: Path | None = None) -> Bank:
    bank, errors = read_bank(directory)
    if errors or bank is None:
        raise BankError(errors or ["題庫是空的"])
    return bank


def read_bank(directory: Path | None = None) -> tuple[Bank | None, list[str]]:
    folder = directory or BANK_DIR
    errors: list[str] = []
    payloads: dict[str, Any] = {}
    for name in (
        "topics.json",
        "sources.json",
        "questions.json",
        "answers.json",
        "explanations.json",
        "templates.json",
    ):
        path = folder / name
        if not path.is_file():
            errors.append(f"缺少檔案 {name}")
            continue
        try:
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{name} 不是合法 JSON：第 {exc.lineno} 行")
    if errors:
        return None, errors
    return _validate(
        payloads["topics.json"],
        payloads["questions.json"],
        payloads["answers.json"],
        payloads["explanations.json"],
        payloads["sources.json"],
        payloads["templates.json"],
    )


def _validate(topics, questions, answers, explanations, sources, templates):
    errors: list[str] = []
    if not isinstance(topics, dict) or not topics:
        errors.append("topics.json 必須是非空物件")
        topics = {}
    if not isinstance(sources, dict) or not sources:
        errors.append("sources.json 必須是非空物件")
        sources = {}
    if not isinstance(questions, list) or not questions:
        errors.append("questions.json 必須是非空陣列")
        questions = []
    if not isinstance(answers, dict):
        errors.append("answers.json 必須是物件")
        answers = {}
    if not isinstance(explanations, dict):
        errors.append("explanations.json 必須是物件")
        explanations = {}

    for source_id, source in sources.items():
        if not isinstance(source, dict):
            errors.append(f"來源 {source_id} 格式不對")
            continue
        url = str(source.get("url", ""))
        if not source.get("title") or not url.startswith("https://"):
            errors.append(f"來源 {source_id} 需要標題與 https 連結")

    for topic_id, topic in topics.items():
        if not isinstance(topic, dict):
            errors.append(f"主題 {topic_id} 格式不對")
            continue
        if topic.get("id") != topic_id:
            errors.append(f"主題 {topic_id} 的 id 與鍵值不一致")
        for field in ("title", "blurb", "objectives", "formulas", "concepts", "source_ids"):
            if not topic.get(field):
                errors.append(f"主題 {topic_id} 缺少 {field}")
        _check_source_ids(topic.get("source_ids", []), sources, f"主題 {topic_id}", errors)

    by_id: dict[str, dict[str, Any]] = {}
    for question in questions:
        if not isinstance(question, dict) or "id" not in question:
            errors.append("有題目缺少 id")
            continue
        qid = question["id"]
        if qid in by_id:
            errors.append(f"題目編號重複：{qid}")
        by_id[qid] = question
        leaked = FORBIDDEN_QUESTION_KEYS.intersection(question)
        if leaked:
            errors.append(f"{qid} 的題幹檔含有答案或解析欄位：{', '.join(sorted(leaked))}")
        if question.get("topic") not in topics:
            errors.append(f"{qid} 的主題不存在")
        if question.get("difficulty") not in {"easy", "medium", "hard"}:
            errors.append(f"{qid} 的難度不合法")
        if question.get("type") not in {"choice", "numeric"}:
            errors.append(f"{qid} 的題型不合法")
        if not str(question.get("prompt", "")).strip():
            errors.append(f"{qid} 沒有題幹")
        diagram = question.get("diagram")
        if diagram is not None:
            if not isinstance(diagram, dict) or diagram.get("kind") not in DIAGRAM_KINDS:
                errors.append(f"{qid} 的圖種類無法繪製")
        if question.get("type") == "choice":
            choices = question.get("choices")
            if not isinstance(choices, list) or not (3 <= len(choices) <= 5):
                errors.append(f"{qid} 的選項數量需為 3 到 5")
            elif any(not str(item).strip() for item in choices):
                errors.append(f"{qid} 有空白選項")

    question_ids = set(by_id)
    if set(answers) != question_ids:
        errors.append("answers.json 的編號必須和題幹一一對應")
    if set(explanations) != question_ids:
        errors.append("explanations.json 的編號必須和題幹一一對應")

    for qid, question in by_id.items():
        answer = answers.get(qid)
        explanation = explanations.get(qid)
        if not isinstance(answer, dict) or not isinstance(explanation, dict):
            continue
        _check_answer(qid, question, answer, errors)
        _check_explanation(qid, question, answer, explanation, sources, errors)

    counts: dict[tuple[str, str], int] = {}
    for question in by_id.values():
        key = (question.get("topic"), question.get("difficulty"))
        counts[key] = counts.get(key, 0) + 1
    for topic_id, topic in topics.items():
        if topic.get("practice") == "mixed":
            continue
        for difficulty in ("easy", "medium", "hard"):
            if counts.get((topic_id, difficulty), 0) < 2:
                errors.append(f"主題 {topic_id} 的 {difficulty} 題少於 2 題")
        types = {item["type"] for item in by_id.values() if item.get("topic") == topic_id}
        if types != {"choice", "numeric"}:
            errors.append(f"主題 {topic_id} 需要同時有選擇題與數值題")

    _check_templates(templates, topics, sources, errors)

    if errors:
        return None, errors
    ordered = sorted(by_id.values(), key=lambda item: item["id"])
    return Bank(topics, ordered, by_id, answers, explanations, sources, list(templates)), []


def _check_templates(templates, topics, sources, errors) -> None:
    if not isinstance(templates, list) or not templates:
        errors.append("templates.json 必須是非空陣列")
        return
    seen: set[str] = set()
    formula_models: dict[str, dict[str, str]] = {}
    source_ids = set(sources)
    for template in templates:
        errors.extend(check_template(template, source_ids))
        if not isinstance(template, dict):
            continue
        tid = str(template.get("id") or "")
        if tid in seen:
            errors.append(f"題型編號重複：{tid}")
        seen.add(tid)
        if template.get("topic") not in topics:
            errors.append(f"題型 {tid} 的主題不存在")
        pieces = [
            str(item.get("formula") or "").replace(" ", "")
            for item in (template.get("derived") or [])
            if isinstance(item, dict)
        ]
        pieces.append(str(template.get("answer_formula") or "").replace(" ", ""))
        for option in template.get("options") or []:
            if isinstance(option, dict):
                pieces.append(str(option.get("text") or ""))
                pieces.append(str(option.get("formula") or "").replace(" ", ""))
        signature = " | ".join(pieces)
        if any(character.isalpha() for character in signature):
            formula_models.setdefault(signature, {})[str(template.get("model"))] = tid
    for _signature, models in formula_models.items():
        if len(models) > 1:
            joined = "、".join(models.values())
            errors.append(f"不同電路模型共用了同一組答案公式：{joined}")
    for topic_id, topic in topics.items():
        if topic.get("practice") == "mixed":
            continue
        group = [item for item in templates if isinstance(item, dict) and item.get("topic") == topic_id]
        for difficulty in ("easy", "medium", "hard"):
            if not any(item.get("difficulty") == difficulty for item in group):
                errors.append(f"主題 {topic_id} 的 {difficulty} 還沒有題型")
        kinds = {item.get("type") for item in group}
        if kinds != {"choice", "numeric"}:
            errors.append(f"主題 {topic_id} 的題型需要同時有選擇題與數值題")
        modes = {item.get("thinking") for item in group}
        missing = {"forward", "reverse", "compare", "error", "predict"} - modes
        if missing:
            errors.append(f"主題 {topic_id} 缺少思考方式：{', '.join(sorted(missing))}")


def _check_source_ids(source_ids, sources, label, errors) -> None:
    if not isinstance(source_ids, list) or not source_ids:
        errors.append(f"{label} 沒有來源")
        return
    for source_id in source_ids:
        if source_id not in sources:
            errors.append(f"{label} 引用了不存在的來源 {source_id}")


def _check_answer(qid, question, answer, errors) -> None:
    if question["type"] == "choice":
        if answer.get("type") != "choice":
            errors.append(f"{qid} 正解檔的題型不是選擇")
            return
        index = answer.get("correct_index")
        choices = question.get("choices") or []
        if not isinstance(index, int) or not (0 <= index < len(choices)):
            errors.append(f"{qid} 的正解索引超出選項")
            return
        values = answer.get("choice_values")
        if values is not None:
            if not isinstance(values, list) or len(values) != len(choices):
                errors.append(f"{qid} 的選項數值無法和選項對齊")
            elif not answer.get("compute"):
                errors.append(f"{qid} 的選項數值沒有對應公式")
            else:
                _match_compute(qid, answer["compute"], float(values[index]), errors)
        if answer.get("damping") is not None:
            _check_damping(qid, question, answer, errors)
        elif values is None and not answer.get("conceptual"):
            errors.append(f"{qid} 的選擇題缺少可檢查欄位")
    else:
        if answer.get("type") != "numeric":
            errors.append(f"{qid} 正解檔的題型不是數值")
            return
        if question.get("unit") != answer.get("unit"):
            errors.append(f"{qid} 的單位在題幹與正解不一致")
        for field in ("value", "abs_tol", "rel_tol"):
            if not isinstance(answer.get(field), (int, float)):
                errors.append(f"{qid} 的 {field} 必須是數字")
                return
        if answer["abs_tol"] <= 0 or answer["rel_tol"] <= 0:
            errors.append(f"{qid} 的允許誤差必須大於 0")
        if not answer.get("compute"):
            errors.append(f"{qid} 的數值題沒有可重算的公式")
        else:
            _match_compute(qid, answer["compute"], float(answer["value"]), errors)


def _match_compute(qid, compute, expected: float, errors) -> None:
    if not isinstance(compute, dict):
        errors.append(f"{qid} 的計算公式格式不對")
        return
    try:
        got = evaluate(str(compute.get("formula", "")), compute.get("vars") or {})
    except FormulaError as exc:
        errors.append(f"{qid} 的公式無法計算：{exc}")
        return
    tolerance = 1e-6 * max(1.0, abs(expected))
    if abs(got - expected) > tolerance:
        errors.append(f"{qid} 的公式結果 {got:.6g} 與存放的正解 {expected:.6g} 不一致")


def _check_damping(qid, question, answer, errors) -> None:
    expect = answer.get("damping")
    if expect not in DAMPING_WORDS:
        errors.append(f"{qid} 的阻尼分類無法檢查")
        return
    params = answer.get("damping_values")
    if not isinstance(params, dict):
        errors.append(f"{qid} 缺少阻尼參數")
        return
    try:
        alpha = evaluate("R/(2*L)", params)
        omega0 = evaluate("1/sqrt(L*C)", params)
    except FormulaError as exc:
        errors.append(f"{qid} 的阻尼公式無法計算：{exc}")
        return
    if omega0 == 0:
        errors.append(f"{qid} 的自然頻率是零")
        return
    if abs(alpha - omega0) / abs(omega0) < 1e-6:
        kind = "critical"
    elif alpha > omega0:
        kind = "overdamped"
    else:
        kind = "underdamped"
    if kind != expect:
        errors.append(f"{qid} 的阻尼分類應為 {kind}")
    word = DAMPING_WORDS[expect]
    choices = question["choices"]
    hits = [index for index, text in enumerate(choices) if word in text]
    if hits != [answer["correct_index"]]:
        errors.append(f"{qid} 的阻尼正解沒有對上選項")


def _check_explanation(qid, question, answer, explanation, sources, errors) -> None:
    steps = explanation.get("steps")
    if not isinstance(steps, list) or len(steps) < 3:
        errors.append(f"{qid} 的逐步解題少於 3 步")
    elif any(not str(step).strip() for step in steps):
        errors.append(f"{qid} 有空白的解題步驟")
    for field in ("answer_display", "substitution", "unit_check"):
        if not str(explanation.get(field, "")).strip():
            errors.append(f"{qid} 的解析缺少 {field}")
    mistakes = explanation.get("common_mistakes")
    if not isinstance(mistakes, list) or len(mistakes) < 2:
        errors.append(f"{qid} 的常見錯誤少於 2 則")
    _check_source_ids(explanation.get("source_ids", []), sources, f"{qid} 的解析", errors)
    display = str(explanation.get("answer_display", ""))
    if question["type"] == "choice":
        choices = question.get("choices") or []
        index = answer.get("correct_index")
        if isinstance(index, int) and 0 <= index < len(choices) and display != choices[index]:
            errors.append(f"{qid} 的解析答案文字和正解選項不一致")
    elif isinstance(answer.get("value"), (int, float)):
        shown = first_number(display)
        if shown is None:
            errors.append(f"{qid} 的答案展示沒有數字")
        elif not grade_numeric(shown, answer):
            errors.append(f"{qid} 的答案展示「{display}」會被計分判錯")
