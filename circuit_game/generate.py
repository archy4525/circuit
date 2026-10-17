"""由題型模板抽出一題：數字、情境、正解與解析使用同一組數值。"""

from __future__ import annotations

import math
import random
import re
from typing import Any

from circuit_game.diagrams import render_svg
from circuit_game.grading import first_number, grade_numeric
from circuit_game.safe_math import FormulaError, evaluate


class TemplateError(ValueError):
    """題型模板無法抽出合格題目。"""


def templates_for(bank, topic_id: str, difficulty: str) -> list[dict[str, Any]]:
    topic = bank.topics.get(topic_id)
    if topic is None:
        raise TemplateError("找不到這個主題")
    chosen = list(bank.templates)
    if topic.get("practice") != "mixed":
        chosen = [item for item in chosen if item["topic"] == topic_id]
    if difficulty != "mixed":
        chosen = [item for item in chosen if item["difficulty"] == difficulty]
    return chosen


def generate_round(
    bank, topic_id: str, difficulty: str, count: int, rng: random.Random
) -> list[dict[str, Any]]:
    pool = templates_for(bank, topic_id, difficulty)
    if not pool:
        raise TemplateError("這個範圍還沒有題型")
    if count < 1:
        raise TemplateError("題數至少要 1 題")
    order: list[dict[str, Any]] = []
    while len(order) < count:
        bag = list(pool)
        rng.shuffle(bag)
        order.extend(bag)
    instances: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for index, template in enumerate(order[:count]):
        picked = None
        candidate = None
        for _ in range(16):
            candidate = instantiate(template, rng, f"{template['id']}-{index}")
            signature = (
                template["id"],
                candidate["question"]["scenario_id"],
                tuple(sorted(candidate["answer"]["compute"]["inputs"].items())),
            )
            if signature not in seen:
                picked = candidate
                seen.add(signature)
                break
        instances.append(picked or candidate)
    return instances


def instantiate(
    template: dict[str, Any],
    rng: random.Random,
    qid: str,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    last = "沒有成功的抽樣"
    for _ in range(80):
        try:
            env = _sample_env(template, rng)
            if not _accept(template, env):
                last = "數值沒有落在條件裡"
                continue
            scenario = _scenario(template, rng, scenario_id)
            return _build(template, env, scenario, qid, rng)
        except (FormulaError, TemplateError, KeyError, ValueError) as exc:
            last = str(exc)
            if scenario_id and isinstance(exc, TemplateError) and "沒有情境" in str(exc):
                raise
            continue
    raise TemplateError(f"{template.get('id', '?')} 無法抽出合格版本：{last}")


def recompute(answer: dict[str, Any]) -> float:
    return evaluate(answer["compute"]["formula"], _env_from(answer))


def audit_instance(instance: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    question = instance["question"]
    answer = instance["answer"]
    explanation = instance["explanation"]
    qid = question["id"]
    try:
        got = recompute(answer)
    except (FormulaError, KeyError, TypeError) as exc:
        return [f"{qid} 無法用原公式重算：{exc}"]
    if not _close(got, float(answer["value"])):
        errors.append(f"{qid} 存放的正解和公式不一致")
    blob = question["prompt"] + "\n" + "\n".join(question.get("notes") or [])
    shown = answer["compute"].get("shown")
    inputs = answer["compute"]["inputs"]
    if shown is None:
        shown = list(inputs)
    for name in shown:
        token = text_of(float(inputs[name]))
        if not _contains_token(blob, token):
            errors.append(f"{qid} 沒有寫出計算需要的 {name} = {token}")
    if question.get("model") != answer["compute"].get("model"):
        errors.append(f"{qid} 的電路模型與公式不是同一題型")
    if question["type"] == "numeric":
        shown = first_number(str(explanation.get("answer_display", "")))
        if shown is None or not grade_numeric(shown, answer):
            errors.append(f"{qid} 的答案展示無法用同一標準計分")
        numbers = _numbers(explanation.get("substitution", ""))
        if not numbers or not grade_numeric(numbers[-1], answer):
            errors.append(f"{qid} 的公式代入最後一個數字不是正解")
        unit = question.get("unit") or ""
        if unit and unit not in question["prompt"]:
            errors.append(f"{qid} 的題幹沒有標出單位 {unit}")
    else:
        choices = question.get("choices") or []
        index = answer.get("correct_index")
        if not isinstance(index, int) or not (0 <= index < len(choices)):
            errors.append(f"{qid} 的正解索引超出選項")
        elif explanation.get("answer_display") != choices[index]:
            errors.append(f"{qid} 的解析答案和正解選項不一致")
        else:
            try:
                option_values = [
                    evaluate(item["formula"], _env_from(answer)) for item in answer["compute"]["options"]
                ]
            except (FormulaError, KeyError) as exc:
                errors.append(f"{qid} 的選項公式無法重算：{exc}")
            else:
                hits = [pos for pos, value in enumerate(option_values) if _close(value, got)]
                if hits != [index]:
                    errors.append(f"{qid} 的選項公式沒有唯一對上正解")
    if len(explanation.get("steps") or []) < 3:
        errors.append(f"{qid} 的逐步解題少於 3 步")
    if len(explanation.get("common_mistakes") or []) < 2:
        errors.append(f"{qid} 的常見錯誤少於 2 則")
    diagram = question.get("diagram")
    if diagram is not None:
        try:
            render_svg(diagram)
        except Exception as exc:  # noqa: BLE001 — 圖失敗要回到題型檢查
            errors.append(f"{qid} 的電路圖無法繪製：{exc}")
    return errors


def text_of(value: float) -> str:
    if not math.isfinite(value):
        return "nan"
    nearest = round(value)
    if abs(value - nearest) <= 1e-8 * max(1.0, abs(value)):
        return str(int(nearest))
    magnitude = abs(value)
    if 1e-3 <= magnitude < 1e6:
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{value:.4g}"


def _sample_env(template: dict[str, Any], rng: random.Random) -> dict[str, float]:
    env: dict[str, float] = {}
    for var in template.get("variables") or []:
        if "values" in var:
            env[var["name"]] = float(rng.choice(var["values"]))
        else:
            step = float(var.get("step", 1))
            start = float(var["min"])
            stop = float(var["max"])
            slots = int(round((stop - start) / step))
            env[var["name"]] = start + step * rng.randrange(slots + 1)
    for item in template.get("derived") or []:
        env[item["name"]] = evaluate(item["formula"], env)
    return env


def _accept(template: dict[str, Any], env: dict[str, float]) -> bool:
    for formula in template.get("constraints") or []:
        if evaluate(formula, env) <= 0:
            return False
    for check in template.get("checks") or []:
        got = evaluate(check["formula"], env)
        if "min" in check and got < float(check["min"]) - 1e-9:
            return False
        if "max" in check and got > float(check["max"]) + 1e-9:
            return False
    return True


def _scenario(template: dict[str, Any], rng: random.Random, scenario_id: str | None) -> dict[str, Any]:
    scenarios = template["scenarios"]
    if scenario_id is None:
        return rng.choice(scenarios)
    for item in scenarios:
        if item["id"] == scenario_id:
            return item
    raise TemplateError(f"{template['id']} 沒有情境 {scenario_id}")


def _build(
    template: dict[str, Any],
    env: dict[str, float],
    scenario: dict[str, Any],
    qid: str,
    rng: random.Random,
) -> dict[str, Any]:
    if scenario.get("model") != template["model"]:
        raise TemplateError(f"{template['id']} 的情境 {scenario.get('id')} 用了另一個電路模型")
    mapping = _mapping(env, scenario)
    prompt = _fill(scenario["prompt"], mapping)
    conditions = [_fill(item, mapping) for item in scenario["conditions"]]
    notes = [f"接法：{_fill(template['connection'], mapping)}", *conditions]
    notes.extend(_fill(item, mapping) for item in template["assumptions"])
    diagram = _fill_tree(template["diagram"], mapping) if template.get("diagram") else None
    steps = [_fill(item, mapping) for item in template["steps"]]
    mistakes = [_fill(item, mapping) for item in template["common_mistakes"]]
    value = evaluate(template["answer_formula"], env)
    compute: dict[str, Any] = {
        "inputs": {var["name"]: env[var["name"]] for var in template.get("variables") or []},
        "shown": [
            var["name"] for var in template.get("variables") or [] if var.get("show", True)
        ],
        "derived": [
            {"name": item["name"], "formula": item["formula"]} for item in template.get("derived") or []
        ],
        "formula": template["answer_formula"],
        "model": template["model"],
        "template_id": template["id"],
    }
    question: dict[str, Any] = {
        "id": qid,
        "topic": template["topic"],
        "difficulty": template["difficulty"],
        "type": template["type"],
        "prompt": prompt,
        "notes": notes,
        "template_id": template["id"],
        "model": template["model"],
        "scenario_id": scenario["id"],
        "thinking": template.get("thinking", ""),
    }
    if diagram is not None:
        question["diagram"] = diagram
    explanation: dict[str, Any] = {
        "steps": steps,
        "substitution": _fill(template["substitution"], mapping),
        "unit_check": _fill(template["unit_check"], mapping),
        "common_mistakes": mistakes,
        "source_ids": list(template["source_ids"]),
    }
    if template["type"] == "numeric":
        unit = template["unit"]
        question["unit"] = unit
        explanation["answer_display"] = f"{text_of(value)} {unit}".strip()
        answer: dict[str, Any] = {
            "type": "numeric",
            "value": value,
            "abs_tol": float(template["abs_tol"]),
            "rel_tol": float(template["rel_tol"]),
            "unit": unit,
            "compute": compute,
        }
    else:
        built = []
        for option in template["options"]:
            built.append(
                {
                    "text": _fill(option["text"], mapping),
                    "formula": option["formula"],
                    "value": evaluate(option["formula"], env),
                }
            )
        texts = [item["text"] for item in built]
        if len(set(texts)) != len(texts) or not (3 <= len(texts) <= 5):
            raise TemplateError("選項文字重複或數量不對")
        hits = [index for index, item in enumerate(built) if _close(item["value"], value)]
        if len(hits) != 1:
            raise TemplateError("選項公式沒有唯一對上正解")
        order = list(range(len(built)))
        rng.shuffle(order)
        shuffled = [built[index] for index in order]
        correct = order.index(hits[0])
        question["choices"] = [item["text"] for item in shuffled]
        compute["options"] = [{"formula": item["formula"], "text": item["text"]} for item in shuffled]
        explanation["answer_display"] = shuffled[correct]["text"]
        answer = {
            "type": "choice",
            "correct_index": correct,
            "value": value,
            "compute": compute,
        }
    return {"question": question, "answer": answer, "explanation": explanation}


def _mapping(env: dict[str, float], scenario: dict[str, Any]) -> dict[str, str]:
    mapping = {key: text_of(value) for key, value in env.items()}
    for key, value in scenario.items():
        if isinstance(value, str) and key != "prompt":
            mapping[key] = value
    return mapping


def _fill(text: str, mapping: dict[str, str]) -> str:
    if not isinstance(text, str):
        raise TemplateError("句型不是文字")
    try:
        filled = text.format_map(_Strict(mapping))
    except KeyError as exc:
        raise TemplateError(f"句型缺少欄位 {exc}") from exc
    if "{" in filled or "}" in filled:
        raise TemplateError("句型還有沒填上的括號")
    return filled


def _fill_tree(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        return _fill(value, mapping)
    if isinstance(value, list):
        return [_fill_tree(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: _fill_tree(item, mapping) for key, item in value.items()}
    return value


def _env_from(answer: dict[str, Any]) -> dict[str, float]:
    compute = answer["compute"]
    env = {key: float(value) for key, value in compute["inputs"].items()}
    for item in compute["derived"]:
        env[item["name"]] = evaluate(item["formula"], env)
    return env


def _close(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-6 * max(1.0, abs(right))


def _numbers(text: str) -> list[float]:
    found: list[float] = []
    cursor = text
    pattern = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
    while cursor:
        match = pattern.search(cursor.replace(",", ""))
        if match is None:
            return found
        found.append(float(match.group(0)))
        cursor = cursor[match.end() :]
    return found


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", text) is not None


class _Strict(dict):
    def __missing__(self, key: str) -> str:
        raise KeyError(key)


def check_template(template: dict[str, Any], source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(template, dict):
        return ["有題型不是物件"]
    tid = str(template.get("id") or "?")
    for field in (
        "id",
        "topic",
        "difficulty",
        "type",
        "model",
        "connection",
        "assumptions",
        "source_ids",
        "scenarios",
        "answer_formula",
        "steps",
        "substitution",
        "unit_check",
        "common_mistakes",
        "step_rule",
        "thinking",
    ):
        if not template.get(field):
            errors.append(f"{tid} 缺少 {field}")
    if template.get("thinking") not in {
        "forward",
        "reverse",
        "compare",
        "error",
        "predict",
        "fault",
    }:
        errors.append(f"{tid} 的思考方式不合法")
    if template.get("difficulty") not in {"easy", "medium", "hard"}:
        errors.append(f"{tid} 的難度不合法")
    if template.get("type") not in {"numeric", "choice"}:
        errors.append(f"{tid} 的題型不合法")
    if template.get("type") == "numeric":
        if not template.get("unit") and template.get("unit") != "":
            errors.append(f"{tid} 缺少單位")
        for field in ("abs_tol", "rel_tol"):
            if not isinstance(template.get(field), (int, float)) or float(template.get(field) or 0) <= 0:
                errors.append(f"{tid} 的 {field} 必須大於 0")
    else:
        options = template.get("options")
        if not isinstance(options, list) or not (3 <= len(options) <= 5):
            errors.append(f"{tid} 的選項需為 3 到 5 個")
        elif any(not item.get("text") or not item.get("formula") for item in options if isinstance(item, dict)):
            errors.append(f"{tid} 有選項缺少文字或公式")
    scenarios = template.get("scenarios")
    if isinstance(scenarios, list):
        if len(scenarios) < 2:
            errors.append(f"{tid} 至少要有兩種情境描述")
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                errors.append(f"{tid} 有情境格式不對")
                continue
            if scenario.get("model") != template.get("model"):
                errors.append(f"{tid} 的情境 {scenario.get('id')} 必須沿用這個題型的電路模型")
            if not scenario.get("prompt") or not scenario.get("conditions"):
                errors.append(f"{tid} 的情境 {scenario.get('id')} 缺少題幹或條件")
    for bucket in (template.get("variables") or [], template.get("derived") or []):
        for item in bucket:
            name = item.get("name") if isinstance(item, dict) else None
            if not isinstance(name, str) or not name.isidentifier() or name in {"sqrt", "exp", "log", "abs", "hypot", "pi", "e"}:
                errors.append(f"{tid} 有不合法的變數名稱")
    missing = [item for item in template.get("source_ids") or [] if item not in source_ids]
    if missing:
        errors.append(f"{tid} 引用了不存在的來源 {', '.join(missing)}")
    if len(template.get("steps") or []) < 3:
        errors.append(f"{tid} 的步驟句型少於 3 句")
    if len(template.get("common_mistakes") or []) < 2:
        errors.append(f"{tid} 的常見錯誤少於 2 則")
    if errors:
        return errors
    for seed in (1, 2, 3):
        try:
            instance = instantiate(template, random.Random(seed), f"{tid}-c{seed}")
        except TemplateError as exc:
            errors.append(str(exc))
            break
        errors.extend(audit_instance(instance))
    return errors
