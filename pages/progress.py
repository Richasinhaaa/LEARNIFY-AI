# ══════════════════════════════════════════════════════════════════════════════
# pages/progress.py — Results & Analytics Dashboard
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import get_progress, get_quizzes, get_evals, get_notes
from services import compute_profile
from ui.components import back_btn, section_header, stat_card, insight_card


def render() -> None:
    back_btn("Progress tracking keeps you accountable.", "back_progress")
    section_header("📈 Results & Analytics", "Your learning journey — quiz scores, mastery, consistency")

    email   = st.session_state.user_email
    prog    = get_progress(email)
    quizzes = get_quizzes(email, 50)
    evals   = get_evals(email, 10)
    notes   = get_notes(email, 20)
    profile = compute_profile(quizzes)

    if prog["total_quizzes"] == 0 and not notes:
        st.info("No data yet. Take a quiz or generate notes to see your progress here.")
        return

    # ── Overview stats ────────────────────────────────────────────────────────
    st.markdown("### 📊 Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: stat_card(str(prog["total_quizzes"]),            "Quizzes",       "attempts")
    with c2: stat_card(f"{prog['avg_score']}%",               "Avg Score",     "all quizzes")
    with c3: stat_card(f"{prog['mastery_score']}%",           "Mastery",       "composite")
    with c4: stat_card(str(prog["topics_studied"]),           "Topics",        "with notes")
    with c5: stat_card(str(prog["total_evals"]),              "Evaluations",   "answers graded")

    # ── Trend & consistency ───────────────────────────────────────────────────
    st.markdown("### 🧠 Intelligence Insights")
    ti1, ti2, ti3 = st.columns(3)

    with ti1:
        tc = "#059669" if profile["trend"] == "improving" else "#DC2626" if profile["trend"] == "declining" else "#D97706"
        insight_card("📈", "LEARNING TREND", profile["trend_label"], tc,
                     "⚠️ Try a new approach" if profile.get("stagnation") else "")

    with ti2:
        m  = profile["mastery_score"]
        mc = "#059669" if m >= 70 else "#D97706" if m >= 40 else "#DC2626"
        ml = "Strong" if m >= 70 else "Building" if m >= 40 else "Foundational"
        insight_card("🎯", "MASTERY", f"{m}% — {ml}", mc, bar_pct=int(m))

    with ti3:
        c  = prog["consistency"]
        cc = "#059669" if c >= 60 else "#D97706" if c >= 30 else "#DC2626"
        cl = "Excellent" if c >= 80 else "Good" if c >= 60 else "Needs Work"
        insight_card("⏱️", "CONSISTENCY", cl, cc, f"{prog['sessions_this_week']} sessions this week")

    # ── Topic scores ─────────────────────────────────────────────────────────
    if profile["topic_scores"]:
        st.markdown("### 📚 Per-Topic Scores")
        ts = profile["topic_scores"]
        sorted_topics = sorted(ts.items(), key=lambda x: -x[1])
        for topic, score in sorted_topics:
            bar_color = "#059669" if score >= 80 else "#D97706" if score >= 60 else "#DC2626"
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
                f"<div style='width:160px;font-size:13px;color:#0F172A;font-weight:500;'>{topic.title()}</div>"
                f"<div style='flex:1;background:#E2E8F0;border-radius:4px;height:8px;'>"
                f"<div style='width:{score}%;background:{bar_color};border-radius:4px;height:8px;'></div>"
                f"</div>"
                f"<div style='font-size:13px;font-weight:600;color:{bar_color};width:40px;text-align:right;'>"
                f"{score}%</div></div>",
                unsafe_allow_html=True,
            )

    # ── Weak & strong topics ──────────────────────────────────────────────────
    wk1, wk2 = st.columns(2)
    with wk1:
        if prog["weak_topics"]:
            st.markdown("### ⚠️ Needs Work")
            for t in prog["weak_topics"]:
                score = profile["topic_scores"].get(t, 0)
                st.markdown(
                    f"<div class='weak-card'><div style='font-size:13px;color:#7F1D1D;'>"
                    f"❌ {t.title()} — {score}%</div></div>",
                    unsafe_allow_html=True,
                )
    with wk2:
        if prog["strong_topics"]:
            st.markdown("### ✅ Mastered")
            for t in prog["strong_topics"]:
                score = profile["topic_scores"].get(t, 0)
                st.markdown(
                    f"<div class='strong-card'><div style='font-size:13px;color:#065F46;'>"
                    f"✅ {t.title()} — {score}%</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Quiz history ──────────────────────────────────────────────────────────
    if quizzes:
        st.markdown("### 🎯 Recent Quiz History")
        for q in quizzes[:10]:
            pct = q.get("pct", 0)
            c   = "#059669" if pct >= 80 else "#D97706" if pct >= 60 else "#DC2626"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:8px 12px;border-radius:10px;background:#F8FAFC;margin-bottom:6px;"
                f"border:0.5px solid #E2E8F0;'>"
                f"<div style='font-size:13px;color:#0F172A;font-weight:500;'>{q.get('topic','').title()}</div>"
                f"<div style='font-size:13px;font-weight:700;color:{c};'>{pct}%</div>"
                f"<div style='font-size:11px;color:#94A3B8;'>{str(q.get('time',''))[:10]}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Evaluation history ────────────────────────────────────────────────────
    if evals:
        st.markdown("### 📝 Recent Evaluations")
        for e in evals[:5]:
            score = e.get("score", 0)
            c     = "#059669" if score >= 7 else "#D97706" if score >= 4 else "#DC2626"
            with st.expander(f"Q: {e.get('question','')[:70]}... | Score: {score}/10"):
                st.markdown(e.get("evaluation", ""))
