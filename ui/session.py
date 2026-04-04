# ══════════════════════════════════════════════════════════════════════════════
# ui/session.py — Streamlit Session State Bootstrap
#
# Defines ALL session state keys and their defaults in one place.
# Called once from app.py before any page renders.
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from datetime import datetime

# Greeting helper — used by dashboard
def greet() -> str:
    h = datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"


def init_session() -> None:
    """
    Set default values for every session key used by the app.
    Only sets keys that don't already exist (preserves state across reruns).
    """
    defaults = {
        # Auth
        "logged_in":   False,
        "user_name":   "",
        "user_email":  "",
        # Navigation
        "active_page": "dashboard",
        # User preferences
        "current_topic": "",
        "user_level":    "Beginner",
        "user_goal":     "Concept Learning",

        "weak_areas":    [],
        "chat_history":  [],
        # Quiz state
        "quiz_started":    False,
        "quiz_answers":    {},
        "quiz_submitted":  False,
        "quiz_questions":  [],
        "quiz_analysis":   "",
        "quiz_topic":      "",
        "tutor_post_quiz": "",
        "last_quiz_wrong": [],
        # Notes state
        "notes_output":    "",
        "notes_yt_url":    "",
        "notes_yt_topic":  "",
        # YouTube state
        "yt_results":      [],
        # Important questions state
        "imp_questions":   [],
        # Evaluation state
        "eval_result":     "",
        "eval_score":      0.0,
        "tutor_post_eval": "",
        # Study plan state
        "study_plan_output":    "",
        "study_plan_structure": [],
        # Upload state
        "uploaded_text":     "",
        "uploaded_filename": "",
        # Dashboard tip banner
        "show_tip":    False,
        "tip_message": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
