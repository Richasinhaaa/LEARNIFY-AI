# ══════════════════════════════════════════════════════════════════════════════
# pages/notes.py — AI Notes Generator
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_note, get_notes, upsert_user, log_activity
from services import generate_notes, notes_from_document
from services.rag_service import index_note, is_available as rag_available
from ui.components import back_btn, section_header, topic_banner, reset_quiz, extract_pdf, extract_txt


def render() -> None:
    back_btn("Review notes within 24 hours — improves retention by 80%.", "back_notes")
    section_header("📝 AI Notes Generator", "Structured, personalised notes — not generic AI output")
    topic_banner()

    tab1, tab2, tab3 = st.tabs(["📌 From Topic", "▶️ From YouTube URL", "📚 Saved Notes"])

    with tab1:
        _from_topic_tab()

    with tab2:
        _from_youtube_tab()

    with tab3:
        _saved_notes_tab()

    # ── Output panel ──────────────────────────────────────────────────────────
    if st.session_state.notes_output:
        st.markdown("---")
        st.markdown("### 📄 Your Notes")
        st.markdown(st.session_state.notes_output)

        na, nb, nc = st.columns(3)
        with na:
            st.download_button(
                "📌 Download Notes",
                st.session_state.notes_output,
                file_name="learnify_notes.md",
                mime="text/markdown",
            )
        with nb:
            if st.button("🔁 Regenerate", key="regen"):
                st.session_state.notes_output = ""
                st.rerun()
        with nc:
            if st.button("🎯 Quiz Me on This", key="notes_quiz"):
                reset_quiz()
                st.session_state.active_page = "quiz"
                st.rerun()

        st.markdown(
            "<div class='connector-card'>"
            "<div style='font-size:13px;font-weight:600;color:#1D4ED8;'>📌 Notes → Quiz Flow</div>"
            "<div style='font-size:12px;color:#475569;margin-top:4px;'>Test your understanding with an AI quiz.</div>"
            "</div>",
            unsafe_allow_html=True,
        )


# ── Sub-tabs ──────────────────────────────────────────────────────────────────

def _from_topic_tab() -> None:
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)
    topic = st.text_input(
        "", placeholder="e.g. Gradient Descent, Binary Trees, SQL JOINs...",
        value=st.session_state.current_topic,
        label_visibility="collapsed", key="n_topic",
    )
    nc1, nc2 = st.columns(2)
    with nc1:
        level = st.selectbox(
            "Level", ["Beginner", "Intermediate", "Advanced"],
            index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.user_level),
            key="n_lvl",
        )
    with nc2:
        goal = st.selectbox(
            "Goal", ["Concept Learning", "Exam Preparation", "Quick Revision"],
            index=["Concept Learning", "Exam Preparation", "Quick Revision"].index(st.session_state.user_goal),
            key="n_goal",
        )
    gen = st.button("Generate Structured Notes →", key="gen_n1")
    st.markdown("</div>", unsafe_allow_html=True)

    if not topic and not st.session_state.notes_output:
        st.info("💡 Enter any topic — notes are tailored to your level and goal.")

    if gen and topic.strip():
        st.session_state.current_topic = topic.strip()
        st.session_state.user_level    = level
        st.session_state.user_goal     = goal
        _persist()
        with st.spinner(f"🤖 Generating {goal} notes on {topic}..."):
            notes = generate_notes(topic.strip(), level, goal)
        st.session_state.notes_output = notes
        save_note(st.session_state.user_email, topic.strip(), notes, level, goal, "topic")
        log_activity(st.session_state.user_email)
        # Auto-index into RAG knowledge base
        if rag_available():
            index_note(st.session_state.user_email, topic.strip(), notes)
            st.toast("🧠 Notes indexed into your personal knowledge base", icon="✅")


def _from_youtube_tab() -> None:
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)
    yt_url = st.text_input(
        "", placeholder="https://youtube.com/watch?v=...",
        value=st.session_state.get("notes_yt_url", ""),
        label_visibility="collapsed", key="n_url",
    )
    yt_topic = st.text_input(
        "", placeholder="What is this video about?",
        value=st.session_state.get("notes_yt_topic", ""),
        label_visibility="collapsed", key="n_url_t",
    )
    gen = st.button("Extract Notes from Video →", key="gen_n2")
    st.markdown("</div>", unsafe_allow_html=True)

    if not yt_url:
        st.info("🎬 Paste any YouTube URL — get structured notes without watching the full video.")

    if gen and yt_url.strip():
        t = yt_topic.strip() or "Video Content"
        st.session_state.current_topic = t
        _persist()
        with st.spinner(f"🤖 Generating notes on {t}..."):
            notes = notes_from_document(
                f"YouTube video about: {t}\nURL: {yt_url}",
                f"YouTube: {t}",
                st.session_state.user_level,
                st.session_state.user_goal,
            )
        st.session_state.notes_output  = notes
        st.session_state.notes_yt_url  = ""
        st.session_state.notes_yt_topic = ""
        save_note(st.session_state.user_email, f"{t} (video)", notes,
                  st.session_state.user_level, st.session_state.user_goal, "youtube")


def _saved_notes_tab() -> None:
    saved = get_notes(st.session_state.user_email)
    if saved:
        for s in saved:
            with st.expander(f"📄 {s.get('topic','')} · {s.get('level','')} · {s.get('goal','')}"):
                st.markdown(s.get("notes", ""))
                st.caption(f"Saved: {str(s.get('updated',''))[:16]} · {s.get('source','topic')}")
    else:
        st.info("No saved notes yet.")


def _persist() -> None:
    upsert_user(
        email=st.session_state.user_email,
        name=st.session_state.user_name,
        level=st.session_state.user_level,
        goal=st.session_state.user_goal,
        current_topic=st.session_state.current_topic,
        weak_areas=st.session_state.weak_areas,
    )
