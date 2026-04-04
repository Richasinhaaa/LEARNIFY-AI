# ══════════════════════════════════════════════════════════════════════════════
# services/spaced_repetition.py — Spaced Repetition Engine (SM-2 Algorithm)
#
# The single highest-ROI feature for a learning app.
# Uses the SM-2 algorithm (the same one Anki uses) to schedule reviews.
#
# How it works:
#   - After each quiz on a topic, the score is mapped to a quality rating (0-5)
#   - SM-2 uses the rating to compute: easiness factor, repetition count,
#     and the number of days until the next review
#   - Topics due for review surface on the dashboard
#
# All functions are pure — no I/O, no DB access, no Streamlit.
# The database layer stores SRSCard dicts in MongoDB.
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ── SRS Card schema ───────────────────────────────────────────────────────────
# Stored in MongoDB as a plain dict (no ORM needed)
#
# {
#   "email":          str,
#   "topic":          str,
#   "easiness":       float,   # starts at 2.5; range 1.3–2.5
#   "repetitions":    int,     # number of successful reviews in a row
#   "interval_days":  int,     # days until next review
#   "next_review":    datetime,
#   "last_score":     float,   # last quiz percentage (0-100)
#   "updated":        datetime,
# }

# SM-2 default easiness factor
_INITIAL_EASINESS  = 2.5
_MINIMUM_EASINESS  = 1.3

# Quiz score → SM-2 quality mapping
# SM-2 quality: 0 = complete blackout, 5 = perfect recall
def _score_to_quality(quiz_pct: float) -> int:
    """Convert a quiz percentage (0-100) to SM-2 quality (0-5)."""
    if quiz_pct >= 90: return 5
    if quiz_pct >= 75: return 4
    if quiz_pct >= 60: return 3
    if quiz_pct >= 40: return 2
    if quiz_pct >= 20: return 1
    return 0


def new_card(email: str, topic: str) -> Dict:
    """Create a fresh SRS card for a topic. Due immediately."""
    return {
        "email":         email,
        "topic":         topic,
        "easiness":      _INITIAL_EASINESS,
        "repetitions":   0,
        "interval_days": 1,
        "next_review":   datetime.now(),
        "last_score":    0.0,
        "updated":       datetime.now(),
    }


def update_card(card: Dict, quiz_pct: float) -> Dict:
    """
    Apply the SM-2 algorithm to update a card after a quiz attempt.

    SM-2 rules:
      - quality < 3  → reset repetitions to 0, interval back to 1
      - quality >= 3 → increment repetitions, compute new interval
        * rep 1 → 1 day
        * rep 2 → 6 days
        * rep n → interval * easiness factor (rounded)
      - Easiness factor adjusted after every review:
        new_ef = ef + (0.1 - (5-q)*(0.08 + (5-q)*0.02))
        Clamped to minimum of 1.3

    Returns a new card dict (does not mutate input).
    """
    quality     = _score_to_quality(quiz_pct)
    easiness    = card.get("easiness",      _INITIAL_EASINESS)
    repetitions = card.get("repetitions",   0)
    interval    = card.get("interval_days", 1)

    # Update easiness factor
    new_ef = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(_MINIMUM_EASINESS, round(new_ef, 4))

    # Update interval and repetition count
    if quality < 3:
        # Failed review — restart sequence
        new_reps     = 0
        new_interval = 1
    else:
        new_reps = repetitions + 1
        if new_reps == 1:
            new_interval = 1
        elif new_reps == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)

    next_review = datetime.now() + timedelta(days=new_interval)

    return {
        **card,
        "easiness":      new_ef,
        "repetitions":   new_reps,
        "interval_days": new_interval,
        "next_review":   next_review,
        "last_score":    quiz_pct,
        "updated":       datetime.now(),
    }


def get_due_cards(cards: List[Dict], as_of: Optional[datetime] = None) -> List[Dict]:
    """
    Return all cards that are due for review on or before `as_of`.
    Sorted by most overdue first.
    """
    cutoff = as_of or datetime.now()
    due = [c for c in cards if c.get("next_review", datetime.now()) <= cutoff]
    return sorted(due, key=lambda c: c.get("next_review", datetime.now()))


def get_upcoming_cards(cards: List[Dict], days_ahead: int = 7) -> List[Dict]:
    """Return cards due within the next N days, sorted by due date."""
    horizon = datetime.now() + timedelta(days=days_ahead)
    upcoming = [c for c in cards if datetime.now() < c.get("next_review", datetime.now()) <= horizon]
    return sorted(upcoming, key=lambda c: c.get("next_review", datetime.now()))


def days_until_review(card: Dict) -> int:
    """Return days until a card is due (0 = due now, negative = overdue)."""
    delta = card.get("next_review", datetime.now()) - datetime.now()
    return delta.days


def format_due_label(card: Dict) -> str:
    """Return a human-readable due label like 'Due today', 'Due in 3 days', 'Overdue by 2 days'."""
    days = days_until_review(card)
    if days < 0:
        return f"⚠️ Overdue by {abs(days)} day{'s' if abs(days) != 1 else ''}"
    if days == 0:
        return "🔴 Due today"
    if days == 1:
        return "🟡 Due tomorrow"
    return f"🟢 Due in {days} days"


def srs_stats(cards: List[Dict]) -> Dict:
    """Compute summary statistics for a user's SRS deck."""
    if not cards:
        return {"total": 0, "due_today": 0, "mastered": 0, "learning": 0}

    now = datetime.now()
    due_today = sum(1 for c in cards if c.get("next_review", now) <= now)
    mastered  = sum(1 for c in cards if c.get("interval_days", 0) >= 21)
    learning  = len(cards) - mastered

    return {
        "total":     len(cards),
        "due_today": due_today,
        "mastered":  mastered,
        "learning":  learning,
    }
