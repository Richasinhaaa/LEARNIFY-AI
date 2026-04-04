# ══════════════════════════════════════════════════════════════════════════════
# pages/youtube.py — YouTube Resource Intelligence Engine
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
from database import upsert_user, get_quizzes
from services import (
    compute_profile, search_videos, build_placeholders,
    rank_video, build_explanation, video_ai_note,
    LEVEL_KEYWORDS, IDEAL_DURATION,
)
from ui.components import back_btn, section_header, topic_banner, intel_box


_RANK_MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]


def render() -> None:
    back_btn("Focus on 1-2 quality videos — depth beats breadth.", "back_yt")
    section_header(
        "▶️ YouTube Resource Intelligence Engine",
        "Rule-based ranking · AI explanations · Personalised to your level and weak areas",
    )
    topic_banner()

    profile = compute_profile(get_quizzes(st.session_state.user_email, 50))

    # ── Search inputs ─────────────────────────────────────────────────────────
    st.markdown("<div class='topic-box'>", unsafe_allow_html=True)
    yi, yb = st.columns([4, 1])
    with yi:
        yt_topic = st.text_input(
            "", placeholder="Enter topic (e.g. Gradient Descent, React Hooks, SQL JOINs...)",
            value=st.session_state.current_topic,
            label_visibility="collapsed", key="yt_topic",
        )
    with yb:
        do_search = st.button("Find Videos →", key="yt_go")
    st.markdown("</div>", unsafe_allow_html=True)

    levels = ["Beginner", "Intermediate", "Advanced"]
    yt_level = st.radio(
        "Level:", levels,
        index=levels.index(st.session_state.user_level),
        horizontal=True, key="yt_lvl",
    )

    # ── How-it-works explainer (shown before first search) ────────────────────
    if not st.session_state.yt_results and not do_search:
        intel_box(
            "🤖 How our ranking engine works",
            "<div style='font-size:13px;color:#94A3B8;line-height:1.8;'>"
            "Our <b>Resource Intelligence Engine</b> ranks videos using 5 explicit criteria:<br>"
            "• <b>Topic Relevance (0–30 pts)</b> — keyword matching in title &amp; description<br>"
            "• <b>Level Match (0–25 pts)</b> — beginner/intermediate/advanced keyword detection<br>"
            "• <b>Duration Fit (0–20 pts)</b> — ideal duration for your level<br>"
            "• <b>Weak Topic Boost (0–15 pts)</b> — prioritise your weak areas<br>"
            "• <b>Popularity Signal (0–10 pts)</b> — view count proxy<br><br>"
            "Each video gets a <b>Relevance Score out of 100</b>."
            "</div>",
        )

    # ── Trigger search ────────────────────────────────────────────────────────
    if do_search and yt_topic.strip():
        st.session_state.current_topic = yt_topic.strip()
        st.session_state.user_level    = yt_level
        upsert_user(
            email=st.session_state.user_email, name=st.session_state.user_name,
            level=yt_level, goal=st.session_state.user_goal,
            current_topic=yt_topic.strip(), weak_areas=st.session_state.weak_areas,
        )

        weak_topics = (
            profile.get("weak_topics", [])
            + [w[:40] for w in st.session_state.weak_areas[:3]]
        )

        with st.spinner("🤖 Searching, scoring and ranking videos..."):
            raw_videos = search_videos(yt_topic.strip(), yt_level, limit=10)
            used_placeholders = not raw_videos
            if used_placeholders:
                raw_videos = build_placeholders(yt_topic.strip(), yt_level)

        # Score and rank each video
        for v in raw_videos:
            score, breakdown, reasons = rank_video(v, yt_topic.strip(), yt_level, weak_topics)
            v["rank_score"] = score
            v["breakdown"]  = breakdown
            v["reasons"]    = reasons
            v["explanation"] = build_explanation(v, yt_topic.strip(), yt_level, weak_topics, breakdown)
            v["ai_note"]     = video_ai_note(yt_topic.strip(), yt_level, v["title"], weak_topics, score)

        ranked = sorted(raw_videos, key=lambda x: x["rank_score"], reverse=True)[:5]
        st.session_state.yt_results = ranked

        if used_placeholders:
            st.warning(
                "⚠️ Live YouTube search was unavailable. "
                "These are suggested search queries, not real results. "
                "Click 'Watch on YouTube' to search manually."
            )

        st.rerun()

    # ── Display results ───────────────────────────────────────────────────────
    if st.session_state.yt_results:
        _render_intel_panel()
        st.markdown("### 🎥 Ranked Videos (by Relevance Score)")
        vcols = st.columns(2)
        for idx, v in enumerate(st.session_state.yt_results):
            with vcols[idx % 2]:
                _render_video_card(v, idx)


def _render_intel_panel() -> None:
    level = st.session_state.user_level
    lo, hi = IDEAL_DURATION.get(level, (5, 60))
    kws = ", ".join(LEVEL_KEYWORDS.get(level, [])[:4])
    weak_display = ", ".join(st.session_state.weak_areas[:3]) or "None (take a quiz to personalise)"
    topic = st.session_state.current_topic

    intel_box(
        "🧠 How We Selected These Videos",
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;color:#94A3B8;'>"
        f"<tr><td style='padding:4px 8px;font-weight:600;color:#60A5FA;'>Matched Keywords</td>"
        f"<td style='padding:4px 8px;'>{', '.join(topic.lower().split())} + level modifiers</td></tr>"
        f"<tr><td style='padding:4px 8px;font-weight:600;color:#60A5FA;'>Level Filter</td>"
        f"<td style='padding:4px 8px;'>{level} — keywords: {kws}</td></tr>"
        f"<tr><td style='padding:4px 8px;font-weight:600;color:#60A5FA;'>Weak Topics</td>"
        f"<td style='padding:4px 8px;'>{weak_display}</td></tr>"
        f"<tr><td style='padding:4px 8px;font-weight:600;color:#60A5FA;'>Duration Ideal</td>"
        f"<td style='padding:4px 8px;'>{lo}–{hi} minutes for {level}</td></tr>"
        f"</table>",
    )


def _render_video_card(v: dict, idx: int) -> None:
    score     = v.get("rank_score", 0)
    breakdown = v.get("breakdown", {})
    vid_id    = v.get("vid_id", "")
    sc_color  = "#059669" if score >= 70 else "#D97706" if score >= 40 else "#DC2626"

    st.markdown("<div class='yt-card'>", unsafe_allow_html=True)

    # Thumbnail / embed
    if vid_id:
        st.video(f"https://youtube.com/watch?v={vid_id}")
    elif v.get("thumb"):
        st.markdown(
            f"<img src='{v['thumb']}' style='width:100%;height:160px;object-fit:cover;'>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='height:140px;display:flex;align-items:center;justify-content:center;"
            f"font-size:36px;background:{v.get('color','#1e3a8a')};'>▶️</div>",
            unsafe_allow_html=True,
        )

    # Card body
    st.markdown(
        f"<div class='yt-body'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;'>"
        f"<div style='font-size:12px;font-weight:700;'>{_RANK_MEDALS[idx]} Rank #{idx+1}</div>"
        f"<div style='font-size:13px;font-weight:700;color:{sc_color};"
        f"padding:2px 10px;background:{sc_color}18;border-radius:12px;'>Score: {score}/100</div>"
        f"</div>"
        f"<div class='yt-title'>{v['title']}</div>"
        f"<div class='yt-chan'>{v['channel']} · {v.get('views','N/A')} views · {v.get('duration','N/A')}</div>"
        f"<span class='badge b-blue'>{st.session_state.user_level}</span>",
        unsafe_allow_html=True,
    )

    # Score breakdown badges
    bd = breakdown
    st.markdown(
        f"<div style='background:#F8FAFC;border-radius:10px;padding:8px 12px;margin:8px 0;'>"
        f"<div style='font-size:11px;font-weight:600;color:#475569;margin-bottom:6px;'>📊 RELEVANCE BREAKDOWN</div>"
        f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>"
        f"<span class='badge b-blue'>Topic: {bd.get('topic_relevance',0)}/30</span>"
        f"<span class='badge b-purple'>Level: {bd.get('level_match',0)}/25</span>"
        f"<span class='badge b-green'>Duration: {bd.get('duration_fit',0)}/20</span>"
        f"<span class='badge b-amber'>Weak: {bd.get('weak_boost',0)}/15</span>"
        f"<span class='badge b-gray'>Popular: {bd.get('popularity',0)}/10</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # Why recommended
    st.markdown(
        f"<div style='background:#EFF6FF;border-radius:10px;padding:10px 12px;margin-bottom:10px;"
        f"border-left:3px solid #2563EB;'>"
        f"<div style='font-size:11px;font-weight:700;color:#1D4ED8;margin-bottom:4px;'>💡 WHY RECOMMENDED</div>"
        f"<div style='font-size:12px;color:#1E40AF;line-height:1.6;'>{v.get('explanation','')}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # Watch button
    st.markdown(
        f"<a href='{v['url']}' target='_blank'>"
        f"<button style='width:100%;padding:9px;background:linear-gradient(135deg,#2563EB,#7C3AED);"
        f"color:white;border:none;border-radius:10px;cursor:pointer;font-size:13px;"
        f"font-weight:600;margin-bottom:4px;'>▶️ Watch on YouTube</button></a>",
        unsafe_allow_html=True,
    )

    # Notes connector
    if st.button("📝 Generate Notes from This Video", key=f"yt_notes_{idx}"):
        st.session_state.active_page   = "notes"
        st.session_state.notes_yt_url  = v["url"]
        st.session_state.notes_yt_topic = v["title"][:60]
        st.rerun()
