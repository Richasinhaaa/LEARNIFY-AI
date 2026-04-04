# ══════════════════════════════════════════════════════════════════════════════
# ui/sidebar.py — Sidebar Navigation
#
# Renders the left navigation sidebar.
# Reading and writing session state is fine here — this is pure UI.
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import upsert_user


# All navigation items: (icon, label, page_key)
_NAV_ITEMS = [
    ("🏠", "Dashboard",      "dashboard"),
    ("▶️", "YouTube Engine", "youtube"),
    ("📝", "AI Notes",       "notes"),
    ("🎯", "Quiz",           "quiz"),
    ("❓", "Questions",      "questions"),
    ("🤖", "AI Tutor",       "chat"),
    ("📅", "Study Planner",  "planner"),
    ("📄", "Upload & Learn", "upload"),
    ("📈", "Results",        "progress"),
]

_LEVELS = ["Beginner", "Intermediate", "Advanced"]
_GOALS  = ["Concept Learning", "Exam Preparation", "Quick Revision"]


def render_sidebar() -> None:
    """Render sidebar navigation and user profile. Sets active_page on click."""
    with st.sidebar:
        _render_logo()
        _render_user_card()
        _render_level_goal_selectors()
        _render_nav_buttons()
        _render_active_topic()
        _render_weak_areas()
        _render_logout()


# ── Private helpers ────────────────────────────────────────────────────────────

def _render_logo() -> None:
    st.markdown(
        "<div style='padding:1.2rem 0.8rem 0.4rem;'>"
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
        "<div style='width:32px;height:32px;background:linear-gradient(135deg,#2563EB,#7C3AED);"
        "border-radius:8px;display:flex;align-items:center;justify-content:center;"
        "color:#fff;font-family:Sora,sans-serif;font-weight:700;font-size:15px;'>L</div>"
        "<span style='font-family:Sora,sans-serif;font-weight:700;font-size:17px;'>LEARNIFY AI</span>"
        "</div>"
        "<p style='font-size:11px;color:#60A5FA;font-weight:500;margin-bottom:0.8rem;'>"
        "Resource Intelligence Engine</p></div>",
        unsafe_allow_html=True,
    )


def _render_user_card() -> None:
    st.markdown(
        "<div style='margin:0 0.8rem 0.8rem;background:#1E293B;border:1px solid #334155;"
        "border-radius:10px;padding:10px 12px;'>"
        f"<div style='font-size:13px;font-weight:600;'>🎓 {st.session_state.user_name}</div>"
        f"<div style='font-size:11px;color:#64748B;margin-top:2px;'>{st.session_state.user_email}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_level_goal_selectors() -> None:
    """Let users change level/goal without navigating away."""
    new_level = st.selectbox(
        "Level", _LEVELS,
        index=_LEVELS.index(st.session_state.user_level),
        key="sb_level",
    )
    new_goal = st.selectbox(
        "Goal", _GOALS,
        index=_GOALS.index(st.session_state.user_goal),
        key="sb_goal",
    )
    # Only write to DB when something actually changed
    if new_level != st.session_state.user_level or new_goal != st.session_state.user_goal:
        st.session_state.user_level = new_level
        st.session_state.user_goal  = new_goal
        _sync_user()


def _render_nav_buttons() -> None:
    st.markdown(
        "<div style='padding:0 0.5rem;'>"
        "<p style='font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;"
        "letter-spacing:.08em;margin:1rem 0 6px;'>Navigation</p></div>",
        unsafe_allow_html=True,
    )
    for icon, label, key in _NAV_ITEMS:
        if st.button(f"{icon} {label}", key=f"nav_{key}", use_container_width=True):
            st.session_state.active_page = key
            st.rerun()


def _render_active_topic() -> None:
    if st.session_state.current_topic:
        st.markdown(
            "<div style='margin:0.8rem 0.5rem;padding:8px 12px;background:#0F2D20;"
            "border-radius:10px;border-left:3px solid #059669;'>"
            "<div style='font-size:10px;color:#34D399;font-weight:700;'>📚 STUDYING</div>"
            f"<div style='font-size:13px;color:#E2E8F0;font-weight:500;margin-top:2px;'>"
            f"{st.session_state.current_topic}</div></div>",
            unsafe_allow_html=True,
        )


def _render_weak_areas() -> None:
    if st.session_state.weak_areas:
        weak_bullets = "<br>".join(
            f"• {w[:36]}" for w in st.session_state.weak_areas[:3]
        )
        st.markdown(
            "<div style='margin:0.4rem 0.5rem;padding:8px 12px;background:#2D0F0F;"
            "border-radius:10px;border-left:3px solid #DC2626;'>"
            "<div style='font-size:10px;color:#F87171;font-weight:700;'>⚠️ WEAK AREAS</div>"
            f"<div style='font-size:12px;color:#FCA5A5;margin-top:4px;'>{weak_bullets}</div>"
            "</div>",
            unsafe_allow_html=True,
        )


def _render_logout() -> None:
    st.markdown(
        "<div style='margin:1rem 0.5rem 0;border-top:1px solid #1E293B;padding-top:1rem;'>",
        unsafe_allow_html=True,
    )
    if st.button("🚪 Logout", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _sync_user() -> None:
    """Persist user preferences to MongoDB."""
    upsert_user(
        email=st.session_state.user_email,
        name=st.session_state.user_name,
        level=st.session_state.user_level,
        goal=st.session_state.user_goal,
        current_topic=st.session_state.current_topic,
        weak_areas=st.session_state.weak_areas,
    )
