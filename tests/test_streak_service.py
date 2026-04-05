# ══════════════════════════════════════════════════════════════════════════════
# tests/test_streak_service.py
# Unit tests for streak computation — pure functions, no DB
# ══════════════════════════════════════════════════════════════════════════════

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from services.streak_service import compute_streak, streak_message, BADGES

def _days_ago(n):
    return datetime.now() - timedelta(days=n)

def test_empty_returns_zero():
    s = compute_streak([])
    assert s["current_streak"] == 0
    assert s["longest_streak"] == 0

def test_single_day():
    s = compute_streak([datetime.now()])
    assert s["current_streak"] == 1
    assert s["longest_streak"] == 1

def test_consecutive_days():
    dates = [_days_ago(i) for i in range(5)]   # today, yesterday, ... 4 days ago
    s = compute_streak(dates)
    assert s["current_streak"] == 5
    assert s["longest_streak"] == 5

def test_broken_streak():
    # 3-day streak then a 2-day gap then 2 more days
    dates = [_days_ago(0), _days_ago(1), _days_ago(2), _days_ago(5), _days_ago(6)]
    s = compute_streak(dates)
    assert s["current_streak"] == 3
    assert s["longest_streak"] == 3

def test_longest_streak_tracked():
    # Old 7-day streak, then broke, now 2-day streak
    old_streak = [_days_ago(i + 20) for i in range(7)]   # 7 consecutive days, 3+ weeks ago
    new_streak = [_days_ago(0), _days_ago(1)]
    s = compute_streak(old_streak + new_streak)
    assert s["longest_streak"] == 7
    assert s["current_streak"] == 2

def test_duplicate_dates_ignored():
    # Multiple activities within same day should count as 1 unique day
    # Use hours-apart timestamps to guarantee same calendar date
    now = datetime.now()
    today_activities = [now, now - timedelta(hours=1), now - timedelta(hours=2)]
    s = compute_streak(today_activities)
    assert s["active_days"] == 1

def test_badge_earned():
    dates = [_days_ago(i) for i in range(7)]
    s = compute_streak(dates)
    badge_names = [b["name"] for b in s["badges_earned"]]
    assert "On Fire"      in badge_names   # 3-day badge
    assert "Week Warrior" in badge_names   # 7-day badge

def test_no_badge_below_threshold():
    dates = [_days_ago(i) for i in range(2)]
    s = compute_streak(dates)
    assert s["badges_earned"] == []

def test_next_badge_pointer():
    dates = [_days_ago(i) for i in range(3)]   # exactly 3-day streak
    s = compute_streak(dates)
    # Next badge should be Week Warrior (7 days)
    assert s["next_badge"]["name"] == "Week Warrior"

def test_streak_message_zero():
    msg = streak_message({"current_streak": 0})
    assert "today" in msg.lower()

def test_streak_message_positive():
    msg = streak_message({"current_streak": 5})
    assert "5" in msg