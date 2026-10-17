"""電路學與電子學解題。手機與 iPad 優先。"""

from __future__ import annotations

import random
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from circuit_game.bank import BankError, load_bank
from circuit_game.diagrams import diagram_document
from circuit_game.game import (
    DIFFICULTY_LABELS,
    THINKING_LABELS,
    advance,
    blank_state,
    current_id,
    list_topics,
    open_brief,
    retry_wrong,
    score,
    start_play,
    submit_answer,
)
from circuit_game.generate import templates_for
from circuit_game.grading import format_tolerance

COUNTS = (3, 5, 8, 10)
LETTERS = "ABCDE"

st.set_page_config(
    page_title="電路解題",
    page_icon="Ω",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    _css()
    try:
        bank = load_bank()
    except BankError as exc:
        st.error("題庫沒有通過檢查，遊戲先暫停。")
        for item in exc.errors:
            st.write(item)
        st.caption("修正 bank 目錄後重新整理。也可在本機執行 python scripts/check_bank.py。")
        return

    if "game" not in st.session_state:
        st.session_state.game = blank_state()
    if "round_token" not in st.session_state:
        st.session_state.round_token = 0
    if "form_error" not in st.session_state:
        st.session_state.form_error = ""
    if "confirm_leave" not in st.session_state:
        st.session_state.confirm_leave = False

    game = st.session_state.game
    if game.get("phase") != "home" and "items" not in game:
        st.session_state.game = blank_state()
        game = st.session_state.game
    phase = game["phase"]
    if phase == "home":
        _home(bank)
    elif phase == "brief":
        _brief(bank)
    elif phase == "play":
        _play(bank)
    else:
        _summary(bank)


def _css() -> None:
    st.markdown(
        """
<style>
  .stApp { background: #f4f0e6; }
  section.stMain { align-items: center; }
  .block-container {
    width: min(42rem, calc(100vw - 1.5rem)) !important;
    max-width: 42rem !important;
    padding-top: 1.1rem;
    padding-bottom: 4.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
  }
  .stElementContainer:has(.stButton),
  .stElementContainer:has(.stFormSubmitButton),
  .stButton,
  .stFormSubmitButton { width: 100% !important; }
  h1 { letter-spacing: -0.03em; font-size: 2rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.35rem !important; }
  p, li, label, .stMarkdown { font-size: 1.05rem; line-height: 1.6; }
  .stButton > button,
  .stFormSubmitButton > button {
    width: 100% !important;
    min-height: 3.35rem;
    border-radius: 14px;
    font-size: 1.08rem;
    font-weight: 680;
    padding: 0.7rem 1rem;
  }
  div[role="radiogroup"] label {
    min-height: 2.8rem;
    align-items: center;
    font-size: 1.05rem !important;
    line-height: 1.45 !important;
  }
  div[data-testid="stRadio"] > label p { font-size: 1.02rem !important; }
  .kicker {
    color: #0f6e56;
    font-weight: 750;
    letter-spacing: 0.08em;
    font-size: 0.82rem;
    margin-bottom: 0.2rem;
  }
  .formula {
    background: #fffdf8;
    border: 1px solid #e4dccb;
    border-radius: 14px;
    padding: 0.85rem 1rem;
    margin: 0.45rem 0;
  }
  .formula .expr {
    font-size: 1.28rem;
    font-weight: 750;
    letter-spacing: -0.02em;
    color: #14221c;
  }
  .formula .note { color: #5c564c; margin-top: 0.15rem; }
  .banner {
    border-radius: 14px;
    padding: 0.9rem 1rem;
    font-size: 1.15rem;
    font-weight: 750;
    margin: 0.2rem 0 0.8rem;
  }
  .banner.ok { background: #e5f4ec; color: #0d5c40; }
  .banner.bad { background: #fde8e4; color: #8d2d22; }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.4rem 0 0.8rem;
  }
  .chip {
    background: #fffdf8;
    border: 1px solid #e4dccb;
    border-radius: 999px;
    padding: 0.28rem 0.7rem;
    font-size: 0.95rem;
  }
  .score {
    font-size: 3rem;
    font-weight: 760;
    letter-spacing: -0.04em;
    line-height: 1;
    color: #0f6e56;
  }
  @media (max-width: 640px) {
    .block-container { padding-left: 0.8rem; padding-right: 0.8rem; }
    h1 { font-size: 1.75rem !important; }
  }
</style>
        """,
        unsafe_allow_html=True,
    )


def _home(bank) -> None:
    st.markdown('<div class="kicker">電路學・電子學</div>', unsafe_allow_html=True)
    st.title("電路解題")
    st.write("一次一題。送出之後才看得到正解、代入過程、單位檢查和常見錯誤。看完解析才能進下一題。")

    with st.container(border=True):
        st.markdown("**怎麼玩**")
        st.markdown("1. 選主題、難度與題數。\n2. 先看這一輪的學習目標和公式。\n3. 作答、讀解析，最後可以只重做錯題。")

    topics = list_topics(bank)
    labels = {item["id"]: item["title"] for item in topics}
    current = st.session_state.game["topic_id"]
    ids = [item["id"] for item in topics]
    if current not in ids:
        current = ids[0]
    topic_id = st.selectbox(
        "主題",
        ids,
        index=ids.index(current),
        format_func=lambda item: labels[item],
    )
    topic = bank.topics[topic_id]
    st.caption(topic["blurb"])

    difficulty = st.radio(
        "難度",
        list(DIFFICULTY_LABELS),
        format_func=lambda item: DIFFICULTY_LABELS[item],
        index=list(DIFFICULTY_LABELS).index(st.session_state.game["difficulty"]),
    )
    count = st.selectbox(
        "題數",
        COUNTS,
        index=COUNTS.index(st.session_state.game["requested_n"])
        if st.session_state.game["requested_n"] in COUNTS
        else 1,
    )
    available = templates_for(bank, topic_id, difficulty)
    st.caption(
        f"這個範圍有 {len(available)} 種題型，包含正向計算、反向求解、比較電路、找錯誤、預測變化或故障判斷。"
        "選幾題就出幾題。每題使用該電器自己的電路模型。"
    )
    if st.button("查看本輪說明", type="primary"):
        try:
            st.session_state.game = open_brief(
                st.session_state.game,
                bank,
                topic_id,
                difficulty,
                int(count),
                random.Random(),
            )
            st.session_state.round_token += 1
            st.session_state.form_error = ""
            st.session_state.confirm_leave = False
            st.rerun()
        except ValueError as exc:
            st.warning(str(exc))

    st.divider()
    st.caption(
        "題目、圖示與解析都是原創，用來練習教材裡的觀念，不複製教材段落、習題或圖片。"
        "觀念對照：All About Circuits《Lessons in Electric Circuits》，以及陽明交通大學 OCW「電路學概論」。"
    )


def _brief(bank) -> None:
    game = st.session_state.game
    topic = bank.topics[game["topic_id"]]
    title = game["title_override"] or topic["title"]
    st.markdown('<div class="kicker">開始之前</div>', unsafe_allow_html=True)
    st.title(title)
    if game["mode"] == "retry":
        st.write("這一輪只保留上一輪答錯的題目，順序已重排。規則和剛才相同：送出後才看解析。")
    else:
        st.write(topic["blurb"])

    chips = [
        f"難度　{DIFFICULTY_LABELS[game['difficulty']]}",
        f"本輪 {len(game['queue'])} 題",
        "選擇題與數值題",
    ]
    if game["mode"] != "retry":
        chips.append(f"{game['pool_size']} 種題型抽成這一輪")
        chips.append("數字與情境是新的")
    st.markdown(
        '<div class="meta">' + "".join(f'<span class="chip">{item}</span>' for item in chips) + "</div>",
        unsafe_allow_html=True,
    )

    st.subheader("學習目標")
    for item in topic["objectives"]:
        st.markdown(f"- {item}")

    st.subheader("相關公式與觀念")
    blocks = []
    for formula in topic["formulas"]:
        blocks.append(
            "<div class='formula'>"
            f"<div class='expr'>{escape(formula['expr'])}</div>"
            f"<div class='note'>{escape(formula['note'])}</div></div>"
        )
    st.markdown("".join(blocks), unsafe_allow_html=True)
    for concept in topic["concepts"]:
        st.markdown(f"- {concept}")

    with st.container(border=True):
        st.markdown("**觀念來源**")
        st.caption("連結只供對照觀念。本輪題目不是從這些頁面抄來的。")
        _source_links(bank, topic["source_ids"])

    if st.button("開始作答", type="primary"):
        st.session_state.game = start_play(game)
        st.session_state.form_error = ""
        st.rerun()
    if st.button("返回選題"):
        _go_home()


def _play(bank) -> None:
    game = st.session_state.game
    qid = current_id(game)
    question = game["items"][qid]["question"]
    topic = bank.topics[question["topic"]]
    total = len(game["queue"])
    number = game["index"] + 1
    st.progress(number / total, text=f"第 {number} 題，共 {total} 題")
    thinking = THINKING_LABELS.get(question.get("thinking", ""), "")
    st.markdown(
        "<div class='meta'>"
        f"<span class='chip'>{topic['title']}</span>"
        f"<span class='chip'>{DIFFICULTY_LABELS[question['difficulty']]}</span>"
        + (f"<span class='chip'>{thinking}</span>" if thinking else "")
        + f"<span class='chip'>{'選擇題' if question['type'] == 'choice' else '數值題'}</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.subheader(question["prompt"])
    if question.get("diagram"):
        html, height = diagram_document(question["diagram"])
        components.html(html, height=height + 8, scrolling=False)
    notes = question.get("notes") or []
    if notes:
        with st.container(border=True):
            st.markdown("**條件**")
            for note in notes:
                st.markdown(f"- {note}")

    if not game["revealed"]:
        _ask(bank, question)
    else:
        _reveal(bank, question)
    _leave_control()


def _ask(bank, question) -> None:
    token = st.session_state.round_token
    qid = question["id"]
    with st.form(key=f"answer-{token}-{qid}", clear_on_submit=False):
        if question["type"] == "choice":
            payload = st.radio(
                "選擇一個答案",
                list(range(len(question["choices"]))),
                format_func=lambda index: f"{LETTERS[index]}. {question['choices'][index]}",
                index=None,
                key=f"choice-{token}-{qid}",
            )
        else:
            unit = question.get("unit") or ""
            label = f"你的答案（{unit}）" if unit and unit != "—" else "你的答案"
            payload = st.text_input(
                label,
                key=f"num-{token}-{qid}",
                placeholder="例如 12.5、-1.6 或 3.2e-3",
            )
            st.caption("只填數字。單位以題目為準，不需再打進空格。")
        submitted = st.form_submit_button("送出答案", type="primary")
    if st.session_state.form_error:
        st.warning(st.session_state.form_error)
    if submitted:
        new_state, error = submit_answer(st.session_state.game, payload)
        if error:
            st.session_state.form_error = error
            st.rerun()
        st.session_state.game = new_state
        st.session_state.form_error = ""
        st.rerun()


def _reveal(bank, question) -> None:
    game = st.session_state.game
    qid = question["id"]
    item = game["items"][qid]
    correct = game["results"][qid]
    explanation = item["explanation"]
    answer = item["answer"]
    banner = "答對了" if correct else "這題還不對"
    kind = "ok" if correct else "bad"
    st.markdown(f"<div class='banner {kind}'>{banner}</div>", unsafe_allow_html=True)
    st.write(f"你的答案：{game['responses'][qid]}")
    st.write(f"正確答案：{_correct_text(question, answer, explanation)}")
    if question["type"] == "numeric":
        st.caption(format_tolerance(answer))

    st.subheader("逐步解題")
    for index, step in enumerate(explanation["steps"], start=1):
        st.markdown(f"{index}. {step}")

    st.subheader("公式代入")
    st.markdown(
        f"<div class='formula'><div class='expr'>{escape(explanation['substitution'])}</div></div>",
        unsafe_allow_html=True,
    )
    st.subheader("單位檢查")
    st.write(explanation["unit_check"])
    st.subheader("常見錯誤")
    for item in explanation["common_mistakes"]:
        st.markdown(f"- {item}")

    with st.container(border=True):
        st.markdown("**觀念來源**")
        st.caption("以下連結用來對照觀念。這一題的數字、圖和解析是原創的。")
        _source_links(bank, explanation["source_ids"])

    last = game["index"] + 1 >= len(game["queue"])
    label = "我已看完解析，看成績" if last else "我已看完解析，下一題"
    if st.button(label, type="primary"):
        st.session_state.game = advance(game)
        st.session_state.form_error = ""
        st.rerun()


def _summary(bank) -> None:
    game = st.session_state.game
    correct, total = score(game)
    topic = bank.topics[game["topic_id"]]
    heading = "錯題再練結果" if game["mode"] == "retry" else "本輪結果"
    st.markdown('<div class="kicker">作答結束</div>', unsafe_allow_html=True)
    st.title(heading)
    st.markdown(f"<div class='score'>{correct} / {total}</div>", unsafe_allow_html=True)
    st.write(f"{topic['title']}　·　{DIFFICULTY_LABELS[game['difficulty']]}")
    if total and correct == total:
        st.success("這一輪全部答對。")
    elif correct == 0:
        st.info("這一輪還沒有答對。可以只把錯題再練一次。")
    else:
        st.info(f"答對 {correct} 題，還有 {total - correct} 題可以重做。")

    st.subheader("每一題")
    for index, qid in enumerate(game["queue"], start=1):
        question = game["items"][qid]["question"]
        mark = "答對" if game["results"].get(qid) else "答錯"
        response = game["responses"].get(qid, "未作答")
        right = _correct_text(question, game["items"][qid]["answer"], game["items"][qid]["explanation"])
        with st.container(border=True):
            st.markdown(f"**{index}. {mark}**　{question['prompt']}")
            st.caption(f"你的答案：{response}")
            if not game["results"].get(qid):
                st.caption(f"正確答案：{right}")

    wrong = [qid for qid in game["queue"] if not game["results"].get(qid)]
    if wrong and st.button(f"重做錯題（{len(wrong)} 題）", type="primary"):
        st.session_state.game = retry_wrong(game, random.Random())
        st.session_state.round_token += 1
        st.session_state.form_error = ""
        st.rerun()
    if st.button("用同樣設定再練一輪", type="primary" if not wrong else "secondary"):
        st.session_state.game = open_brief(
            blank_state(),
            bank,
            game["topic_id"],
            game["difficulty"],
            game["requested_n"],
            random.Random(),
        )
        st.session_state.round_token += 1
        st.rerun()
    if st.button("回首頁"):
        _go_home()


def _correct_text(question, answer, explanation) -> str:
    if question["type"] == "choice":
        return f"{LETTERS[answer['correct_index']]}. {explanation['answer_display']}"
    return explanation["answer_display"]


def _source_links(bank, source_ids) -> None:
    for source_id in source_ids:
        source = bank.sources[source_id]
        st.markdown(f"- [{source['title']}]({source['url']})")


def _leave_control() -> None:
    st.write("")
    if st.session_state.confirm_leave:
        st.caption("離開後，這一輪的進度不會保留。")
        if st.button("確認離開，回首頁"):
            _go_home()
        if st.button("繼續作答"):
            st.session_state.confirm_leave = False
            st.rerun()
    elif st.button("離開本輪"):
        st.session_state.confirm_leave = True
        st.rerun()


def _go_home() -> None:
    kept = {
        "topic_id": st.session_state.game.get("topic_id", "ohm_power"),
        "difficulty": st.session_state.game.get("difficulty", "easy"),
        "requested_n": st.session_state.game.get("requested_n", 5),
    }
    st.session_state.game = {**blank_state(), **kept, "phase": "home"}
    st.session_state.form_error = ""
    st.session_state.confirm_leave = False
    st.rerun()


if __name__ == "__main__":
    main()
