# ══════════════════════════════════════════════════════════════════════════════
# tests/test_ranking_service.py
#
# Unit tests for the video ranking engine.
# Run with: pytest tests/ -v
# ══════════════════════════════════════════════════════════════════════════════

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ranking_service import rank_video, build_explanation, _parse_duration


# ── Duration parser ───────────────────────────────────────────────────────────

def test_parse_duration_mm_ss():
    assert _parse_duration("10:30") == pytest.approx(10.5, rel=0.01)

def test_parse_duration_hh_mm_ss():
    assert _parse_duration("1:30:00") == 90.0

def test_parse_duration_na():
    assert _parse_duration("N/A") == 0.0

def test_parse_duration_empty():
    assert _parse_duration("") == 0.0


# ── rank_video ────────────────────────────────────────────────────────────────

def test_rank_video_high_relevance():
    video = {
        "title":    "Python for Beginners — Complete Tutorial",
        "desc":     "Learn python basics from scratch. Introduction to python programming.",
        "duration": "15:00",
        "views":    "1.2M",
    }
    score, breakdown, reasons = rank_video(video, "python", "Beginner")
    assert score > 40, f"Highly relevant beginner Python video should score > 40, got {score}"
    assert breakdown["topic_relevance"] > 0
    assert breakdown["level_match"] > 0

def test_rank_video_weak_boost():
    video = {
        "title":    "Gradient Descent deep dive — advanced",
        "desc":     "master gradient descent optimization algorithm",
        "duration": "45:00",
        "views":    "500K",
    }
    score_no_weak, bd_no_weak, _ = rank_video(video, "machine learning", "Advanced")
    score_with_weak, bd_with_weak, reasons = rank_video(
        video, "machine learning", "Advanced", weak_topics=["gradient descent"]
    )
    assert bd_with_weak["weak_boost"] == 15
    assert score_with_weak > score_no_weak
    assert any("weak area" in r for r in reasons)

def test_rank_video_score_capped_at_100():
    video = {
        "title":    "Python beginner basics introduction getting started easy",
        "desc":     "python beginner fundamental simple crash course for beginners",
        "duration": "12:00",
        "views":    "5M",
    }
    score, _, _ = rank_video(video, "python", "Beginner", ["python"])
    assert score <= 100

def test_rank_video_no_info():
    video = {"title": "", "desc": "", "duration": "N/A", "views": "N/A"}
    score, breakdown, reasons = rank_video(video, "python", "Beginner")
    assert score == 0
    assert reasons == []

def test_rank_video_returns_three_values():
    """rank_video must always return a 3-tuple."""
    video = {"title": "Some video", "desc": "some desc", "duration": "10:00", "views": "10K"}
    result = rank_video(video, "python", "Beginner")
    assert len(result) == 3

def test_rank_video_intermediate_duration():
    """Intermediate level should reward 10-50 min videos."""
    video = {
        "title":    "React Hooks Intermediate Tutorial",
        "desc":     "hooks useState useEffect intermediate explained",
        "duration": "30:00",
        "views":    "200K",
    }
    score, breakdown, _ = rank_video(video, "react", "Intermediate")
    assert breakdown["duration_fit"] > 0

def test_rank_video_advanced_duration_too_short():
    """A 5-min video should score low on duration_fit for Advanced level."""
    video = {
        "title":    "Neural Networks Advanced",
        "desc":     "advanced neural networks deep learning",
        "duration": "5:00",
        "views":    "100K",
    }
    _, breakdown, _ = rank_video(video, "neural networks", "Advanced")
    # Short video is not ideal for Advanced learners
    assert breakdown["duration_fit"] < 15


# ── build_explanation ─────────────────────────────────────────────────────────

def test_build_explanation_weak_boost():
    video     = {"title": "Overfitting explained", "duration": "10:00"}
    breakdown = {"weak_boost": 15, "level_match": 10, "topic_relevance": 16}
    explanation = build_explanation(video, "machine learning", "Beginner", ["overfitting"], breakdown)
    assert "overfitting" in explanation.lower()

def test_build_explanation_fallback():
    video     = {"title": "Some video", "duration": ""}
    breakdown = {"weak_boost": 0, "level_match": 0, "topic_relevance": 8}
    explanation = build_explanation(video, "python", "Beginner", [], breakdown)
    assert len(explanation) > 0

def test_build_explanation_returns_string():
    video     = {"title": "SQL JOINs tutorial", "duration": "20:00"}
    breakdown = {"weak_boost": 0, "level_match": 25, "topic_relevance": 30}
    result = build_explanation(video, "SQL", "Intermediate", [], breakdown)
    assert isinstance(result, str)