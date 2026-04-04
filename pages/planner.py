# ══════════════════════════════════════════════════════════════════════════════
# pages/planner.py — Study Planner
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_plan, get_plans, get_quizzes, upsert_user
from services import (
    compute_profile, build_study_structure, generate_study_plan,
)
from ui.components import back_btn, section_header, topic_banner

_TASK_ICONS = {
    "learn":    "📖",
    "video":    "▶️",
    "practice": "✏️",
    "quiz":     "🎯",
    "revision": "🔄",
    "project":  "🛠️",
    "weak":     "⚠️",
}
_PHASE_COLORS = {
    "Foundation":   "#3B82F6",
    "Application":  "#7C3AED",
    "Mastery":      "#059669",
}


def render() -> None:
    back_btn("A 7-day plan beats 7 days of aimless studying.", "back_planner")
    section_header("📅 Study Planner", "Rule-based structure + AI-generated daily tasks")
    topic_banner()

    email   = st.session_state.user_email
    profile = compute_profile(get_quizzes(email, 50))

    # ── Plan configuration ────────────────────────────────────────────────────
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)
    plan_topic = st.text_input(
        "", placeholder="e.g. Machine Learning, Data Structures, React...",
        value=st.session_state.current_topic,
        label_visibility="collapsed", key="plan_topic",
    )
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        plan_level = st.selectbox(
            "Level", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.user_level),
            key="plan_lvl",
        )
    with pc2:
        days = st.selectbox("Duration", [3, 5, 7, 10, 14], index=2, key="plan_days")
    with pc3:
        hours = st.selectbox("Daily Hours", [0.5, 1.0, 1.5, 2.0, 3.0], index=1, key="plan_hours")

    gen = st.button("Generate Study Plan →", key="gen_plan")
    st.markdown("</div>", unsafe_allow_html=True)

    if gen and plan_topic.strip():
        st.session_state.current_topic = plan_topic.strip()
        st.session_state.user_level    = plan_level
        upsert_user(
            email=email, name=st.session_state.user_name,
            level=plan_level, goal=st.session_state.user_goal,
            current_topic=plan_topic.strip(), weak_areas=st.session_state.weak_areas,
        )

        with st.spinner("🤖 Building your personalised study plan..."):
            # Rule-based structure (always works)
            structure = build_study_structure(
                plan_topic.strip(), plan_level,
                profile.get("weak_topics", []),
                days, hours,
            )
            # AI narrative (optional enhancement)
            ai_plan = generate_study_plan(
                plan_topic.strip(), profile.get("weak_topics", []),
                plan_level, st.session_state.user_goal,
                days, hours, profile,
            )

        st.session_state.study_plan_structure = structure
        st.session_state.study_plan_output    = ai_plan
        save_plan(email, plan_topic.strip(), ai_plan, days)

    # ── Display plan ──────────────────────────────────────────────────────────
    if st.session_state.study_plan_structure:
        _render_structure(st.session_state.study_plan_structure)

    if st.session_state.study_plan_output:
        st.markdown("---")
        st.markdown("### 🤖 AI-Enriched Plan Details")
        st.markdown(f"<div class='plan-card'>{st.session_state.study_plan_output}</div>",
                    unsafe_allow_html=True)

    # ── Saved plans ───────────────────────────────────────────────────────────
    saved = get_plans(email)
    if saved:
        st.markdown("---")
        st.markdown("### 📂 Saved Plans")
        for p in saved:
            with st.expander(f"📅 {p.get('topic','')} — {p.get('days','')} days"):
                st.markdown(p.get("plan", ""))


def _render_structure(structure: list) -> None:
    st.markdown("### 📅 Day-by-Day Structure")
    for day in structure:
        phase       = day["phase"]
        color       = _PHASE_COLORS.get(phase, "#64748B")
        total_mins  = sum(t["duration"] for t in day["tasks"])

        st.markdown(
            f"<div class='day-card'>"
            f"<div class='day-header'>Day {day['day']} "
            f"<span style='font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;"
            f"background:{color}20;color:{color};margin-left:8px;'>{phase}</span>"
            f"<span style='font-size:11px;color:#94A3B8;margin-left:8px;'>{total_mins} min total</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        for task in day["tasks"]:
            icon = _TASK_ICONS.get(task["type"], "📌")
            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;'>"
                f"<span style='font-size:14px;'>{icon}</span>"
                f"<div><div style='font-size:13px;color:#0F172A;'>{task['task']}</div>"
                f"<div style='font-size:11px;color:#94A3B8;'>{task['duration']} min</div></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div style='font-size:11px;color:#7C3AED;font-style:italic;margin-top:6px;'>"
            f"💬 {day['reminder']}</div></div>",
            unsafe_allow_html=True,
        )
