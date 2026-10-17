"""題庫與對局流程的單元測試。"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from circuit_game.bank import load_bank
from circuit_game.game import advance, blank_state, open_brief, retry_wrong, score, start_play, submit_answer
from circuit_game.generate import instantiate, recompute
from circuit_game.grading import grade_numeric, parse_number, within_tolerance
from circuit_game.safe_math import FormulaError, evaluate


class BankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = load_bank()

    def test_topics_cover_both_curricula(self):
        joined = " ".join(source["url"] for source in self.bank.sources.values())
        self.assertIn("allaboutcircuits.com/textbook", joined)
        self.assertIn("ocw.nycu.edu.tw", joined)

    def test_numeric_display_passes_and_far_value_fails(self):
        for question in self.bank.questions:
            if question["type"] != "numeric":
                continue
            answer = self.bank.answers[question["id"]]
            self.assertTrue(grade_numeric(answer["value"], answer))
            self.assertFalse(grade_numeric(answer["value"] + answer["abs_tol"] * 20 + 1, answer))

    def test_requested_count_is_filled_from_templates(self):
        state = open_brief(blank_state(), self.bank, "ohm_power", "easy", 5, random.Random(1))
        self.assertEqual(len(state["queue"]), 5)
        self.assertEqual(len(state["items"]), 5)
        again = open_brief(blank_state(), self.bank, "ohm_power", "easy", 5, random.Random(2))
        prompts = [state["items"][qid]["question"]["prompt"] for qid in state["queue"]]
        other = [again["items"][qid]["question"]["prompt"] for qid in again["queue"]]
        self.assertNotEqual(prompts, other)

    def test_same_formula_survives_a_new_scenario(self):
        template = next(item for item in self.bank.templates if item["id"] == "ohm-forward")
        lamp = instantiate(template, random.Random(4), "a", scenario_id="lamp")
        heater = instantiate(template, random.Random(4), "b", scenario_id="heater")
        self.assertEqual(lamp["answer"]["value"], heater["answer"]["value"])
        self.assertEqual(lamp["question"]["model"], heater["question"]["model"])
        self.assertEqual(lamp["question"]["thinking"], "forward")
        self.assertNotEqual(lamp["question"]["prompt"], heater["question"]["prompt"])
        self.assertIn("桌燈", lamp["question"]["prompt"])
        self.assertIn(str(int(lamp["answer"]["compute"]["inputs"]["R"])), heater["question"]["prompt"])
        motor = next(item for item in self.bank.templates if item["id"] == "ohm-predict")
        self.assertEqual(motor["thinking"], "predict")
        self.assertNotEqual(template["model"], motor["model"])
        modes = {item["thinking"] for item in self.bank.templates if item["topic"] == "ohm_power"}
        self.assertTrue({"forward", "reverse", "compare", "error", "predict", "fault"} <= modes)

    def test_game_requires_reveal_before_next(self):
        state = open_brief(blank_state(), self.bank, "ohm_power", "easy", 5, random.Random(1))
        state = start_play(state)
        with self.assertRaises(ValueError):
            advance(state)
        qid = state["queue"][0]
        item = state["items"][qid]
        if item["question"]["type"] == "numeric":
            payload = str(item["answer"]["value"])
        else:
            payload = item["answer"]["correct_index"]
        state, error = submit_answer(state, payload)
        self.assertIsNone(error)
        self.assertTrue(state["results"][qid])
        self.assertAlmostEqual(recompute(item["answer"]), item["answer"]["value"])
        state = advance(state)
        self.assertEqual(state["index"], 1)
        self.assertFalse(state["revealed"])

    def test_retry_keeps_only_wrong_questions(self):
        state = open_brief(blank_state(), self.bank, "ohm_power", "easy", 5, random.Random(8))
        state["phase"] = "summary"
        state["results"] = {state["queue"][0]: False, state["queue"][1]: True}
        state["responses"] = {state["queue"][0]: "未答", state["queue"][1]: "對"}
        state["queue"] = state["queue"][:2]
        wrong_id = state["queue"][0]
        prompt = state["items"][wrong_id]["question"]["prompt"]
        retried = retry_wrong(state, random.Random(3))
        self.assertEqual(retried["queue"], [wrong_id])
        self.assertEqual(retried["items"][wrong_id]["question"]["prompt"], prompt)
        self.assertEqual(retried["phase"], "brief")
        self.assertEqual(score(retried), (0, 1))


class GradingTests(unittest.TestCase):
    def test_parse_decimal_comma_and_scientific(self):
        self.assertEqual(parse_number(" 3,5 "), 3.5)
        self.assertEqual(parse_number("-1.6"), -1.6)
        self.assertAlmostEqual(parse_number("3.2e-3"), 0.0032)

    def test_tolerance_either_bound(self):
        self.assertTrue(within_tolerance(318, 318.31, 1, 0.005))
        self.assertFalse(within_tolerance(330, 318.31, 1, 0.005))

    def test_formula_rejects_calls(self):
        with self.assertRaises(FormulaError):
            evaluate("__import__('os').system('echo no')", {})
        self.assertAlmostEqual(evaluate("1 / (2 * pi * f * C)", {"f": 50, "C": 10e-6}), 318.3098861837907)


if __name__ == "__main__":
    unittest.main()
