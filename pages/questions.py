# ══════════════════════════════════════════════════════════════════════════════
# pages/questions.py — Important Questions + Answer Evaluation
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_eval, upsert_user
from services import (
    generate_important_questions, parse_questions,
    evaluate_answer, extract_score, tutor_post_eval,
)
from ui.components import back_btn, section_header, topic_banner, extract_pdf, extract_txt


_TYPE_BADGE = {
    "Conceptual": "b-blue",
    "Analytical":  "b-purple",
    "Applied":     "b-green",
    "Evaluative":  "b-amber",
}


def render() -> None:
    back_btn("Subjective practice builds exam confidence.", "back_questions")
    section_header("❓ Important Questions & Answer Evaluation",
                   "Exam-relevant questions + AI-powered answer evaluation with rubric scoring")
    topic_banner()

    _generate_questions_section()
    st.markdown("---")
    _evaluate_answer_section()


# ── Generate questions ────────────────────────────────────────────────────────

def _generate_questions_section() -> None:
    st.markdown("### 📋 Generate Important Questions")
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)

    topic = st.text_input(
        "", placeholder="e.g. Machine Learning, Photosynthesis, French Revolution...",
        value=st.session_state.current_topic,
        label_visibility="collapsed", key="iq_topic",
    )
    c1, c2 = st.columns(2)
    with c1:
        level = st.selectbox(
            "Level", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.user_level),
            key="iq_lvl",
        )
    with c2:
        count = st.selectbox("Number of Questions", [4, 6, 8], index=1, key="iq_count")

    gen = st.button("Generate Important Questions →", key="gen_iq")
    st.markdown("</div>", unsafe_allow_html=True)

    if gen and topic.strip():
        st.session_state.current_topic = topic.strip()
        st.session_state.user_level    = level
        upsert_user(
            email=st.session_state.user_email, name=st.session_state.user_name,
            level=level, goal=st.session_state.user_goal,
            current_topic=topic.strip(), weak_areas=st.session_state.weak_areas,
        )
        with st.spinner(f"🤖 Generating {count} exam-relevant questions on {topic}..."):
            raw = generate_important_questions(topic.strip(), level, count)
            st.session_state.imp_questions = parse_questions(raw)

    if st.session_state.imp_questions:
        st.markdown("### 📚 Questions to Practice")
        for i, q in enumerate(st.session_state.imp_questions):
            badge_cls = _TYPE_BADGE.get(q.get("type", "Conceptual").split("/")[0].strip(), "b-gray")
            st.markdown(
                f"<div class='q-card'>"
                f"<div style='font-size:14px;font-weight:600;color:#0F172A;'>Q{i+1}. {q['q']}</div>"
                f"<div class='q-type'>"
                f"<span class='badge {badge_cls}'>{q.get('type','Conceptual')}</span>"
                f"<span class='badge b-gray'>{q.get('length','Medium')} answer</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ── Evaluate answer ───────────────────────────────────────────────────────────

def _evaluate_answer_section() -> None:
    st.markdown("### 📝 Evaluate Your Answer")
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)

    # Question selector
    question_text = ""
    if st.session_state.imp_questions:
        options = ["Type your own question..."] + [
            q["q"][:80] + "..." for q in st.session_state.imp_questions
        ]
        selected = st.selectbox("Select question to answer:", options, key="q_select")
        if selected == "Type your own question...":
            question_text = st.text_area("Enter your question:", height=80, key="q_custom")
        else:
            idx = options.index(selected) - 1
            question_text = st.session_state.imp_questions[idx]["q"] if idx >= 0 else ""
    else:
        question_text = st.text_area("Enter question to answer:", height=80, key="q_manual")

    # Answer input
    st.markdown("**Your Answer:**")
    ans_tab1, ans_tab2 = st.tabs(["✍️ Type Answer", "📄 Upload Answer (PDF/TXT)"])
    user_answer = ""

    with ans_tab1:
        user_answer = st.text_area(
            "", placeholder="Type your answer here...",
            height=200, key="ans_typed", label_visibility="collapsed",
        )

    with ans_tab2:
        ans_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"], key="ans_file")
        if ans_file:
            fb  = ans_file.read()
            ext = ans_file.name.lower().split(".")[-1]
            text, err = extract_pdf(fb) if ext == "pdf" else extract_txt(fb)
            if err:
                st.error(f"Error: {err}")
            elif text:
                user_answer = text
                st.success(f"✅ Extracted {len(text)} characters")
                st.text(text[:300] + "...")

    eval_btn = st.button("📊 Evaluate My Answer →", key="eval_btn")
    st.markdown("</div>", unsafe_allow_html=True)

    if eval_btn:
        if not question_text.strip():
            st.warning("Please enter or select a question.")
        elif not user_answer.strip():
            st.warning("Please type or upload your answer.")
        else:
            _run_evaluation(question_text.strip(), user_answer.strip())

    # Results
    if st.session_state.eval_result:
        _render_eval_result()


def _run_evaluation(question: str, answer: str) -> None:
    topic = st.session_state.current_topic or "the topic"
    with st.spinner("🤖 Evaluating your answer with rubric scoring..."):
        evaluation = evaluate_answer(question, answer, topic, st.session_state.user_level)
        score      = extract_score(evaluation)

    st.session_state.eval_result     = evaluation
    st.session_state.eval_score      = score

    # Extract weakness context for tutor
    lines       = evaluation.split("\n")
    weak_lines  = [l for l in lines if any(w in l.lower() for w in ("weak", "missing", "incorrect"))]
    weak_ctx    = " ".join(weak_lines[:3])
    miss_idx    = evaluation.find("Missing")
    miss_ctx    = evaluation[miss_idx:miss_idx + 200] if miss_idx != -1 else ""

    with st.spinner("🤖 Generating tutor guidance..."):
        st.session_state.tutor_post_eval = tutor_post_eval(
            question, score, weak_ctx, miss_ctx, topic
        )

    save_eval(st.session_state.user_email, question, answer, evaluation, score)


def _render_eval_result() -> None:
    score = st.session_state.eval_score
    sc    = "#059669" if score >= 7 else "#D97706" if score >= 4 else "#DC2626"

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:1rem;'>"
        f"<div style='font-size:36px;font-weight:700;color:{sc};'>{score}/10</div>"
        f"<div style='font-size:14px;color:#64748B;'>AI Rubric Score</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(st.session_state.eval_result)

    if st.session_state.tutor_post_eval:
        st.markdown("### 🤖 AI Tutor Guidance")
        st.markdown(
            "<div class='connector-card'>"
            "<div style='font-size:13px;color:#1E40AF;line-height:1.7;'>"
            + st.session_state.tutor_post_eval.replace('\n', '<br>')
            + "</div></div>",
            unsafe_allow_html=True,
        )
