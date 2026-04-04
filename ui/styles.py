# ══════════════════════════════════════════════════════════════════════════════
# ui/styles.py — Global CSS
#
# Single source of truth for all styling.
# Called once from app.py via inject_css().
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=DM+Sans:wght@400;500&display=swap');

*, html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; box-sizing: border-box; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
section[data-testid="stSidebar"] { background: #0F172A; border-right: none; }
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }

/* Buttons */
.stButton > button {
  background: linear-gradient(135deg, #2563EB, #7C3AED) !important;
  color: white !important; border: none !important; border-radius: 10px !important;
  font-family: 'Sora', sans-serif !important; font-weight: 600 !important;
  width: 100% !important; padding: 0.55rem 1rem !important;
  transition: all 0.2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }

/* Cards */
.card { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px; padding:1.4rem 1.6rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
.card-dark { background:#1E293B; border:1px solid #334155; border-radius:16px; padding:1.4rem 1.6rem; margin-bottom:1rem; }
.stat-card { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:14px; padding:1.1rem 1.2rem; text-align:center; }
.stat-value { font-family:'Sora',sans-serif; font-size:24px; font-weight:700; color:#0F172A; }
.stat-label { font-size:11px; color:#94A3B8; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.05em; }
.stat-sub   { font-size:11px; color:#059669; margin-top:2px; }

/* Badges */
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; margin-right:4px; }
.b-blue   { background:#EFF6FF; color:#2563EB; }
.b-green  { background:#ECFDF5; color:#059669; }
.b-amber  { background:#FFFBEB; color:#D97706; }
.b-purple { background:#F5F3FF; color:#7C3AED; }
.b-red    { background:#FEF2F2; color:#DC2626; }
.b-gray   { background:#F1F5F9; color:#475569; }

/* Typography */
.page-title { font-family:'Sora',sans-serif; font-size:24px; font-weight:700; color:#0F172A; margin-bottom:4px; }
.page-sub   { font-size:14px; color:#64748B; margin-bottom:1rem; }
.tagline    { font-size:14px; color:#2563EB; font-weight:500; margin-bottom:1.4rem; }
.section-title { font-family:'Sora',sans-serif; font-size:16px; font-weight:700; color:#0F172A; margin:1.2rem 0 0.6rem; }

/* Topic input box */
.topic-box { background:linear-gradient(135deg,#EFF6FF,#F5F3FF); border:1.5px solid rgba(37,99,235,0.2); border-radius:14px; padding:1.3rem; margin-bottom:1rem; }

/* Chat bubbles */
.chat-bot  { background:#F1F5F9; color:#0F172A; border-radius:16px 16px 16px 4px; padding:10px 14px; font-size:14px; line-height:1.7; max-width:84%; margin-bottom:8px; display:inline-block; }
.chat-user { background:linear-gradient(135deg,#2563EB,#7C3AED); color:#fff; border-radius:16px 16px 4px 16px; padding:10px 14px; font-size:14px; line-height:1.7; max-width:84%; margin-bottom:8px; display:inline-block; }
.chat-row-bot  { display:flex; justify-content:flex-start; margin-bottom:6px; }
.chat-row-user { display:flex; justify-content:flex-end;   margin-bottom:6px; }

/* YouTube */
.yt-card { background:#fff; border:1px solid #E2E8F0; border-radius:14px; overflow:hidden; margin-bottom:1rem; transition:transform 0.2s,box-shadow 0.2s; }
.yt-card:hover { transform:translateY(-2px); box-shadow:0 8px 24px rgba(0,0,0,0.08); }
.yt-body  { padding:12px 14px; }
.yt-title { font-size:13.5px; font-weight:600; color:#0F172A; margin-bottom:4px; line-height:1.4; }
.yt-chan  { font-size:12px; color:#94A3B8; margin-bottom:8px; }

/* Score circle */
.score-circle { width:100px; height:100px; border-radius:50%; background:linear-gradient(135deg,#2563EB,#7C3AED); display:flex; flex-direction:column; align-items:center; justify-content:center; color:#fff; margin:0 auto 1rem; }
.score-num { font-family:'Sora',sans-serif; font-size:26px; font-weight:700; }
.score-lbl { font-size:10px; opacity:0.85; }

/* Status cards */
.weak-card    { background:#FEF2F2; border:1px solid #FECACA; border-radius:12px; padding:0.9rem; margin-bottom:0.6rem; }
.strong-card  { background:#ECFDF5; border:1px solid #BBF7D0; border-radius:12px; padding:0.9rem; margin-bottom:0.6rem; }
.plan-card    { background:#F5F3FF; border:1px solid #DDD6FE; border-radius:12px; padding:1rem;   margin-bottom:0.8rem; }
.insight-card { background:#FFFBEB; border:1px solid #FDE68A; border-radius:12px; padding:0.9rem; margin-bottom:0.6rem; }
.info-card    { background:#EFF6FF; border:1px solid #BFDBFE; border-radius:12px; padding:0.9rem; margin-bottom:0.6rem; }
.dep-card     { background:#F0F9FF; border:1px solid #BAE6FD; border-radius:10px; padding:8px 12px; margin-bottom:4px; font-size:13px; }

/* Intel dark box */
.intel-box { background:linear-gradient(135deg,#1E293B,#0F172A); border:1px solid #334155; border-radius:14px; padding:1.2rem; margin-bottom:1rem; }
.intel-box * { color:#E2E8F0 !important; }
.intel-title { font-family:'Sora',sans-serif; font-size:13px; font-weight:600; color:#60A5FA !important; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.06em; }

/* Question card */
.q-card { background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #2563EB; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
.q-type { font-size:11px; font-weight:600; color:#7C3AED; margin-top:4px; }

/* Connector */
.connector-card { background:linear-gradient(135deg,#EFF6FF,#F0FDF4); border:1px solid #BFDBFE; border-radius:12px; padding:1rem 1.2rem; margin:1rem 0; }

/* Day plan */
.day-card   { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:1rem; margin-bottom:0.8rem; }
.day-header { font-family:'Sora',sans-serif; font-size:14px; font-weight:700; color:#0F172A; margin-bottom:8px; }
</style>
"""


def inject_css() -> None:
    """Inject global CSS. Call once from app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)
