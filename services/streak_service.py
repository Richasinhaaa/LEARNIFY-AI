# ══════════════════════════════════════════════════════════════════════════════
# services/streak_service.py — Study Streak & Gamification
#
# Tracks consecutive daily study sessions and awards milestone badges.
# Pure logic — no I/O, no DB, no Streamlit. Fully testable.
# ══════════════════════════════════════════════════════════════════════════════

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional


# ── Milestone badges ──────────────────────────────────────────────────────────
BADGES = [
    {"days":  3, "icon": "🔥",  "name": "On Fire",      "desc": "3-day streak"},
    {"days":  7, "icon": "⚡",  "name": "Week Warrior",  "desc": "7-day streak"},
    {"days": 14, "icon": "💎",  "name": "Diamond Mind",  "desc": "14-day streak"},
    {"days": 30, "icon": "🏆",  "name": "Legend",        "desc": "30-day streak"},
    {"days": 50, "icon": "🚀",  "name": "Unstoppable",   "desc": "50-day streak"},
    {"days":100, "icon": "👑",  "name": "Grand Master",  "desc": "100-day streak"},
]


def compute_streak(activity_dates: List[datetime]) -> Dict:
    """
    Compute streak statistics from a list of activity timestamps.

    Args:
        activity_dates: List of datetime objects (quiz attempts, note saves, etc.)

    Returns dict with:
        current_streak: int   — consecutive days ending today/yesterday
        longest_streak: int   — all-time best streak
        last_active:    date  — most recent activity date
        active_days:    int   — total unique days with activity
        badges_earned:  list  — list of badge dicts earned so far
    """
    if not activity_dates:
        return _empty_streak()

    # Deduplicate to unique dates
    unique_dates = sorted({d.date() for d in activity_dates}, reverse=True)
    today        = date.today()
    yesterday    = today - timedelta(days=1)

    # Current streak: count backwards from today or yesterday
    current = 0
    if unique_dates and unique_dates[0] in (today, yesterday):
        expected = unique_dates[0]
        for d in unique_dates:
            if d == expected:
                current += 1
                expected = d - timedelta(days=1)
            else:
                break

    # Longest streak ever
    longest    = 0
    run        = 0
    prev_date  = None
    for d in reversed(unique_dates):
        if prev_date is None or d == prev_date + timedelta(days=1):
            run += 1
        else:
            longest = max(longest, run)
            run = 1
        prev_date = d
    longest = max(longest, run)

    earned_badges = [b for b in BADGES if longest >= b["days"]]

    return {
        "current_streak": current,
        "longest_streak": longest,
        "last_active":    unique_dates[0] if unique_dates else None,
        "active_days":    len(unique_dates),
        "badges_earned":  earned_badges,
        "next_badge":     _next_badge(longest),
        "days_to_next":   _days_to_next(longest),
    }


def _next_badge(current_longest: int) -> Optional[Dict]:
    """Return the next badge the user hasn't earned yet."""
    for b in BADGES:
        if current_longest < b["days"]:
            return b
    return None


def _days_to_next(current_longest: int) -> int:
    """Return days needed to earn the next badge."""
    nb = _next_badge(current_longest)
    return nb["days"] - current_longest if nb else 0


def _empty_streak() -> Dict:
    return {
        "current_streak": 0,
        "longest_streak": 0,
        "last_active":    None,
        "active_days":    0,
        "badges_earned":  [],
        "next_badge":     BADGES[0],
        "days_to_next":   BADGES[0]["days"],
    }


def streak_message(streak_data: Dict) -> str:
    """Return a motivational message based on the current streak."""
    cs = streak_data["current_streak"]
    if cs == 0:
        return "Start studying today to begin your streak! 🌱"
    if cs == 1:
        return "Great start! Come back tomorrow to build your streak. 🔥"
    if cs < 7:
        return f"{cs}-day streak! You're building momentum. Keep going! ⚡"
    if cs < 14:
        return f"Incredible! {cs} days straight. You're in the top 10%! 💎"
    return f"🏆 {cs} days! You're a learning legend. Nothing can stop you!"
