# ══════════════════════════════════════════════════════════════════════════════
# pages/dashboard.py — Home Dashboard
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import upsert_user, get_notes, get_studied_topics, get_quizzes, get_progress, get_srs_cards, get_activity_dates
from services import compute_profile, smart_recommend, get_prerequisites, get_learning_gaps
from services.spaced_repetition import get_due_cards, format_due_label, srs_stats
from services.streak_service import compute_streak, streak_message
from services.rag_service import get_indexed_topics, is_available as rag_available
from ui.components import (
    tip_banner, topic_banner, section_header,
    stat_card, insight_card, intel_box, dep_card, connector_card,
)
from ui.session import greet


def render() -> None:
    st.markdown(
        f"<div class='page-title'>{greet()}, {st.session_state.user_name}! 🌟</div>"
        "<div class='tagline'>Personalized AI Learning · Resource Intelligence Engine · Adaptive Tutor</div>",
        unsafe_allow_html=True,
    )

    tip_banner()
    topic_banner()

    # ── DB status (shown once, only when MONGO_URI missing) ───────────────────
    import os
    if not os.getenv("MONGO_URI"):
        st.info(
            "ℹ️ **No database connected** — add `MONGO_URI` to your `.env` file to persist data. "
            "The app works fully in demo mode without it.",
            icon=None,
        )

    # ── Load data ────────────────────────────────────────────────────────────
    email   = st.session_state.user_email
    prog    = get_progress(email)
    quizzes = get_quizzes(email, 50)
    profile = compute_profile(quizzes)
    studied = get_studied_topics(email)

    # ── Streak banner ─────────────────────────────────────────────────────────
    activity_dates = get_activity_dates(email)
    streak_data    = compute_streak(activity_dates)
    cs             = streak_data["current_streak"]
    nb             = streak_data.get("next_badge")

    if cs > 0:
        streak_color = "#059669" if cs >= 7 else "#D97706" if cs >= 3 else "#2563EB"
        # Build badge icons without backslash inside f-string (Python <3.12 compat)
        badge_parts = []
        for b in streak_data["badges_earned"]:
            bn, bd, bi = b["name"], b["desc"], b["icon"]
            badge_parts.append(f"<span title='{bn}: {bd}' style='font-size:18px;'>{bi}</span>")
        badges_html = " ".join(badge_parts)
        if nb:
            nd, ni, nn = nb["days"] - cs, nb["icon"], nb["name"]
            next_badge_html = (
                f"<span style='font-size:11px;color:#94A3B8;margin-left:12px;'>"
                f"{nd} more days for {ni} {nn}</span>"
            )
        else:
            next_badge_html = ""
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:14px;"
            f"padding:12px 20px;display:flex;align-items:center;gap:16px;margin-bottom:1rem;'>"
            f"<div style='font-size:28px;font-weight:700;color:{streak_color};font-family:Sora,sans-serif;'>"
            f"🔥 {cs}</div>"
            f"<div><div style='font-size:13px;font-weight:600;color:#E2E8F0;'>"
            f"{streak_message(streak_data)}</div>"
            f"<div style='margin-top:4px;'>{badges_html}{next_badge_html}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # ── SRS: due cards ────────────────────────────────────────────────────────
    srs_cards = get_srs_cards(email)
    due_cards = get_due_cards(srs_cards)
    if due_cards:
        st.markdown(
            f"<div class='insight-card'>"
            f"<div style='font-size:12px;font-weight:700;color:#D97706;margin-bottom:6px;'>"
            f"⏰ SPACED REPETITION — {len(due_cards)} topic{'s' if len(due_cards)>1 else ''} due for review</div>"
            f"<div style='display:flex;gap:8px;flex-wrap:wrap;'>",
            unsafe_allow_html=True,
        )
        for card in due_cards[:5]:
            label = format_due_label(card)
            if st.button(f"🎯 Review: {card['topic'].title()}", key=f"srs_{card['topic']}"):
                st.session_state.current_topic = card["topic"]
                st.session_state.active_page   = "quiz"
                _sync(); st.rerun()
        st.markdown("</div></div>", unsafe_allow_html=True)

    # ── RAG knowledge base status ─────────────────────────────────────────────
    if rag_available():
        indexed = get_indexed_topics(email)
        if indexed:
            st.markdown(
                f"<div class='info-card'>"
                f"<div style='font-size:11px;font-weight:700;color:#1D4ED8;margin-bottom:4px;'>"
                f"🧠 PERSONAL KNOWLEDGE BASE — {len(indexed)} topics indexed</div>"
                f"<div style='font-size:12px;color:#475569;'>"
                f"AI Tutor answers grounded in: {', '.join(t.title() for t in indexed[:5])}"
                f"{'...' if len(indexed) > 5 else ''}</div></div>",
                unsafe_allow_html=True,
            )

    # ── Stats row ─────────────────────────────────────────────────────────────
    cols = st.columns(5)
    stats = [
        (str(prog["total_quizzes"]),            "Quizzes Taken",   "performance tracked"),
        (f"{round(prog['avg_score'], 1)}%",      "Avg Quiz Score",  "across all topics"),
        (f"{round(prog['mastery_score'], 1)}%",  "Mastery Score",   "rule-based engine"),
        (str(prog["topics_studied"]),            "Topics Studied",  "notes library"),
        (str(prog["sessions_this_week"]),        "Sessions/Week",   "consistency"),
    ]
    for col, (val, lbl, sub) in zip(cols, stats):
        with col:
            stat_card(val, lbl, sub)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Insight cards ─────────────────────────────────────────────────────────
    # Pre-compute all values before passing to insight_card (Python <3.12 compat)
    trend_color = "#059669" if profile["trend"] == "improving" else "#DC2626" if profile["trend"] == "declining" else "#D97706"
    trend_sub   = "⚠️ Try a different approach" if profile.get("stagnation") else ""
    trend_label = profile["trend_label"]

    mastery_val   = profile["mastery_score"]
    mastery_color = "#059669" if mastery_val >= 70 else "#D97706" if mastery_val >= 40 else "#DC2626"
    mastery_label = "Strong" if mastery_val >= 70 else "Building" if mastery_val >= 40 else "Foundational"
    mastery_str   = str(mastery_val) + "% — " + mastery_label

    consist_val   = profile["consistency"]
    consist_color = "#059669" if consist_val >= 60 else "#D97706" if consist_val >= 30 else "#DC2626"
    consist_label = "Excellent" if consist_val >= 80 else "Good" if consist_val >= 60 else "Needs Work"
    sessions_str  = str(profile["sessions_this_week"]) + " sessions this week"

    i1, i2, i3 = st.columns(3)
    with i1:
        insight_card("📈", "LEARNING TREND", trend_label, trend_color, trend_sub)
    with i2:
        insight_card("🎯", "MASTERY LEVEL", mastery_str, mastery_color, bar_pct=int(mastery_val))
    with i3:
        insight_card("⏱️", "CONSISTENCY", consist_label, consist_color, sessions_str)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Smart recommendation ──────────────────────────────────────────────────
    rec_topic, rec_reason, confidence = smart_recommend(
        profile, studied, st.session_state.current_topic
    )
    if rec_topic:
        gaps     = get_learning_gaps(studied, rec_topic)
        conf_pct = f"{int(confidence * 100)}%"
        gaps_html = (
            f"<div style='font-size:12px;color:#FBBF24;'>⚠️ Gaps: <b>{', '.join(gaps)}</b></div>"
            if gaps else ""
        )
        intel_box(
            f"🤖 Smart Recommendation — Rule-Based Engine · Confidence: {conf_pct}",
            f"<div style='font-size:18px;font-weight:700;margin-bottom:4px;'>{rec_topic.title()}</div>"
            f"<div style='font-size:13px;color:#94A3B8;margin-bottom:10px;'>📌 {rec_reason}</div>"
            f"{gaps_html}",
        )

        r1, r2 = st.columns(2)
        with r1:
            if st.button(f"🔁 Start Learning {rec_topic.title()}"):
                st.session_state.current_topic = rec_topic
                st.session_state.active_page   = "youtube"
                _sync(); st.rerun()
        with r2:
            if gaps and st.button("📝 Fix Prerequisites First"):
                st.session_state.current_topic = gaps[0]
                st.session_state.active_page   = "notes"
                _sync(); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick Actions ─────────────────────────────────────────────────────────
    st.markdown("### ⚡ Quick Actions")
    qa_cols = st.columns(5)
    actions = [
        ("▶️", "YouTube Engine",  "AI-ranked videos",        "youtube"),
        ("📝", "Generate Notes",  "Structured learning",     "notes"),
        ("🎯", "Take a Quiz",     "AI questions + analysis", "quiz"),
        ("❓", "Questions",       "Exam-style practice",     "questions"),
        ("🤖", "AI Tutor",        "Personalised guidance",   "chat"),
    ]
    for col, (icon, title, desc, target) in zip(qa_cols, actions):
        with col:
            st.markdown(
                f"<div class='card'><div style='font-size:20px;margin-bottom:6px;'>{icon}</div>"
                f"<div style='font-size:13px;font-weight:600;color:#0F172A;'>{title}</div>"
                f"<div style='font-size:11px;color:#94A3B8;margin-top:2px;'>{desc}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"qa_{target}"):
                st.session_state.active_page = target
                st.rerun()

    # ── Set topic ─────────────────────────────────────────────────────────────
    st.markdown("### 🔄 Set Learning Topic")
    t_col, b_col = st.columns([4, 1])
    with t_col:
        new_topic = st.text_input(
            "", placeholder="Enter topic (e.g. Neural Networks, SQL, React...)",
            label_visibility="collapsed", key="dash_topic",
        )
    with b_col:
        if st.button("Set →"):
            if new_topic.strip():
                st.session_state.current_topic = new_topic.strip()
                _sync(); st.rerun()

    # ── Concept map ───────────────────────────────────────────────────────────
    if st.session_state.current_topic:
        prereqs = get_prerequisites(st.session_state.current_topic)
        if prereqs:
            gaps = get_learning_gaps(studied, st.session_state.current_topic)
            st.markdown(f"### 🗺️ Concept Map — {st.session_state.current_topic.title()}")
            dc1, dc2 = st.columns(2)
            with dc1:
                st.markdown("**✅ Prerequisites covered:**")
                covered = [p for p in prereqs if p not in gaps]
                for p in covered:
                    dep_card(p, covered=True)
                if not covered:
                    st.caption("None detected yet")
            with dc2:
                st.markdown("**⚠️ Prerequisites needed:**")
                for g in gaps:
                    dep_card(g, covered=False)
                if not gaps:
                    st.markdown(
                        "<div class='strong-card'><div style='font-size:13px;color:#065F46;'>🎉 All covered!</div></div>",
                        unsafe_allow_html=True,
                    )

    # ── Recent notes ──────────────────────────────────────────────────────────
    recent_notes = get_notes(email, 4)
    if recent_notes:
        st.markdown("### 📚 Notes Library")
        for n in recent_notes:
            with st.expander(f"📄 {n.get('topic','')} · {n.get('level','')} · {n.get('goal','')}"):
                st.markdown(n.get("notes", ""))
                st.caption(f"Saved: {str(n.get('updated', ''))[:16]}")


def _sync() -> None:
    upsert_user(
        email=st.session_state.user_email,
        name=st.session_state.user_name,
        level=st.session_state.user_level,
        goal=st.session_state.user_goal,
        current_topic=st.session_state.current_topic,
        weak_areas=st.session_state.weak_areas,
    )
