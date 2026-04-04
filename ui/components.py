# ══════════════════════════════════════════════════════════════════════════════
# ui/components.py — Shared UI Components
#
# Reusable HTML/Streamlit fragments used across multiple pages.
# Every component is a plain function — no state, no side effects.
# Pages import what they need; nothing is duplicated.
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from datetime import datetime
from services.llm_service import validate_topic, validate_answer, validate_chat_input


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def back_btn(tip: str, key: str) -> None:
    """Render a 'Back to Dashboard' button. Sets a tip message on click."""
    if st.button("⬅️ Back to Dashboard", key=key):
        st.session_state.show_tip    = True
        st.session_state.tip_message = tip
        st.session_state.active_page = "dashboard"
        st.rerun()


def section_header(title: str, subtitle: str = "") -> None:
    """Render a page title + optional subtitle."""
    st.markdown(
        f"<div class='page-title'>{title}</div>"
        + (f"<div class='page-sub'>{subtitle}</div>" if subtitle else ""),
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# BANNERS
# ══════════════════════════════════════════════════════════════════════════════

def topic_banner() -> None:
    """Show the current topic/level/goal as an info strip if a topic is set."""
    if st.session_state.current_topic:
        st.info(
            f"📚 **{st.session_state.current_topic}** · "
            f"{st.session_state.user_level} · "
            f"{st.session_state.user_goal}"
        )


def tip_banner() -> None:
    """Show and clear the one-shot tip message set by back_btn."""
    if st.session_state.show_tip:
        st.success(f"💡 {st.session_state.tip_message}")
        st.session_state.show_tip = False


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATED INPUTS
# Wraps st.text_input / st.text_area with built-in validation + error display.
# Returns (value, is_valid) — pages just check is_valid before calling LLM.
# ══════════════════════════════════════════════════════════════════════════════

def topic_input(
    placeholder: str = "e.g. Gradient Descent, SQL JOINs...",
    value: str = "",
    key: str = "topic_input",
    label: str = "",
) -> tuple:
    """
    Validated topic text input.
    Returns (cleaned_value: str, is_valid: bool).
    Shows an inline error automatically if invalid.
    """
    raw = st.text_input(
        label or "",
        placeholder=placeholder,
        value=value,
        label_visibility="collapsed" if not label else "visible",
        key=key,
    )
    if not raw:
        return "", False
    is_valid, result = validate_topic(raw)
    if not is_valid:
        st.error(f"⚠️ {result}")
        return raw, False
    return result, True


def answer_input(
    placeholder: str = "Type your answer here...",
    height: int = 200,
    key: str = "answer_input",
) -> tuple:
    """
    Validated answer text area.
    Returns (cleaned_value: str, is_valid: bool).
    Shows an inline error automatically if invalid.
    """
    raw = st.text_area(
        "",
        placeholder=placeholder,
        height=height,
        label_visibility="collapsed",
        key=key,
    )
    if not raw:
        return "", False
    is_valid, result = validate_answer(raw)
    if not is_valid:
        st.error(f"⚠️ {result}")
        return raw, False
    return result, True


def chat_input_field(
    placeholder: str = "Ask your tutor...",
    key: str = "chat_input",
) -> tuple:
    """
    Validated chat text input.
    Returns (cleaned_value: str, is_valid: bool).
    """
    raw = st.text_input(
        "",
        placeholder=placeholder,
        label_visibility="collapsed",
        key=key,
    )
    if not raw:
        return "", False
    is_valid, result = validate_chat_input(raw)
    if not is_valid:
        st.error(f"⚠️ {result}")
        return raw, False
    return result, True


# ══════════════════════════════════════════════════════════════════════════════
# METRIC CARDS
# ══════════════════════════════════════════════════════════════════════════════

def stat_card(value: str, label: str, sub: str = "") -> None:
    """Render a single metric stat card."""
    st.markdown(
        f"<div class='stat-card'>"
        f"<div class='stat-label'>{label}</div>"
        f"<div class='stat-value'>{value}</div>"
        f"<div class='stat-sub'>{sub}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def score_circle(pct: int) -> None:
    """Render the circular score badge."""
    st.markdown(
        f"<div class='card' style='text-align:center;padding:2rem;'>"
        f"<div class='score-circle'>"
        f"<div class='score-num'>{pct}%</div>"
        f"<div class='score-lbl'>Score</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# INSIGHT / INFO CARDS
# ══════════════════════════════════════════════════════════════════════════════

def insight_card(
    icon: str,
    label: str,
    value: str,
    color: str,
    sub: str = "",
    bar_pct: int = 0,
) -> None:
    """Render a coloured insight card with optional progress bar."""
    bar = (
        f"<div style='height:6px;background:#E2E8F0;border-radius:4px;margin-top:8px;'>"
        f"<div style='height:6px;border-radius:4px;width:{min(bar_pct, 100)}%;background:{color};'></div>"
        f"</div>"
    ) if bar_pct else ""
    sub_html = (
        "<div style='font-size:12px;color:#94A3B8;margin-top:4px;'>" + sub + "</div>"
    ) if sub else ""
    st.markdown(
        f"<div class='insight-card'>"
        f"<div style='font-size:11px;color:#94A3B8;margin-bottom:5px;'>{icon} {label}</div>"
        f"<div style='font-size:17px;font-weight:700;color:{color};'>{value}</div>"
        f"{sub_html}{bar}</div>",
        unsafe_allow_html=True,
    )


def intel_box(title: str, body_html: str) -> None:
    """Render the dark intelligence explanation box."""
    st.markdown(
        f"<div class='intel-box'>"
        f"<div class='intel-title'>{title}</div>"
        f"{body_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def connector_card(title: str, body: str) -> None:
    """Render the blue/green connector card between sections."""
    st.markdown(
        f"<div class='connector-card'>"
        f"<div style='font-size:13px;font-weight:600;color:#1D4ED8;'>{title}</div>"
        f"<div style='font-size:12px;color:#475569;margin-top:4px;'>{body}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = "blue") -> str:
    """Return a badge HTML string. Use inside intel_box or markdown calls."""
    return f"<span class='badge b-{color}'>{text}</span>"


def plan_card(content: str) -> None:
    """Render a purple plan card (used for AI analysis output)."""
    st.markdown(
        f"<div class='plan-card'>{content}</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# QUIZ COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def quiz_answer_row(question: dict, user_answer_idx: int) -> None:
    """Render a single answered quiz question with correct/wrong styling."""
    is_right    = user_answer_idx == question["ans"]
    bg          = "#ECFDF5" if is_right else "#FEF2F2"
    border      = "#059669" if is_right else "#DC2626"
    icon        = "✅" if is_right else "❌"
    user_text   = question["opts"][user_answer_idx] if user_answer_idx != -1 else "Not answered"
    correct_line = (
        "" if is_right
        else (
            f"<div style='font-size:13px;color:#059669;margin-top:3px;'>"
            f"✓ Correct: {question['opts'][question['ans']]}</div>"
        )
    )
    st.markdown(
        f"<div style='padding:12px;border-radius:12px;margin-bottom:8px;"
        f"border:1.5px solid {border};background:{bg};'>"
        f"<div style='font-size:14px;font-weight:600;color:#0F172A;'>{icon} {question['q']}</div>"
        f"<div style='font-size:13px;color:{border};margin-top:4px;'>{user_text}</div>"
        f"{correct_line}</div>",
        unsafe_allow_html=True,
    )


def question_card(index: int, question: dict) -> None:
    """Render an important question card with type and length badges."""
    type_colors = {
        "Conceptual": "b-blue",
        "Analytical":  "b-purple",
        "Applied":     "b-green",
        "Evaluative":  "b-amber",
    }
    color_class = type_colors.get(
        question.get("type", "Conceptual").split("/")[0].strip(), "b-gray"
    )
    st.markdown(
        f"<div class='q-card'>"
        f"<div style='font-size:14px;font-weight:600;color:#0F172A;'>Q{index}. {question['q']}</div>"
        f"<div class='q-type'>"
        f"<span class='badge {color_class}'>{question.get('type', 'Conceptual')}</span>"
        f"<span class='badge b-gray'>{question.get('length', 'Medium')} answer</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY / PREREQUISITE CARDS
# ══════════════════════════════════════════════════════════════════════════════

def dep_card(topic: str, covered: bool) -> None:
    """Render a prerequisite card — green if covered, red if missing."""
    if covered:
        st.markdown(
            f"<div class='strong-card'>"
            f"<div style='font-size:13px;color:#065F46;'>✅ {topic.title()}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='weak-card'>"
            f"<div style='font-size:13px;color:#7F1D1D;'>❌ {topic.title()}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FILE EXTRACTION UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def extract_pdf(file_bytes: bytes):
    """Extract text from PDF bytes. Returns (text, error_str)."""
    try:
        import io
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        return text.strip(), None
    except ImportError:
        return None, "PyPDF2 not installed. Run: pip install PyPDF2"
    except Exception as e:
        return None, str(e)


def extract_txt(file_bytes: bytes):
    """Decode text file bytes trying common encodings. Returns (text, error_str)."""
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            return file_bytes.decode(enc), None
        except Exception:
            continue
    return None, "Could not decode file"


# ══════════════════════════════════════════════════════════════════════════════
# QUIZ STATE
# ══════════════════════════════════════════════════════════════════════════════

def reset_quiz() -> None:
    """Clear all quiz-related session state keys."""
    st.session_state.quiz_started    = False
    st.session_state.quiz_submitted  = False
    st.session_state.quiz_answers    = {}
    st.session_state.quiz_questions  = []
    st.session_state.quiz_analysis   = ""
    st.session_state.tutor_post_quiz = ""