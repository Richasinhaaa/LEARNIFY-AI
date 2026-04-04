# ══════════════════════════════════════════════════════════════════════════════
# pages/chat.py — AI Tutor Chat (RAG-enhanced)
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import save_chat, get_chats, get_quizzes, upsert_user
from services import tutor_chat, compute_profile
from services.rag_service import retrieve_context, build_rag_context_block, is_available as rag_available
from services.llm_service import _call as llm_call
from ui.components import back_btn, section_header, topic_banner


def render() -> None:
    back_btn("Daily tutor sessions outperform weekly cramming.", "back_chat")
    section_header("🤖 AI Tutor", "Personalised guidance based on your quiz history and weak areas")
    topic_banner()

    email = st.session_state.user_email

    # ── RAG status indicator ──────────────────────────────────────────────────
    if rag_available():
        st.markdown(
            "<span class='badge b-green'>🧠 RAG Active — answers grounded in your notes</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='badge b-gray'>ℹ️ RAG unavailable — install chromadb & sentence-transformers to enable</span>",
            unsafe_allow_html=True,
        )

    # ── Profile & context ─────────────────────────────────────────────────────
    profile    = compute_profile(get_quizzes(email, 50))
    past_chats = get_chats(email, st.session_state.current_topic, limit=6)

    # ── Show mastery context ──────────────────────────────────────────────────
    m  = profile["mastery_score"]
    mc = "#059669" if m >= 70 else "#D97706" if m >= 40 else "#DC2626"
    st.markdown(
        f"<div class='info-card' style='display:flex;gap:16px;align-items:center;'>"
        f"<div style='font-size:20px;font-weight:700;color:{mc};'>{m}%</div>"
        f"<div><div style='font-size:12px;font-weight:600;color:#0F172A;'>Mastery Level</div>"
        f"<div style='font-size:11px;color:#64748B;'>{profile['trend_label']} · "
        f"Tutor adapts to your level</div></div></div>",
        unsafe_allow_html=True,
    )

    if profile.get("weak_topics"):
        wt = ", ".join(profile["weak_topics"][:3])
        st.markdown(
            f"<div class='weak-card'><div style='font-size:12px;color:#7F1D1D;'>"
            f"⚠️ <b>Weak areas detected:</b> {wt} — Ask me about any of these!</div></div>",
            unsafe_allow_html=True,
        )

    # ── Chat history display ──────────────────────────────────────────────────
    st.markdown("---")
    for msg in st.session_state.chat_history:
        role_class = "chat-row-user" if msg["role"] == "user" else "chat-row-bot"
        bubble_class = "chat-user" if msg["role"] == "user" else "chat-bot"
        st.markdown(
            f"<div class='{role_class}'><div class='{bubble_class}'>{msg['text']}</div></div>",
            unsafe_allow_html=True,
        )

    # ── Input row ─────────────────────────────────────────────────────────────
    ci, cb = st.columns([5, 1])
    with ci:
        user_input = st.text_input(
            "", placeholder="Ask anything about your topic...",
            label_visibility="collapsed", key="chat_input",
        )
    with cb:
        send = st.button("Send →", key="chat_send")

    # Suggested starter questions
    if not st.session_state.chat_history:
        st.markdown("**💡 Try asking:**")
        sug_cols = st.columns(3)
        starters = [
            f"Explain {st.session_state.current_topic or 'my topic'} simply",
            "What are my weakest areas?",
            "Give me a 5-minute revision plan",
        ]
        for i, (col, q) in enumerate(zip(sug_cols, starters)):
            with col:
                if st.button(q, key=f"sug_{i}"):
                    user_input = q
                    send = True

    if send and user_input.strip():
        _send_message(user_input.strip(), profile, past_chats)

    # ── Clear chat button ─────────────────────────────────────────────────────
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


def _send_message(user_input: str, profile: dict, past_chats: list) -> None:
    email = st.session_state.user_email

    # Append user message to history
    st.session_state.chat_history.append({"role": "user", "text": user_input})

    with st.spinner("🤖 Thinking..."):
        # ── RAG: retrieve grounding context from the user's own notes ─────────
        rag_context = ""
        if rag_available():
            chunks = retrieve_context(email, user_input, top_k=3)
            if chunks:
                rag_context = build_rag_context_block(chunks)

        response = tutor_chat(
            user_input=user_input,
            topic=st.session_state.current_topic,
            level=st.session_state.user_level,
            profile=profile,
            chat_history=st.session_state.chat_history,
            weak_areas=st.session_state.weak_areas,
            past_chats=past_chats,
            rag_context=rag_context,   # NEW: injected note context
        )

    st.session_state.chat_history.append({"role": "bot", "text": response})

    # Persist to DB
    save_chat(email, st.session_state.current_topic, user_input, response)
    st.rerun()
