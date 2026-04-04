# ══════════════════════════════════════════════════════════════════════════════
# tests/test_spaced_repetition.py
# Unit tests for SM-2 spaced repetition engine — pure functions, no DB needed
# ══════════════════════════════════════════════════════════════════════════════

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from services.spaced_repetition import (
    new_card, update_card, get_due_cards, srs_stats, _score_to_quality,
    days_until_review,
)

def test_quality_mapping():
    assert _score_to_quality(95) == 5
    assert _score_to_quality(80) == 4
    assert _score_to_quality(65) == 3
    assert _score_to_quality(45) == 2
    assert _score_to_quality(25) == 1
    assert _score_to_quality(10) == 0

def test_new_card_defaults():
    card = new_card("user@test.com", "python")
    assert card["easiness"]      == 2.5
    assert card["repetitions"]   == 0
    assert card["interval_days"] == 1

def test_first_rep_interval():
    card = update_card(new_card("u@t.com", "python"), 90.0)
    assert card["repetitions"]   == 1
    assert card["interval_days"] == 1

def test_second_rep_interval():
    c1 = update_card(new_card("u@t.com", "python"), 90.0)
    c2 = update_card(c1, 85.0)
    assert c2["repetitions"]   == 2
    assert c2["interval_days"] == 6

def test_third_rep_grows():
    c = new_card("u@t.com", "python")
    for _ in range(3):
        c = update_card(c, 90.0)
    assert c["interval_days"] > 6

def test_fail_resets():
    c = update_card(update_card(new_card("u@t.com", "ml"), 90.0), 90.0)
    assert c["repetitions"] == 2
    c = update_card(c, 15.0)
    assert c["repetitions"]   == 0
    assert c["interval_days"] == 1

def test_easiness_floor():
    card = new_card("u@t.com", "hard")
    for _ in range(20):
        card = update_card(card, 0.0)
    assert card["easiness"] >= 1.3

def test_due_cards_sorted():
    now = datetime.now()
    cards = [
        {"topic": "a", "next_review": now - timedelta(days=1)},
        {"topic": "b", "next_review": now - timedelta(days=5)},
        {"topic": "c", "next_review": now - timedelta(days=2)},
    ]
    due = get_due_cards(cards)
    assert due[0]["topic"] == "b"   # most overdue first

def test_no_due_cards():
    now = datetime.now()
    cards = [{"topic": "a", "next_review": now + timedelta(days=5)}]
    assert get_due_cards(cards) == []

def test_srs_stats_empty():
    stats = srs_stats([])
    assert stats["total"] == 0

def test_srs_stats_mastered():
    now = datetime.now()
    cards = [
        {"next_review": now - timedelta(days=1), "interval_days": 30},
        {"next_review": now + timedelta(days=3), "interval_days": 5},
    ]
    stats = srs_stats(cards)
    assert stats["total"]     == 2
    assert stats["mastered"]  == 1
    assert stats["due_today"] == 1
