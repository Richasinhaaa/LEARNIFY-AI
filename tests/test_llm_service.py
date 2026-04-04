# ══════════════════════════════════════════════════════════════════════════════
# tests/test_llm_service.py
#
# Unit tests for pure parsing functions in llm_service.
# These tests require NO API key — they test only parsing logic.
# ══════════════════════════════════════════════════════════════════════════════

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm_service import parse_quiz, parse_questions, extract_score


# ── parse_quiz ────────────────────────────────────────────────────────────────

_VALID_QUIZ = """
Q1: What is a Python list?
A) A fixed-size array
B) A mutable ordered sequence
C) A dictionary of values
D) An immutable tuple
ANS: B

Q2: Which keyword defines a function?
A) func
B) define
C) def
D) lambda
ANS: C
"""

def test_parse_quiz_valid():
    result = parse_quiz(_VALID_QUIZ)
    assert len(result) == 2
    assert result[0]["q"] == "What is a Python list?"
    assert result[0]["ans"] == 1        # B = index 1
    assert len(result[0]["opts"]) == 4

def test_parse_quiz_second_question():
    result = parse_quiz(_VALID_QUIZ)
    assert result[1]["ans"] == 2        # C = index 2

def test_parse_quiz_empty():
    assert parse_quiz("") == []

def test_parse_quiz_malformed():
    # Missing options — should return empty
    bad = "Q1: Some question\nANS: A"
    assert parse_quiz(bad) == []


# ── parse_questions ───────────────────────────────────────────────────────────

_VALID_QUESTIONS = """
Q1: Explain the concept of overfitting in machine learning.
Type: Conceptual
Length: Medium

Q2: Compare gradient descent and stochastic gradient descent.
Type: Analytical
Length: Long
"""

def test_parse_questions_valid():
    result = parse_questions(_VALID_QUESTIONS)
    assert len(result) == 2
    assert result[0]["type"] == "Conceptual"
    assert result[1]["length"] == "Long"

def test_parse_questions_empty():
    assert parse_questions("") == []

def test_parse_questions_short_text_skipped():
    # Questions shorter than 10 chars should be ignored
    short = "Q1: Hi\nType: Conceptual\nLength: Short"
    result = parse_questions(short)
    assert result == []


# ── extract_score ─────────────────────────────────────────────────────────────

def test_extract_score_simple():
    text = "## Score\n7/10 — Good understanding of the topic."
    assert extract_score(text) == 7.0

def test_extract_score_decimal():
    text = "Score: 8.5/10"
    assert extract_score(text) == 8.5

def test_extract_score_missing():
    assert extract_score("No score here") == 0.0

def test_extract_score_empty():
    assert extract_score("") == 0.0
