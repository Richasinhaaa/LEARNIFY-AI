# ══════════════════════════════════════════════════════════════════════════════
# models/user_model.py — Data Models
#
# Defines typed dataclasses for all domain objects.
# These are the single source of truth for what a User / QuizResult / Note
# looks like. Any code that creates or reads these objects must use these types.
# ══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    """Represents a learner profile stored in MongoDB."""
    email: str
    name: str
    level: str = "Beginner"          # Beginner | Intermediate | Advanced
    goal: str = "Concept Learning"   # Concept Learning | Exam Preparation | Quick Revision
    current_topic: str = ""
    weak_areas: List[str] = field(default_factory=list)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class QuizResult:
    """A single quiz attempt stored in MongoDB."""
    email: str
    topic: str
    score: int        # number of correct answers
    total: int        # total questions
    pct: int          # percentage 0-100
    wrong: List[str]  # text of wrong questions
    time: datetime = field(default_factory=datetime.now)


@dataclass
class Note:
    """A saved note document."""
    email: str
    topic: str
    notes: str
    level: str
    goal: str
    source: str = "topic"    # "topic" | "youtube" | "upload"
    updated: datetime = field(default_factory=datetime.now)


@dataclass
class Evaluation:
    """A subjective answer evaluation."""
    email: str
    question: str
    answer_preview: str
    evaluation: str
    score: float
    time: datetime = field(default_factory=datetime.now)


@dataclass
class LearnerProfile:
    """
    Derived analytics profile computed from quiz history.
    Not persisted directly — computed on demand.
    """
    mastery_score: float = 0.0
    avg_score: float = 0.0
    trend: str = "new"               # new | improving | consistent | declining
    trend_label: str = "Just Starting"
    consistency: int = 0
    total_quizzes: int = 0
    weak_topics: List[str] = field(default_factory=list)
    strong_topics: List[str] = field(default_factory=list)
    topic_scores: dict = field(default_factory=dict)
    stagnation: bool = False
    sessions_this_week: int = 0
    improvement_rate: float = 0.0
    persistent_weak: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to plain dict for use in prompts and display logic."""
        return self.__dict__
