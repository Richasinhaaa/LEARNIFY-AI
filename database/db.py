# ══════════════════════════════════════════════════════════════════════════════
# database/db.py — MongoDB Connection Singleton
#
# Single responsibility: provide a cached database handle.
# No query logic lives here — that belongs in user_repo.py.
#
# Uses st.cache_resource so the MongoClient is reused across Streamlit reruns.
# Returns None gracefully when MongoDB is unavailable (app degrades, not crash).
# ══════════════════════════════════════════════════════════════════════════════

import os
import streamlit as st

try:
    from pymongo import MongoClient
    from pymongo.database import Database
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Read connection string from environment / Streamlit secrets
MONGO_URI: str = os.getenv("MONGO_URI", "")


@st.cache_resource(show_spinner=False)
def get_database():
    """
    Return a connected MongoDB database handle, or None if unavailable.

    Cached at the Streamlit resource level — connection is reused across all
    reruns. Warnings shown only ONCE because this function is cached.
    """
    if not MONGO_AVAILABLE:
        return None   # Silent — pymongo missing is expected in some envs

    if not MONGO_URI:
        return None   # Silent — .env not set yet (user sees info on dashboard)

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        client.server_info()  # validate connection immediately
        return client["learnify"]
    except Exception:
        return None   # Silent — UI handles the degraded state
