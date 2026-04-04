# ══════════════════════════════════════════════════════════════════════════════
# pages/upload.py — Upload & Learn (PDF / TXT)
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_note, upsert_user
from services import notes_from_document, generate_quiz, parse_quiz
from ui.components import (
    back_btn, section_header, reset_quiz, extract_pdf, extract_txt,
)


def render() -> None:
    back_btn("Upload your syllabus or textbook and let AI extract the key points.", "back_upload")
    section_header("📄 Upload & Learn", "Upload PDFs or text files — AI generates notes and quizzes from YOUR material")

    st.markdown("<div class='upload-box'>", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop a PDF or TXT file",
        type=["pdf", "txt"],
        key="upload_file",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded:
        fb  = uploaded.read()
        ext = uploaded.name.lower().split(".")[-1]

        with st.spinner("Extracting text..."):
            text, err = extract_pdf(fb) if ext == "pdf" else extract_txt(fb)

        if err:
            st.error(f"Could not read file: {err}")
            return

        if not text:
            st.warning("The file appears to be empty.")
            return

        st.success(f"✅ Extracted **{len(text):,}** characters from **{uploaded.name}**")
        st.session_state.uploaded_text     = text
        st.session_state.uploaded_filename = uploaded.name

        # Topic override
        u1, u2 = st.columns([3, 1])
        with u1:
            override_topic = st.text_input(
                "Topic label (optional)",
                placeholder="e.g. Chapter 3 — Binary Trees",
                key="upload_topic",
            )
        with u2:
            level = st.selectbox(
                "Level", ["Beginner", "Intermediate", "Advanced"],
                index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.user_level),
                key="upload_lvl",
            )

        ub1, ub2 = st.columns(2)
        with ub1:
            gen_notes = st.button("📝 Generate Notes from File →", key="upload_notes")
        with ub2:
            gen_quiz  = st.button("🎯 Generate Quiz from File →", key="upload_quiz")

        topic_label = override_topic.strip() or uploaded.name.rsplit(".", 1)[0]

        if gen_notes:
            st.session_state.current_topic = topic_label
            upsert_user(
                email=st.session_state.user_email, name=st.session_state.user_name,
                level=level, goal=st.session_state.user_goal,
                current_topic=topic_label, weak_areas=st.session_state.weak_areas,
            )
            with st.spinner("🤖 Generating notes from document..."):
                notes = notes_from_document(
                    text, uploaded.name, level, st.session_state.user_goal
                )
            save_note(
                st.session_state.user_email, topic_label, notes,
                level, st.session_state.user_goal, "upload",
            )
            st.session_state.notes_output = notes
            st.markdown("### 📄 Generated Notes")
            st.markdown(notes)
            st.download_button(
                "📌 Download Notes", notes,
                file_name=f"{topic_label}_notes.md", mime="text/markdown",
            )

        if gen_quiz:
            st.session_state.current_topic = topic_label
            with st.spinner("🤖 Generating quiz from document..."):
                # Pass document context to quiz generator
                raw = generate_quiz(topic_label, level, context=text[:1200])
                qs  = parse_quiz(raw)

            if not qs:
                st.error("Quiz generation failed — please try again.")
                return

            st.session_state.quiz_questions = qs
            st.session_state.quiz_topic     = topic_label
            st.session_state.quiz_started   = True
            st.session_state.quiz_submitted = False
            st.session_state.quiz_answers   = {}
            st.session_state.active_page    = "quiz"
            reset_quiz()
            # Re-inject questions (reset_quiz clears them)
            st.session_state.quiz_questions = qs
            st.session_state.quiz_started   = True
            st.session_state.quiz_topic     = topic_label
            st.rerun()
