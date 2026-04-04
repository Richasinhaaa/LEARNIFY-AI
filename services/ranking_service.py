# ══════════════════════════════════════════════════════════════════════════════
# services/ranking_service.py — Video Ranking Engine
#
# Rule-based scoring system that ranks videos 0-100 across 5 dimensions.
# This is PURE logic — no I/O, no Streamlit, no LLM calls.
# Every function here is independently unit-testable.
# ══════════════════════════════════════════════════════════════════════════════

import re
from typing import Dict, List, Optional, Tuple

# ── Constants (exported so UI can display them) ───────────────────────────────

LEVEL_KEYWORDS: Dict[str, List[str]] = {
    "Beginner": [
        "beginner", "basics", "introduction", "intro", "getting started",
        "for beginners", "learn", "simple", "easy", "fundamental",
        "crash course", "explained simply", "tutorial for beginners",
    ],
    "Intermediate": [
        "intermediate", "tutorial", "guide", "explained", "how to",
        "course", "practice", "build", "complete",
    ],
    "Advanced": [
        "advanced", "deep dive", "in-depth", "expert", "master",
        "complete", "professional", "production", "from scratch",
    ],
}

# Ideal video duration range (minutes) per level
IDEAL_DURATION: Dict[str, Tuple[int, int]] = {
    "Beginner":     (4,  22),
    "Intermediate": (10, 50),
    "Advanced":     (20, 120),
}

# Scoring weights (must sum to 100)
WEIGHTS = {
    "topic_relevance": 30,
    "level_match":     25,
    "duration_fit":    20,
    "weak_boost":      15,
    "popularity":      10,
}


# ── Public API ────────────────────────────────────────────────────────────────

def rank_video(
    video: Dict,
    topic: str,
    level: str,
    weak_topics: Optional[List[str]] = None,
) -> Tuple[int, Dict[str, int], List[str]]:
    """
    Score a single video 0-100 across 5 explicit criteria.

    Args:
        video:       Dict with keys: title, desc, duration, views
        topic:       The user's current study topic
        level:       Beginner | Intermediate | Advanced
        weak_topics: List of topics the user has struggled with

    Returns:
        (total_score, breakdown_dict, reason_list)
    """
    title = (video.get("title") or "").lower()
    desc  = (video.get("desc")  or "").lower()
    weak  = [w.lower() for w in (weak_topics or [])]

    score = 0
    breakdown: Dict[str, int] = {}
    reasons: List[str] = []

    # 1. Topic Relevance (0–30)
    # Count how many words from the topic appear in title + desc
    topic_words = [w for w in topic.lower().split() if len(w) > 3]
    hits = sum(1 for w in topic_words if w in title or w in desc)
    topic_score = min(WEIGHTS["topic_relevance"], hits * 8)
    score += topic_score
    breakdown["topic_relevance"] = topic_score
    if hits > 0:
        reasons.append(f"covers '{topic}'")

    # 2. Level Match (0–25)
    level_kws = LEVEL_KEYWORDS.get(level, [])
    level_hits = sum(1 for kw in level_kws if kw in title or kw in desc)
    level_score = min(WEIGHTS["level_match"], level_hits * 10)
    score += level_score
    breakdown["level_match"] = level_score
    if level_hits > 0:
        reasons.append(f"matches {level} level")

    # 3. Duration Fit (0–20)
    duration_score = _score_duration(video.get("duration", ""), level, reasons)
    score += duration_score
    breakdown["duration_fit"] = duration_score

    # 4. Weak Topic Boost (0–15)
    weak_score = 0
    for wt in weak:
        wt_words = [w for w in wt.split() if len(w) > 3]
        if wt_words and any(w in title or w in desc for w in wt_words):
            weak_score = WEIGHTS["weak_boost"]
            reasons.append(f"addresses your weak area: '{wt}'")
            break  # Only count the first matching weak topic
    score += weak_score
    breakdown["weak_boost"] = weak_score

    # 5. Popularity Signal (0–10)
    pop_score = _score_popularity(video.get("views", ""))
    score += pop_score
    breakdown["popularity"] = pop_score

    return min(100, score), breakdown, reasons


def build_explanation(
    video: Dict,
    topic: str,
    level: str,
    weak_topics: List[str],
    breakdown: Dict[str, int],
) -> str:
    """
    Build a human-readable explanation of why a video was recommended.
    Pure function — no LLM call, no I/O.
    """
    minutes = _parse_duration(video.get("duration", ""))
    weak = weak_topics or []
    parts = []

    if breakdown.get("weak_boost", 0) > 0 and weak:
        parts.append(
            f"You previously struggled with **{weak[0]}** — "
            "this video directly addresses that gap."
        )
    else:
        parts.append(f"This video matches your topic: **{topic}**.")

    if breakdown.get("level_match", 0) > 0:
        parts.append(f"It's designed for **{level} learners**, matching your current stage.")

    if minutes > 0:
        lo, hi = IDEAL_DURATION.get(level, (5, 60))
        if lo <= minutes <= hi:
            parts.append(f"At **{int(minutes)} min**, it fits your ideal study window.")
        elif minutes < lo:
            parts.append(f"It's short ({int(minutes)} min) — great for a quick session.")
        else:
            parts.append(f"It's comprehensive ({int(minutes)} min) — set aside focused time.")

    if breakdown.get("topic_relevance", 0) >= 16:
        parts.append(f"Strong keyword match with **{topic}** in the title/description.")

    return " ".join(parts) if parts else "Recommended based on topic and level match."


# ── Private helpers ────────────────────────────────────────────────────────────

def _parse_duration(dur_str: str) -> float:
    """Convert 'MM:SS' or 'HH:MM:SS' string to total minutes. Returns 0 on failure."""
    if not dur_str or dur_str in ("N/A", ""):
        return 0.0
    try:
        parts = dur_str.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
    except Exception:
        pass
    return 0.0


def _score_duration(dur_str: str, level: str, reasons: List[str]) -> int:
    """Score video duration against ideal range for the given level."""
    minutes = _parse_duration(dur_str)
    if minutes <= 0:
        return 0

    lo, hi = IDEAL_DURATION.get(level, (5, 60))
    if lo <= minutes <= hi:
        reasons.append(f"ideal duration ({int(minutes)} min)")
        return WEIGHTS["duration_fit"]
    elif minutes < lo:
        return max(0, WEIGHTS["duration_fit"] - int((lo - minutes) * 2))
    else:
        return max(0, WEIGHTS["duration_fit"] - int(minutes - hi))


def _score_popularity(views_str: str) -> int:
    """Convert view count string (e.g. '1.2M', '450K') to a 0-10 score."""
    if not views_str:
        return 0
    v = views_str.upper().replace(",", "").replace(" ", "")
    try:
        if "M" in v:
            return min(10, int(float(re.sub(r"[^0-9.]", "", v.replace("M", ""))) * 2))
        if "K" in v:
            return min(10, int(float(re.sub(r"[^0-9.]", "", v.replace("K", ""))) / 100))
    except Exception:
        pass
    return 0



