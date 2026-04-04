# ══════════════════════════════════════════════════════════════════════════════
# app.py — Entry Point & Router
#
# Responsibilities (ONLY these):
#   1. Streamlit page config
#   2. Inject global CSS
#   3. Bootstrap session state
#   4. Render sidebar navigation
#   5. Route to the correct page module
#
# Nothing else belongs here. All logic lives in pages/, services/, database/.
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st

from ui.styles import inject_css
from ui.sidebar import render_sidebar
from ui.session import init_session

# ── Page imports ──────────────────────────────────────────────────────────────
from pages import (
    login,
    dashboard,
    youtube,
    notes,
    quiz,
    questions,
    chat,
    planner,
    upload,
    progress,
)

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="LEARNIFY AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Bootstrap ─────────────────────────────────────────────────────────────────
inject_css()
init_session()

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    login.render()
    st.stop()

# ── Sidebar (sets st.session_state.active_page) ───────────────────────────────
render_sidebar()

# ── Router ────────────────────────────────────────────────────────────────────
PAGE_MAP = {
    "dashboard": dashboard,
    "youtube":   youtube,
    "notes":     notes,
    "quiz":      quiz,
    "questions": questions,
    "chat":      chat,
    "planner":   planner,
    "upload":    upload,
    "progress":  progress,
}

page_module = PAGE_MAP.get(st.session_state.active_page, dashboard)
page_module.render()
