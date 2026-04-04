# ══════════════════════════════════════════════════════════════════════════════
# pages/quiz.py — AI Quiz Generator + Performance Analysis
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_quiz, save_note, get_quizzes, upsert_user, log_activity, upsert_srs_card, get_srs_card
from services import (
    generate_quiz, parse_quiz, analyze_quiz,
    tutor_post_quiz, compute_profile, update_weak_areas, generate_notes,
)
from services.spaced_repetition import new_card, update_card
from ui.components import (
    back_btn, section_header, topic_banner, score_circle,
    quiz_answer_row, connector_card, reset_quiz,
)


def render() -> None:
    back_btn("Analysing mistakes is where 80% of real learning happens.", "back_quiz")
    section_header("🎯 Quiz Generator", "Specific questions for your topic and level — with AI performance analysis")
    topic_banner()

    if not st.session_state.quiz_started:
        _setup_panel()
    elif st.session_state.quiz_submitted:
        _results_panel()
    else:
        _active_quiz_panel()


# ── Setup ─────────────────────────────────────────────────────────────────────

def _setup_panel() -> None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)

    q_topic = st.text_input(
        "Quiz Topic", placeholder="e.g. Gradient Descent, SQL JOINs, Newton's Laws...",
        value=st.session_state.current_topic, key="q_topic_inp",
    )
    qc1, qc2 = st.columns(2)
    with qc1:
        q_level = st.selectbox(
            "Level", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.user_level),
            key="q_lvl",
        )
    with qc2:
        st.selectbox("Questions", [5], key="q_num")

    gen = st.button("Generate AI Quiz →", key="gen_quiz_btn")
    st.markdown("</div>", unsafe_allow_html=True)

    # Weak area quick-quiz buttons
    if st.session_state.weak_areas:
        st.markdown("**⚠️ Quick-quiz on weak areas:**")
        wc = st.columns(min(3, len(st.session_state.weak_areas)))
        for i, w in enumerate(st.session_state.weak_areas[:3]):
            with wc[i]:
                if st.button(f"Quiz: {w[:22]}...", key=f"wq_{i}"):
                    q_topic = w
                    gen = True

    st.markdown("</div>", unsafe_allow_html=True)

    if not q_topic and not gen:
        st.info("🎯 Enter a topic — AI generates 5 specific, non-generic questions.")

    if gen and q_topic.strip():
        _generate_quiz(q_topic.strip(), q_level)
    elif gen:
        st.warning("Please enter a topic first!")


def _generate_quiz(topic: str, level: str) -> None:
    with st.spinner(f"🤖 Generating quiz on {topic}..."):
        raw = generate_quiz(topic, level)
        qs  = parse_quiz(raw)

    if not qs:
        st.error("Quiz generation failed — the AI response was malformed. Please try again.")
        return

    st.session_state.quiz_questions  = qs
    st.session_state.quiz_topic      = topic
    st.session_state.current_topic   = topic
    st.session_state.user_level      = level
    st.session_state.quiz_started    = True
    st.session_state.quiz_submitted  = False
    st.session_state.quiz_answers    = {}
    st.session_state.quiz_analysis   = ""
    st.session_state.tutor_post_quiz = ""
    upsert_user(
        email=st.session_state.user_email, name=st.session_state.user_name,
        level=level, goal=st.session_state.user_goal,
        current_topic=topic, weak_areas=st.session_state.weak_areas,
    )
    st.rerun()


# ── Active quiz ───────────────────────────────────────────────────────────────

def _active_quiz_panel() -> None:
    qs = st.session_state.quiz_questions
    answered = len(st.session_state.quiz_answers)

    st.progress(answered / len(qs) if qs else 0)
    st.caption(f"{answered}/{len(qs)} answered")

    for i, q in enumerate(qs):
        st.markdown(
            f"<div class='card'>"
            f"<div style='font-size:12px;color:#94A3B8;margin-bottom:6px;'>Q{i+1}/{len(qs)}</div>"
            f"<div style='font-family:Sora,sans-serif;font-size:15px;font-weight:600;color:#0F172A;'>"
            f"{q['q']}</div></div>",
            unsafe_allow_html=True,
        )
        choice = st.radio("", q["opts"], key=f"quiz_q_{i}", index=None, label_visibility="collapsed")
        if choice is not None:
            st.session_state.quiz_answers[i] = q["opts"].index(choice)

    if st.button("✅ Submit Quiz"):
        st.session_state.quiz_submitted = True
        st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────

def _results_panel() -> None:
    email   = st.session_state.user_email
    qs      = st.session_state.quiz_questions
    topic   = st.session_state.quiz_topic
    total   = len(qs)
    correct = sum(1 for i, q in enumerate(qs) if st.session_state.quiz_answers.get(i) == q["ans"])
    pct     = int(correct / total * 100) if total else 0
    wrong   = [qs[i]["q"] for i in range(total) if st.session_state.quiz_answers.get(i) != qs[i]["ans"]]

    # Persist result + update weak areas
    save_quiz(email, topic, correct, total, wrong)
    log_activity(email)
    st.session_state.weak_areas = update_weak_areas(st.session_state.weak_areas, wrong)
    st.session_state.last_quiz_wrong = wrong

    # Update spaced repetition card for this topic
    existing_card = get_srs_card(email, topic)
    card = existing_card if existing_card else new_card(email, topic)
    updated_card = update_card(card, float(pct))
    upsert_srs_card(email, updated_card)

    upsert_user(
        email=email, name=st.session_state.user_name,
        level=st.session_state.user_level, goal=st.session_state.user_goal,
        current_topic=st.session_state.current_topic,
        weak_areas=st.session_state.weak_areas,
    )

    # Score header
    score_circle(pct)
    st.markdown(
        f"<div style='text-align:center;'>"
        f"<div style='font-family:Sora,sans-serif;font-size:22px;font-weight:700;color:#0F172A;'>"
        f"{'Excellent! 🏆' if pct>=80 else 'Good Job! 🎉' if pct>=60 else 'Keep Going! 💪'}</div>"
        f"<div style='font-size:14px;color:#64748B;margin-top:6px;'>{correct}/{total} correct</div></div>",
        unsafe_allow_html=True,
    )

    # Answer review
    st.markdown("### 📋 Answer Review")
    for i, q in enumerate(qs):
        quiz_answer_row(q, st.session_state.quiz_answers.get(i, -1))

    # AI performance analysis
    st.markdown("### 📊 AI Performance Analysis")
    if not st.session_state.quiz_analysis:
        profile = compute_profile(get_quizzes(email, 50))
        with st.spinner("🤖 Analysing performance..."):
            st.session_state.quiz_analysis = analyze_quiz(
                topic, correct, total, wrong, st.session_state.user_level, profile
            )
    st.markdown(f"<div class='plan-card'>{st.session_state.quiz_analysis}</div>", unsafe_allow_html=True)

    # AI Tutor post-quiz
    st.markdown("### 🤖 AI Tutor — Post-Quiz Guidance")
    if not st.session_state.tutor_post_quiz:
        profile = compute_profile(get_quizzes(email, 50))
        with st.spinner("🤖 AI Tutor analysing your results..."):
            st.session_state.tutor_post_quiz = tutor_post_quiz(
                topic, correct, total, wrong,
                profile.get("weak_topics", []), st.session_state.user_level,
            )
    _tpq = st.session_state.tutor_post_quiz.replace('\n', '<br>')
    st.markdown(
        "<div class='connector-card'>"
        "<div style='font-size:12px;font-weight:700;color:#1D4ED8;margin-bottom:8px;'>🤖 YOUR AI TUTOR SAYS:</div>"
        f"<div style='font-size:13px;color:#1E40AF;line-height:1.7;'>{_tpq}</div></div>",
        unsafe_allow_html=True,
    )

    # Action buttons
    ta, tb, tc, td = st.columns(4)
    with ta:
        if st.button("▶️ Find Videos on Weak Topics"):
            st.session_state.active_page = "youtube"
            st.rerun()
    with tb:
        if st.button("📝 Notes on Weak Areas"):
            reset_quiz()
            st.session_state.active_page = "notes"
            st.rerun()
    with tc:
        if st.button("📅 Create Study Plan"):
            st.session_state.active_page = "planner"
            st.rerun()
    with td:
        if st.button("🔁 Try Again"):
            reset_quiz()
            st.rerun()

    # Targeted notes
    if wrong and pct < 80:
        st.markdown("---")
        st.info(f"You got {len(wrong)} wrong. Generate targeted notes?")
        if st.button("📝 Generate Targeted Notes →"):
            ctx = "Focus on these:\n" + "\n".join(f"- {w}" for w in wrong)
            with st.spinner("🤖 Generating targeted notes..."):
                notes = generate_notes(topic, st.session_state.user_level, st.session_state.user_goal, ctx)
            st.session_state.notes_output = notes
            save_note(email, f"{topic} — weak areas", notes,
                      st.session_state.user_level, st.session_state.user_goal)
            st.markdown(notes)
