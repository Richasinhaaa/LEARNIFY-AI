# ══════════════════════════════════════════════════════════════════════════════
# services/learning_engine.py — Rule-Based Learning Intelligence
#
# Responsibilities:
#   - Concept dependency graph (prerequisites)
#   - Smart topic recommendations based on profile + gaps
#   - Learning profile computation from raw quiz history
#   - Study plan day-structure generation
#   - Weak area tracking
#
# All pure logic — no I/O, no LLM calls, no Streamlit.
# ══════════════════════════════════════════════════════════════════════════════

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# CONCEPT DEPENDENCY GRAPH
# Keys = topics. Values = list of prerequisite topics.
# ══════════════════════════════════════════════════════════════════════════════

CONCEPT_GRAPH: Dict[str, List[str]] = {
    # AI / ML
    "machine learning":          ["python", "statistics", "linear algebra"],
    "deep learning":             ["machine learning", "neural networks", "calculus"],
    "neural networks":           ["machine learning", "linear algebra"],
    "natural language processing": ["machine learning", "python", "statistics"],
    "computer vision":           ["deep learning", "linear algebra", "python"],
    "reinforcement learning":    ["machine learning", "probability", "python"],
    "transformers":              ["neural networks", "natural language processing"],
    "large language models":     ["transformers", "natural language processing"],
    "embeddings":                ["machine learning", "linear algebra"],
    # Data
    "data science":              ["python", "statistics", "pandas", "numpy"],
    "pandas":                    ["python"],
    "numpy":                     ["python"],
    "scikit-learn":              ["python", "machine learning"],
    "tensorflow":                ["python", "deep learning"],
    "pytorch":                   ["python", "deep learning"],
    # Databases
    "sql":                       ["databases"],
    "mongodb":                   ["databases", "json"],
    "databases":                 [],
    # Web
    "react":                     ["javascript", "html", "css"],
    "javascript":                ["html", "css"],
    "typescript":                ["javascript"],
    "html":                      [],
    "css":                       ["html"],
    "node.js":                   ["javascript"],
    "rest api":                  ["http", "json"],
    # Core CS
    "data structures":           ["python"],
    "algorithms":                ["data structures", "python"],
    "binary search":             ["arrays", "algorithms"],
    "linked lists":              ["data structures"],
    "trees":                     ["linked lists", "recursion"],
    "graphs":                    ["trees", "algorithms"],
    "dynamic programming":       ["recursion", "algorithms"],
    "recursion":                 ["python", "algorithms"],
    "arrays":                    ["python"],
    "sorting algorithms":        ["arrays", "algorithms"],
    # Math
    "statistics":                ["mathematics"],
    "probability":               ["statistics", "mathematics"],
    "linear algebra":            ["mathematics"],
    "calculus":                  ["mathematics"],
    "mathematics":               [],
    # DevOps / Infra
    "git":                       [],
    "docker":                    ["linux"],
    "linux":                     [],
    "cloud computing":           ["networking", "linux"],
    "networking":                [],
    "system design":             ["databases", "networking", "algorithms"],
    # Languages
    "python":                    [],
    "java":                      [],
    "c++":                       [],
}

# Common abbreviation aliases
_ALIASES: Dict[str, str] = {
    "ml":   "machine learning",
    "dl":   "deep learning",
    "nlp":  "natural language processing",
    "cv":   "computer vision",
    "rl":   "reinforcement learning",
    "ds":   "data science",
    "llm":  "large language models",
    "llms": "large language models",
    "dsa":  "data structures",
    "dp":   "dynamic programming",
    "nn":   "neural networks",
}


def _normalise(topic: str) -> str:
    """Lowercase, strip, and resolve common abbreviations."""
    t = topic.lower().strip()
    return _ALIASES.get(t, t)


# ── Prerequisite queries ──────────────────────────────────────────────────────

def get_prerequisites(topic: str) -> List[str]:
    """Return direct prerequisites for a topic. Fuzzy-matches partial names."""
    t = _normalise(topic)
    if t in CONCEPT_GRAPH:
        return CONCEPT_GRAPH[t]
    # Fuzzy match: topic contains a graph key or vice versa
    for key in CONCEPT_GRAPH:
        if key in t or t in key:
            return CONCEPT_GRAPH[key]
    return []


def get_learning_gaps(studied: List[str], target: str) -> List[str]:
    """Return prerequisites of target that the user hasn't studied yet."""
    prereqs = get_prerequisites(target)
    studied_lower = [s.lower() for s in studied]
    return [p for p in prereqs if not any(p in s or s in p for s in studied_lower)]


def get_unlocked_by(topic: str) -> List[str]:
    """Return topics that become available once this topic is mastered."""
    t = _normalise(topic)
    return [
        k for k, prereqs in CONCEPT_GRAPH.items()
        if any(t in p or p in t for p in prereqs)
    ][:4]


def get_learning_path(target: str, studied: List[str]) -> List[str]:
    """
    Return an ordered list of topics to study to reach the target,
    skipping anything already studied.
    Uses DFS over the prerequisite graph.
    """
    studied_lower = [s.lower() for s in studied]
    visited: set = set()
    path: List[str] = []

    def dfs(t: str) -> None:
        norm = _normalise(t)
        if norm in visited:
            return
        visited.add(norm)
        for prereq in get_prerequisites(norm):
            if not any(prereq in s or s in prereq for s in studied_lower):
                dfs(prereq)
        if not any(norm in s or s in norm for s in studied_lower):
            path.append(norm)

    dfs(target)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# LEARNER PROFILE (derived from quiz history)
# ══════════════════════════════════════════════════════════════════════════════

def compute_profile(quiz_history: List[Dict]) -> Dict:
    """
    Derive a LearnerProfile dict from raw quiz history.
    Pure function — no DB access.
    """
    if not quiz_history:
        return _empty_profile()

    topic_scores: Dict[str, List[float]] = defaultdict(list)
    pcts: List[float] = []

    for q in quiz_history:
        p = q.get("pct", 0)
        pcts.append(p)
        topic_scores[q.get("topic", "unknown")].append(p)

    ts_avg = {t: round(sum(s) / len(s), 1) for t, s in topic_scores.items()}
    weak_topics = sorted([t for t, s in ts_avg.items() if s < 60], key=lambda t: ts_avg[t])
    strong_topics = [t for t, s in ts_avg.items() if s >= 80]

    avg = round(sum(pcts) / len(pcts), 1) if pcts else 0
    mastery = min(100, round(avg * 0.7 + len(strong_topics) * 5, 1))

    trend, trend_label, improvement_rate = "new", "Just Starting", 0.0
    if len(pcts) >= 6:
        recent_avg = sum(pcts[:5]) / 5
        prev_avg   = sum(pcts[5:10]) / min(5, len(pcts[5:]))
        improvement_rate = round(recent_avg - prev_avg, 1)
        if improvement_rate >= 8:
            trend, trend_label = "improving",  "Improving ↑"
        elif improvement_rate <= -8:
            trend, trend_label = "declining",  "Needs Attention ↓"
        else:
            trend, trend_label = "consistent", "Consistent →"

    stagnation = False
    if len(pcts) >= 5:
        v5 = pcts[:5]
        if max(v5) - min(v5) < 10 and avg < 70:
            stagnation = True

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    sessions_this_week = sum(
        1 for q in quiz_history if q.get("time", now) > week_ago
    )
    consistency = min(100, sessions_this_week * 20)

    # Questions wrong in ≥2 quizzes
    wrong_freq: Dict[str, int] = defaultdict(int)
    for q in quiz_history:
        for wq in q.get("wrong", []):
            wrong_freq[wq[:60]] += 1
    persistent_weak = [
        q for q, c in sorted(wrong_freq.items(), key=lambda x: -x[1]) if c >= 2
    ]

    return {
        "mastery_score":      mastery,
        "avg_score":          avg,
        "trend":              trend,
        "trend_label":        trend_label,
        "consistency":        consistency,
        "total_quizzes":      len(quiz_history),
        "weak_topics":        weak_topics[:5],
        "strong_topics":      strong_topics[:5],
        "topic_scores":       ts_avg,
        "stagnation":         stagnation,
        "sessions_this_week": sessions_this_week,
        "improvement_rate":   improvement_rate,
        "persistent_weak":    persistent_weak[:5],
    }


def _empty_profile() -> Dict:
    return {
        "mastery_score": 0, "avg_score": 0, "trend": "new",
        "trend_label": "Just Starting", "consistency": 0,
        "total_quizzes": 0, "weak_topics": [], "strong_topics": [],
        "topic_scores": {}, "stagnation": False,
        "sessions_this_week": 0, "improvement_rate": 0,
        "persistent_weak": [],
    }


def update_weak_areas(existing: List[str], wrong_questions: List[str]) -> List[str]:
    """Append new wrong questions to weak areas list (capped at 10)."""
    updated = list(existing)
    for w in wrong_questions:
        short = w[:70]
        if short not in updated:
            updated.append(short)
    return updated[-10:]


def smart_recommend(
    profile: Dict,
    studied: List[str],
    current_topic: str,
) -> Tuple[Optional[str], str, float]:
    """
    Recommend the next best topic to study.
    Returns (topic, reason, confidence) or (None, "", 0.0).
    """
    studied_lower = [s.lower() for s in studied]

    # 1. Stagnation: recommend a prerequisite of the weak topic
    if profile.get("stagnation") and profile.get("weak_topics"):
        for wt in profile["weak_topics"]:
            for prereq in get_prerequisites(wt):
                if not any(prereq in s or s in prereq for s in studied_lower):
                    return prereq, f"You appear stuck on '{wt}' — master this prerequisite", 0.95

    # 2. Directly weak topic
    if profile.get("weak_topics"):
        wt = profile["weak_topics"][0]
        score = profile["topic_scores"].get(wt, 0)
        return wt, f"Your quiz history shows {round(score)}% on this — it needs work", 0.85

    # 3. Gap in current topic's prerequisites
    if current_topic:
        gaps = get_learning_gaps(studied, current_topic)
        if gaps:
            return gaps[0], f"Prerequisite you haven't studied for '{current_topic}'", 0.80

    # 4. Unlocked topic
    for key, prereqs in CONCEPT_GRAPH.items():
        if any(key in s or s in key for s in studied_lower):
            continue
        all_met = all(
            any(p in s or s in p for s in studied_lower) for p in prereqs
        ) if prereqs else True
        if all_met and prereqs:
            return key, "Your completed topics unlock this", 0.65

    return None, "", 0.0


# ══════════════════════════════════════════════════════════════════════════════
# STUDY PLANNER — Rule-based day structure
# ══════════════════════════════════════════════════════════════════════════════

_DAILY_REMINDERS = [
    "Consistency matters more than intensity — show up every day.",
    "Revise before forgetting — review yesterday's notes first.",
    "Active recall beats passive reading — test yourself.",
    "One concept at a time — depth over breadth.",
    "Take short breaks — your brain consolidates during rest.",
    "You're making real progress — trust the process.",
    "Almost there — push through the final stretch!",
]

_TASK_ICONS = {
    "learn":    "📖",
    "video":    "▶️",
    "practice": "✏️",
    "quiz":     "🎯",
    "revision": "🔄",
    "project":  "🛠️",
    "weak":     "⚠️",
}


def build_study_structure(
    topic: str,
    level: str,
    weak_topics: List[str],
    days: int,
    daily_hours: float,
) -> List[Dict]:
    """
    Build a day-by-day study plan structure.
    Returns list of day dicts with keys: day, phase, tasks, reminder.
    Pure function — no I/O.
    """
    plan = []
    foundation_days = max(1, days // 3)
    application_days = max(2, days * 2 // 3)

    for day in range(1, days + 1):
        if day <= foundation_days:
            phase = "Foundation"
            tasks = [
                {"type": "learn",    "duration": min(40, int(daily_hours * 20)), "task": f"Study core concepts of {topic}"},
                {"type": "video",    "duration": min(20, int(daily_hours * 10)), "task": f"Watch beginner/intermediate video on {topic}"},
                {"type": "practice", "duration": min(25, int(daily_hours * 12)), "task": "Solve 3 practice problems"},
            ]
            if weak_topics:
                tasks.append({"type": "weak", "duration": 15, "task": f"Review weak area: {weak_topics[0]}"})

        elif day <= application_days:
            phase = "Application"
            tasks = [
                {"type": "practice", "duration": min(45, int(daily_hours * 22)), "task": f"Apply {topic} to real problems"},
                {"type": "video",    "duration": min(25, int(daily_hours * 12)), "task": f"Watch advanced video on {topic}"},
                {"type": "quiz",     "duration": 20,                              "task": f"Take 5-question quiz on {topic}"},
            ]
        else:
            phase = "Mastery"
            tasks = [
                {"type": "revision", "duration": min(30, int(daily_hours * 15)), "task": f"Revise all notes on {topic}"},
                {"type": "quiz",     "duration": 25,                              "task": "Full quiz to test mastery"},
                {"type": "project",  "duration": min(40, int(daily_hours * 20)), "task": "Build a mini project / solve exam-style question"},
            ]

        plan.append({
            "day":      day,
            "phase":    phase,
            "tasks":    tasks,
            "reminder": _DAILY_REMINDERS[(day - 1) % len(_DAILY_REMINDERS)],
        })

    return plan
