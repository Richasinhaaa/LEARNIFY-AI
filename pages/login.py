# ══════════════════════════════════════════════════════════════════════════════
# pages/login.py — Login / Onboarding Page
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import upsert_user, load_user


def render() -> None:
    """Render the login / onboarding form. Sets session state on success."""
    c1, c2, c3 = st.columns([1, 1.4, 1])

    with c2:
        # Logo header
        st.markdown(
            "<div style='text-align:center;margin-bottom:2rem;padding-top:2rem;'>"
            "<div style='display:inline-flex;align-items:center;gap:12px;'>"
            "<div style='width:52px;height:52px;background:linear-gradient(135deg,#2563EB,#7C3AED);"
            "border-radius:14px;display:flex;align-items:center;justify-content:center;"
            "color:#fff;font-family:Sora,sans-serif;font-weight:700;font-size:24px;'>L</div>"
            "<span style='font-family:Sora,sans-serif;font-weight:700;font-size:30px;color:#0F172A;'>"
            "LEARNIFY <span style='color:#2563EB;'>AI</span></span>"
            "</div>"
            "<p style='color:#2563EB;font-size:14px;font-weight:500;margin-top:10px;'>"
            "Personalized AI Learning · Resource Intelligence Engine · Adaptive Tutor</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Form card
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            "<h3 style='font-family:Sora,sans-serif;font-size:19px;"
            "text-align:center;margin-bottom:1.2rem;color:#0F172A;'>"
            "Start Your Learning Journey 👋</h3>",
            unsafe_allow_html=True,
        )

        name  = st.text_input("Full Name *",  placeholder="Your name")
        email = st.text_input("Email *",      placeholder="you@email.com")

        col_l, col_r = st.columns(2)
        with col_l:
            level = st.selectbox("Your Level", ["Beginner", "Intermediate", "Advanced"])
        with col_r:
            goal  = st.selectbox("Learning Goal", ["Concept Learning", "Exam Preparation", "Quick Revision"])

        topic0 = st.text_input(
            "Starting Topic (optional)",
            placeholder="e.g. Machine Learning, Python, SQL...",
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("Start Learning →"):
            if not name.strip():
                st.error("Please enter your name!")
            elif not email.strip() or "@" not in email:
                st.error("Please enter a valid email!")
            else:
                _login(name.strip(), email.strip(), level, goal, topic0.strip())

        st.markdown(
            "<p style='text-align:center;color:#94A3B8;font-size:12px;margin-top:1rem;'>"
            "Free · No credit card · Intelligence built in ✨</p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _login(name: str, email: str, level: str, goal: str, topic: str) -> None:
    """Persist user and set session state."""
    st.session_state.logged_in     = True
    st.session_state.user_name     = name
    st.session_state.user_email    = email
    st.session_state.user_level    = level
    st.session_state.user_goal     = goal
    st.session_state.current_topic = topic

    # Restore weak areas from previous session if user exists
    existing = load_user(email)
    if existing:
        st.session_state.weak_areas = existing.get("weak_areas", [])

    upsert_user(
        email=email, name=name, level=level, goal=goal,
        current_topic=topic, weak_areas=st.session_state.weak_areas,
    )
    st.rerun()
