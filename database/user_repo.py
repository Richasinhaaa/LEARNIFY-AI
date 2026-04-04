# ══════════════════════════════════════════════════════════════════════════════
# database/user_repo.py — Repository Layer (all MongoDB queries)
#
# This is the ONLY file that writes MongoDB queries.
# Every function:
#   - Accepts plain Python types (str, int, list)
#   - Returns plain Python types or None / []
#   - Wraps every DB call in try/except — the app NEVER crashes on DB failure
#   - Never imports streamlit — this is pure data logic
#
# Pattern: Repository pattern — callers don't know MongoDB exists.
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Optional, Dict, Any

from database.db import get_database
from models.user_model import LearnerProfile


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper — avoids repeating get_database() guard in every function
# ─────────────────────────────────────────────────────────────────────────────

def _db():
    """Return the database handle. Functions check for None before querying."""
    return get_database()


# ══════════════════════════════════════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════════════════════════════════════

def upsert_user(
    email: str,
    name: str,
    level: str,
    goal: str,
    current_topic: str,
    weak_areas: List[str],
) -> None:
    """Create or update a user document. Silently no-ops if DB unavailable."""
    db = _db()
    if not db:
        return
    try:
        db.users.update_one(
            {"email": email},
            {"$set": {
                "name": name,
                "email": email,
                "level": level,
                "goal": goal,
                "current_topic": current_topic,
                "weak_areas": weak_areas,
                "last_seen": datetime.now(),
            }},
            upsert=True,
        )
    except Exception:
        pass  # Non-fatal: the user just won't be persisted this call


def load_user(email: str) -> Dict[str, Any]:
    """Return user document dict, or empty dict if not found / DB unavailable."""
    db = _db()
    if not db:
        return {}
    try:
        return db.users.find_one({"email": email}) or {}
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# NOTES
# ══════════════════════════════════════════════════════════════════════════════

def save_note(
    email: str,
    topic: str,
    notes: str,
    level: str,
    goal: str,
    source: str = "topic",
) -> None:
    """Upsert a note for (email, topic). One note per topic per user."""
    db = _db()
    if not db:
        return
    try:
        db.notes.update_one(
            {"email": email, "topic": topic},
            {"$set": {
                "notes": notes,
                "level": level,
                "goal": goal,
                "source": source,
                "updated": datetime.now(),
            }},
            upsert=True,
        )
    except Exception:
        pass


def get_notes(email: str, limit: int = 10) -> List[Dict]:
    """Return the most recently updated notes for a user."""
    db = _db()
    if not db:
        return []
    try:
        return list(
            db.notes.find({"email": email})
            .sort("updated", -1)
            .limit(limit)
        )
    except Exception:
        return []


def get_studied_topics(email: str) -> List[str]:
    """Return list of distinct topic names the user has saved notes for."""
    db = _db()
    if not db:
        return []
    try:
        return db.notes.distinct("topic", {"email": email})
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# QUIZ
# ══════════════════════════════════════════════════════════════════════════════

def save_quiz(
    email: str,
    topic: str,
    correct: int,
    total: int,
    wrong: List[str],
) -> None:
    """Insert a new quiz attempt. Each attempt is a separate document."""
    db = _db()
    if not db:
        return
    try:
        pct = int(correct / total * 100) if total else 0
        db.quizzes.insert_one({
            "email": email,
            "topic": topic,
            "score": correct,
            "total": total,
            "pct": pct,
            "wrong": wrong,
            "time": datetime.now(),
        })
    except Exception:
        pass


def get_quizzes(email: str, limit: int = 50) -> List[Dict]:
    """Return recent quiz attempts for analytics computation."""
    db = _db()
    if not db:
        return []
    try:
        return list(
            db.quizzes.find({"email": email})
            .sort("time", -1)
            .limit(limit)
        )
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATIONS
# ══════════════════════════════════════════════════════════════════════════════

def save_eval(
    email: str,
    question: str,
    answer: str,
    evaluation: str,
    score: float,
) -> None:
    """Store a subjective answer evaluation result."""
    db = _db()
    if not db:
        return
    try:
        db.evals.insert_one({
            "email": email,
            "question": question[:200],
            "answer_preview": answer[:200],
            "evaluation": evaluation,
            "score": score,
            "time": datetime.now(),
        })
    except Exception:
        pass


def get_evals(email: str, limit: int = 10) -> List[Dict]:
    db = _db()
    if not db:
        return []
    try:
        return list(
            db.evals.find({"email": email})
            .sort("time", -1)
            .limit(limit)
        )
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# CHAT HISTORY
# ══════════════════════════════════════════════════════════════════════════════

def save_chat(email: str, topic: str, user_msg: str, bot_msg: str) -> None:
    db = _db()
    if not db:
        return
    try:
        db.chats.insert_one({
            "email": email,
            "topic": topic,
            "user": user_msg,
            "bot": bot_msg,
            "time": datetime.now(),
        })
    except Exception:
        pass


def get_chats(email: str, topic: str = "", limit: int = 6) -> List[Dict]:
    db = _db()
    if not db:
        return []
    try:
        query: Dict[str, Any] = {"email": email}
        if topic:
            query["topic"] = topic
        return list(
            db.chats.find(query)
            .sort("time", -1)
            .limit(limit)
        )
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# STUDY PLANS
# ══════════════════════════════════════════════════════════════════════════════

def save_plan(email: str, topic: str, plan_text: str, days: int) -> None:
    db = _db()
    if not db:
        return
    try:
        db.plans.update_one(
            {"email": email, "topic": topic},
            {"$set": {"plan": plan_text, "days": days, "created": datetime.now()}},
            upsert=True,
        )
    except Exception:
        pass


def get_plans(email: str) -> List[Dict]:
    db = _db()
    if not db:
        return []
    try:
        return list(
            db.plans.find({"email": email})
            .sort("created", -1)
            .limit(5)
        )
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS — Progress Profile
# ══════════════════════════════════════════════════════════════════════════════

def get_progress(email: str) -> Dict[str, Any]:
    """
    Compute a full progress profile from all quiz history.
    This is a read-heavy analytics query — not cached here;
    callers can cache with st.cache_data if needed.
    """
    db = _db()
    if not db:
        return _empty_progress()

    try:
        quizzes = list(db.quizzes.find({"email": email}))
        evals = list(db.evals.find({"email": email}))
        notes_count = db.notes.count_documents({"email": email})
        topics = db.notes.distinct("topic", {"email": email})
        user = db.users.find_one({"email": email}) or {}

        topic_scores: Dict[str, List[float]] = defaultdict(list)
        pcts: List[float] = []

        for q in quizzes:
            p = q.get("pct", 0)
            pcts.append(p)
            topic_scores[q.get("topic", "unknown")].append(p)

        # Per-topic averages
        ts_avg = {t: round(sum(s) / len(s), 1) for t, s in topic_scores.items()}
        weak_topics = sorted([t for t, s in ts_avg.items() if s < 60], key=lambda t: ts_avg[t])
        strong_topics = [t for t, s in ts_avg.items() if s >= 80]

        avg_score = round(sum(pcts) / len(pcts), 1) if pcts else 0
        mastery = min(100, round(avg_score * 0.7 + len(strong_topics) * 5, 1))

        # Trend detection (need ≥6 quizzes)
        trend, trend_label, improvement_rate = "new", "Just Starting", 0.0
        if len(pcts) >= 6:
            recent = sum(pcts[:5]) / 5
            prev = sum(pcts[5:10]) / min(5, len(pcts[5:]))
            improvement_rate = round(recent - prev, 1)
            if improvement_rate >= 8:
                trend, trend_label = "improving", "Improving ↑"
            elif improvement_rate <= -8:
                trend, trend_label = "declining", "Needs Attention ↓"
            else:
                trend, trend_label = "consistent", "Consistent →"

        # Stagnation: last 5 quizzes all within 10% range and avg < 70
        stagnation = False
        if len(pcts) >= 5:
            v5 = pcts[:5]
            if max(v5) - min(v5) < 10 and avg_score < 70:
                stagnation = True

        # Sessions this week
        week_ago = datetime.now() - timedelta(days=7)
        sessions_this_week = sum(1 for q in quizzes if q.get("time", datetime.now()) > week_ago)
        consistency = min(100, sessions_this_week * 20)

        # Persistently wrong questions (wrong in ≥2 quizzes)
        wrong_freq: Dict[str, int] = defaultdict(int)
        for q in quizzes:
            for wq in q.get("wrong", []):
                wrong_freq[wq[:60]] += 1
        persistent_weak = [q for q, c in sorted(wrong_freq.items(), key=lambda x: -x[1]) if c >= 2]

        # Eval average score
        eval_scores = [e.get("score", 0) for e in evals if e.get("score")]
        eval_avg = round(sum(eval_scores) / len(eval_scores), 1) if eval_scores else 0.0

        return {
            "mastery_score": mastery,
            "avg_score": avg_score,
            "trend": trend,
            "trend_label": trend_label,
            "consistency": consistency,
            "total_quizzes": len(quizzes),
            "total_evals": len(evals),
            "weak_topics": weak_topics[:5],
            "strong_topics": strong_topics[:5],
            "topic_scores": ts_avg,
            "stagnation": stagnation,
            "sessions_this_week": sessions_this_week,
            "improvement_rate": improvement_rate,
            "topics_studied": len(topics),
            "notes_saved": notes_count,
            "weak_areas": user.get("weak_areas", []),
            "persistent_weak": persistent_weak[:5],
            "eval_avg": eval_avg,
        }

    except Exception:
        return _empty_progress()


def _empty_progress() -> Dict[str, Any]:
    """Return a zeroed-out progress dict — used when DB is unavailable."""
    return {
        "mastery_score": 0, "avg_score": 0, "trend": "new",
        "trend_label": "Just Starting", "consistency": 0,
        "total_quizzes": 0, "total_evals": 0, "weak_topics": [],
        "strong_topics": [], "topic_scores": {}, "stagnation": False,
        "sessions_this_week": 0, "improvement_rate": 0,
        "topics_studied": 0, "notes_saved": 0, "weak_areas": [],
        "persistent_weak": [], "eval_avg": 0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SPACED REPETITION (SRS)
# ══════════════════════════════════════════════════════════════════════════════

def upsert_srs_card(email: str, card: Dict[str, Any]) -> None:
    """Create or update an SRS card for (email, topic)."""
    db = _db()
    if not db:
        return
    try:
        db.srs_cards.update_one(
            {"email": email, "topic": card["topic"]},
            {"$set": card},
            upsert=True,
        )
    except Exception:
        pass


def get_srs_cards(email: str) -> List[Dict]:
    """Return all SRS cards for a user."""
    db = _db()
    if not db:
        return []
    try:
        return list(db.srs_cards.find({"email": email}))
    except Exception:
        return []


def get_srs_card(email: str, topic: str) -> Optional[Dict[str, Any]]:
    """Return a single SRS card for (email, topic), or None."""
    db = _db()
    if not db:
        return None
    try:
        return db.srs_cards.find_one({"email": email, "topic": topic})
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOG (used for streak computation)
# ══════════════════════════════════════════════════════════════════════════════

def log_activity(email: str) -> None:
    """
    Record a study session activity timestamp for streak tracking.
    Called whenever a quiz is completed or notes are generated.
    """
    db = _db()
    if not db:
        return
    try:
        db.activity.insert_one({
            "email": email,
            "time":  datetime.now(),
        })
    except Exception:
        pass


def get_activity_dates(email: str, limit: int = 200) -> List[datetime]:
    """Return list of activity datetimes for streak computation."""
    db = _db()
    if not db:
        return []
    try:
        docs = list(
            db.activity.find({"email": email})
            .sort("time", -1)
            .limit(limit)
        )
        return [d["time"] for d in docs if "time" in d]
    except Exception:
        return []
