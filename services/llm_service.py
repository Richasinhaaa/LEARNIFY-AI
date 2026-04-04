# ══════════════════════════════════════════════════════════════════════════════
# services/llm_service.py — LLM / Groq Integration
#
# Single responsibility: all prompt construction and Groq API calls.
#
# Design decisions:
#   - One private _call() function handles all API communication
#   - All prompts are strings built in dedicated functions — never in UI files
#   - Every call has a fallback message — the app never crashes on LLM failure
#   - Exponential backoff retry on rate limits
#   - Input validation guards against prompt injection
#   - parse_* functions are pure (no I/O) and fully testable
# ══════════════════════════════════════════════════════════════════════════════

import os
import re
import time
from typing import List, Dict, Optional, Tuple
import streamlit as st

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

MAX_TOPIC_LENGTH     = 200
MAX_ANSWER_LENGTH    = 5000
MAX_CHAT_LENGTH      = 1000

_BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "forget your instructions",
    "you are now",
    "act as if",
    "disregard all",
    "<script",
    "javascript:",
    "drop table",
    "'; drop",
    "prompt injection",
]


def validate_topic(text: str) -> Tuple[bool, str]:
    """
    Validate a topic input string.
    Returns (is_valid, cleaned_text_or_error_message).
    """
    if not text or not text.strip():
        return False, "Topic cannot be empty."
    cleaned = text.strip()
    if len(cleaned) > MAX_TOPIC_LENGTH:
        return False, f"Topic too long — max {MAX_TOPIC_LENGTH} characters."
    lower = cleaned.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in lower:
            return False, "Invalid input detected. Please enter a valid topic."
    return True, cleaned


def validate_answer(text: str) -> Tuple[bool, str]:
    """
    Validate a free-text answer input.
    Returns (is_valid, cleaned_text_or_error_message).
    """
    if not text or not text.strip():
        return False, "Answer cannot be empty."
    cleaned = text.strip()
    if len(cleaned) > MAX_ANSWER_LENGTH:
        return False, f"Answer too long — max {MAX_ANSWER_LENGTH} characters."
    lower = cleaned.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in lower:
            return False, "Invalid input detected."
    return True, cleaned


def validate_chat_input(text: str) -> Tuple[bool, str]:
    """Validate a chat message."""
    if not text or not text.strip():
        return False, "Message cannot be empty."
    cleaned = text.strip()
    if len(cleaned) > MAX_CHAT_LENGTH:
        return False, f"Message too long — max {MAX_CHAT_LENGTH} characters."
    lower = cleaned.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in lower:
            return False, "Invalid input detected."
    return True, cleaned


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_client: Optional[object] = None


def _get_client():
    global _client
    if _client is None and GROQ_AVAILABLE:
        api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY", "")
        if api_key:
            try:
                _client = Groq(api_key=api_key)
            except Exception:
                _client = None
    return _client


# ══════════════════════════════════════════════════════════════════════════════
# CORE LLM CALL — with retry + backoff
# ══════════════════════════════════════════════════════════════════════════════

_DEFAULT_SYSTEM = (
    "You are Learnify — a precise, structured academic tutor. "
    "NEVER give generic responses. Every answer is specific to the topic, "
    "level, and goal. Use clear markdown with headings and real examples."
)


def _fallback(reason: str = "unknown") -> str:
    """Return a user-friendly error message based on failure reason."""
    messages = {
        "no_client": (
            "⚠️ AI service not configured.\n\n"
            "**Fix:** Add your `GROQ_API_KEY` to `.env` or Streamlit secrets.\n\n"
            "*Get a free key at console.groq.com*"
        ),
        "auth": (
            "🔑 Invalid API key.\n\n"
            "**Fix:** Check your `GROQ_API_KEY` in `.env` or Streamlit secrets.\n\n"
            "*Get a free key at console.groq.com*"
        ),
        "rate_limit": (
            "⏳ Rate limit reached — please wait 30 seconds and try again.\n\n"
            "**Your data is saved** — nothing was lost."
        ),
        "connection": (
            "🌐 Connection error — check your internet and try again.\n\n"
            "**Your data is saved** — nothing was lost."
        ),
        "unknown": (
            "⚠️ The AI service is temporarily unavailable.\n\n"
            "**What you can do:**\n"
            "- Wait 30 seconds and try again\n"
            "- Check your GROQ_API_KEY\n"
            "- Your data is saved — nothing is lost\n\n"
            "*This is usually a temporary rate limit or network issue.*"
        ),
    }
    return messages.get(reason, messages["unknown"])


def _call(
    prompt: str,
    max_tokens: int = 1400,
    temperature: float = 0.4,
    system: Optional[str] = None,
    max_retries: int = 3,
) -> str:
    """
    Send a prompt to Groq and return the text response.
    - Retries up to max_retries times on rate limit errors (exponential backoff)
    - Returns a user-friendly fallback string on any failure
    - Never raises an exception — the app always stays alive
    """
    client = _get_client()
    if not client:
        return _fallback("no_client")

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system or _DEFAULT_SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            err = str(e).lower()

            # Rate limit — wait with exponential backoff and retry
            if "rate" in err or "429" in err or "too many" in err:
                if attempt < max_retries - 1:
                    wait_seconds = 2 ** attempt  # 1s → 2s → 4s
                    time.sleep(wait_seconds)
                    continue
                return _fallback("rate_limit")

            # Auth / key issue — no point retrying
            if "auth" in err or "401" in err or "api_key" in err or "invalid key" in err:
                return _fallback("auth")

            # Connection / timeout — retry once then give up
            if "connection" in err or "timeout" in err or "network" in err:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return _fallback("connection")

            # Unknown error — return fallback immediately
            return _fallback("unknown")

    return _fallback("rate_limit")


# ══════════════════════════════════════════════════════════════════════════════
# NOTES GENERATION
# ══════════════════════════════════════════════════════════════════════════════

_LEVEL_GUIDE = {
    "Beginner":     "Simple language, no jargon, everyday analogies, explain from scratch.",
    "Intermediate": "Assume basic knowledge; use technical terms briefly.",
    "Advanced":     "Full depth, edge cases, nuances, advanced applications.",
}

_GOAL_FORMAT = {
    "Concept Learning": (
        "## 📖 What is {topic}?\n[2-3 sentence definition]\n\n"
        "## 🧠 Core Concepts\n[3-5 key ideas with analogies]\n\n"
        "## 💡 Real-World Examples\n[2-3 named real examples]\n\n"
        "## ⚠️ Common Mistakes\n[2-3 mistakes students make]\n\n"
        "## 🔗 What to Study Next\n[Related topics]\n\n"
        "## ✅ Mastery Checklist\n[4 things you can do after mastering this]"
    ),
    "Exam Preparation": (
        "## 📌 Exam Definition\n[One perfect exam-ready definition]\n\n"
        "## 🎯 Top 7 Must-Know Points\n[Highest-yield facts]\n\n"
        "## 📐 Key Formulas / Rules\n[Every formula with symbol meanings]\n\n"
        "## ✍️ Sample Q&A\n[3 likely exam Qs with full answers]\n\n"
        "## ⚡ Last-Minute Facts\n[5 facts to read before the exam]\n\n"
        "## 🔄 Exam Traps\n[2-3 tricks examiners use]"
    ),
    "Quick Revision": (
        "## ⚡ One-Line Summary\n[Entire topic in one sentence]\n\n"
        "## 🔑 5 Must-Know Points\n[Most critical facts only]\n\n"
        "## 🧠 Memory Trick\n[One mnemonic]\n\n"
        "## 📊 Key Numbers / Formulas\n[Hardest-to-remember specifics]\n\n"
        "## ✅ Self-Check\n[3 quick questions with answers]"
    ),
}


def generate_notes(topic: str, level: str, goal: str, extra_ctx: str = "") -> str:
    """Generate structured study notes tailored to topic, level, and goal."""
    is_valid, result = validate_topic(topic)
    if not is_valid:
        return f"⚠️ {result}"

    level_guide = _LEVEL_GUIDE.get(level, "")
    fmt = _GOAL_FORMAT.get(goal, _GOAL_FORMAT["Concept Learning"]).replace("{topic}", result)
    ctx_block = f"\n\nUSE THIS CONTEXT:\n{extra_ctx[:1500]}" if extra_ctx else ""

    prompt = (
        f"Generate HIGHLY SPECIFIC study notes.\n"
        f"Topic: {result}\nLevel: {level} — {level_guide}\nGoal: {goal}\n\n"
        f"RULES:\n- Name '{result}' in every section\n"
        f"- Use REAL examples (real companies, real code, real numbers)\n"
        f"- ZERO generic filler\n\nFORMAT:\n{fmt}{ctx_block}"
    )
    return _call(prompt, max_tokens=1800, temperature=0.35)


def notes_from_document(text: str, filename: str, level: str, goal: str) -> str:
    """Generate notes grounded in an uploaded document — no outside knowledge added."""
    prompt = (
        f"Document: '{filename}'\nLevel: {level} | Goal: {goal}\n\n"
        f"CONTENT:\n{text[:3000]}\n\n"
        "Generate notes ONLY from this document.\n\n"
        "## 📄 Overview\n[What this document covers]\n\n"
        "## 🔑 Key Concepts\n[Every major concept with explanation]\n\n"
        "## 📌 Important Facts\n[All specific facts, numbers, definitions]\n\n"
        "## 💡 Examples\n[Real examples from the document]\n\n"
        "## ⚡ Top 10 Revision Points\n[Most important things]\n\n"
        "## ✅ Key Takeaways\n[Must-remember points]\n\n"
        "DO NOT add outside information."
    )
    return _call(prompt, max_tokens=2000, temperature=0.3)


# ══════════════════════════════════════════════════════════════════════════════
# QUIZ
# ══════════════════════════════════════════════════════════════════════════════

_QUIZ_LEVEL_GUIDE = {
    "Beginner":     "Basic definitions, simple recall",
    "Intermediate": "Application, cause-effect, problem solving",
    "Advanced":     "Analysis, edge cases, synthesis",
}


def generate_quiz(topic: str, level: str, context: str = "") -> str:
    """Generate 5 MCQ questions. Returns raw LLM text to be parsed by parse_quiz()."""
    is_valid, result = validate_topic(topic)
    if not is_valid:
        return f"⚠️ {result}"

    guide = _QUIZ_LEVEL_GUIDE.get(level, "")
    ctx_block = f"\n\nBASE QUESTIONS ON:\n{context[:1200]}" if context else ""

    prompt = (
        f"Generate exactly 5 MCQ questions on: {result}\n"
        f"Level: {level} — {guide}\n\n"
        f"RULES: Questions MUST be specific to {result}. "
        "All 4 options must be plausible. Mix question types.\n\n"
        "FORMAT:\n\n"
        "Q1: [question]\nA) [opt]\nB) [opt]\nC) [opt]\nD) [opt]\nANS: [A/B/C/D]\n\n"
        "Q2: [question]\nA) [opt]\nB) [opt]\nC) [opt]\nD) [opt]\nANS: [A/B/C/D]\n\n"
        "Q3: [question]\nA) [opt]\nB) [opt]\nC) [opt]\nD) [opt]\nANS: [A/B/C/D]\n\n"
        "Q4: [question]\nA) [opt]\nB) [opt]\nC) [opt]\nD) [opt]\nANS: [A/B/C/D]\n\n"
        f"Q5: [question]\nA) [opt]\nB) [opt]\nC) [opt]\nD) [opt]\nANS: [A/B/C/D]{ctx_block}"
    )
    return _call(prompt, max_tokens=900, temperature=0.3)


def parse_quiz(raw: str) -> List[Dict]:
    """
    Parse raw LLM quiz text into a list of question dicts.
    Pure function — no side effects, fully testable.
    """
    questions = []
    if not raw:
        return questions

    try:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw.strip()) if b.strip()]
        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) < 6:
                continue

            q_text = re.sub(r"^Q\d+[:.]\s*", "", lines[0]).strip()
            opts, ans = [], "A"

            for line in lines[1:]:
                opt_match = re.match(r"^([A-D])[).]\s*(.+)", line, re.I)
                if opt_match:
                    opts.append(opt_match.group(2).strip())
                elif re.match(r"^ANS", line, re.I):
                    found = re.search(r"\b([A-D])\b", line, re.I)
                    if found:
                        ans = found.group(1).upper()

            if len(opts) == 4 and q_text:
                questions.append({
                    "q":    q_text,
                    "opts": opts,
                    "ans":  {"A": 0, "B": 1, "C": 2, "D": 3}.get(ans, 0),
                })
    except Exception:
        pass

    return questions


def analyze_quiz(
    topic: str,
    correct: int,
    total: int,
    wrong: List[str],
    level: str,
    profile: Dict,
) -> str:
    """Generate a performance analysis after a quiz."""
    pct = int(correct / total * 100) if total else 0
    wrong_text = "\n".join(f"- {q}" for q in wrong) if wrong else "None"
    trend_ctx = f"Trend: {profile.get('trend_label', 'Unknown')}. "
    stag_ctx = "Student appears stagnated. " if profile.get("stagnation") else ""

    prompt = (
        f"Quiz on: {topic}\nScore: {correct}/{total} ({pct}%) | Level: {level}\n"
        f"{trend_ctx}{stag_ctx}\nWrong:\n{wrong_text}\n\n"
        "## 📊 Performance\n[2-sentence honest assessment]\n\n"
        "## 🔴 Weak Concepts\n[Specific subtopics based on wrong answers]\n\n"
        "## 📚 Next 30 Minutes\n[3 specific steps to improve]\n\n"
        "## 💡 Concepts to Revisit\n[Specific concepts with brief explanation]\n\n"
        "## 🎯 Next Action\n[One specific recommended action]"
    )
    return _call(prompt, max_tokens=600, temperature=0.35)


# ══════════════════════════════════════════════════════════════════════════════
# IMPORTANT QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════

_IQ_LEVEL_GUIDE = {
    "Beginner":     "conceptual and definitional",
    "Intermediate": "application and analytical",
    "Advanced":     "synthesis, comparison, and critical thinking",
}


def generate_important_questions(topic: str, level: str, count: int = 6) -> str:
    """Generate exam-relevant subjective questions."""
    is_valid, result = validate_topic(topic)
    if not is_valid:
        return f"⚠️ {result}"

    guide = _IQ_LEVEL_GUIDE.get(level, "")
    prompt = (
        f"Generate {count} important exam questions on: {result}\n"
        f"Level: {level} — {guide}\n\n"
        f"RULES: Questions must be concept-heavy. No yes/no. Specific to {result}.\n\n"
        f"FORMAT:\nQ1: [question]\nType: [Conceptual/Analytical/Applied]\nLength: [Short/Medium/Long]\n\n"
        f"Continue for all {count} questions."
    )
    return _call(prompt, max_tokens=700, temperature=0.3)


def parse_questions(raw: str) -> List[Dict]:
    """
    Parse raw LLM important-question text into structured dicts.
    Pure function — no side effects, fully testable.
    """
    qs = []
    if not raw:
        return qs
    try:
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw.strip()) if b.strip()]
        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            q_text = re.sub(r"^Q\d+[:.]\s*", "", lines[0]).strip()
            if not q_text or len(q_text) < 10:
                continue
            qtype, qlen = "Conceptual", "Medium"
            for line in lines[1:]:
                if "Type:" in line:
                    qtype = line.split("Type:")[-1].strip()
                if "Length:" in line or "length:" in line.lower():
                    qlen = line.split(":")[-1].strip()
            qs.append({"q": q_text, "type": qtype, "length": qlen})
    except Exception:
        pass
    return qs


# ══════════════════════════════════════════════════════════════════════════════
# ANSWER EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_answer(question: str, user_answer: str, topic: str, level: str) -> str:
    """Evaluate a student's written answer with rubric scoring."""
    is_valid, result = validate_answer(user_answer)
    if not is_valid:
        return f"⚠️ {result}"

    is_valid_q, clean_q = validate_topic(question)
    if not is_valid_q:
        return f"⚠️ {clean_q}"

    prompt = (
        f"Evaluate this student answer.\n\n"
        f"Topic: {topic} | Level: {level}\n"
        f"Question: {clean_q}\n\n"
        f"Student Answer:\n{result[:2000]}\n\n"
        "## 📊 Score\n[X/10 — be precise and fair]\n\n"
        "## ✅ Strengths\n[What the student got right — specific]\n\n"
        "## ❌ Weaknesses\n[What is wrong or missing — specific]\n\n"
        "## 🧩 Missing Concepts\n[Important concepts not mentioned]\n\n"
        "## 💡 Suggestions\n[How to improve this answer]\n\n"
        "## 📝 Ideal Answer Structure\n[How a perfect answer should be organized]\n\n"
        f"Be specific to '{topic}'. Zero generic feedback."
    )
    return _call(prompt, max_tokens=900, temperature=0.35)


def extract_score(evaluation_text: str) -> float:
    """Extract numeric score (0-10) from an evaluation string. Pure function."""
    try:
        m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", evaluation_text or "")
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return 0.0


# ══════════════════════════════════════════════════════════════════════════════
# AI TUTOR
# ══════════════════════════════════════════════════════════════════════════════

def tutor_chat(
    user_input: str,
    topic: str,
    level: str,
    profile: Dict,
    chat_history: List[Dict],
    weak_areas: List[str],
    past_chats: Optional[List[Dict]] = None,
    rag_context: str = "",
) -> str:
    """Generate a tutor response personalised to the student's profile."""
    is_valid, clean_input = validate_chat_input(user_input)
    if not is_valid:
        return f"⚠️ {clean_input}"

    mastery = profile.get("mastery_score", 0)
    trend   = profile.get("trend_label", "N/A")
    weak_topics = profile.get("weak_topics", [])

    if mastery < 40:
        style = "intuition-first with analogies and step-by-step breakdowns"
        tone  = "Student is at foundational level — be encouraging and use very simple language."
    elif mastery < 70:
        style = "clear explanations with technical terms and concrete examples"
        tone  = "Student has intermediate understanding — balance clarity with depth."
    else:
        style = "deep technical explanations with edge cases"
        tone  = "Student has strong mastery — go deep and challenge them."

    recent = "".join(
        f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['text'][:150]}\n"
        for m in chat_history[-6:]
    )
    memory = "".join(
        f"- Student asked: {(c.get('user') or '')[:80]}\n"
        for c in (past_chats or [])[:3]
    )
    weak_ctx = ""
    if weak_topics:
        weak_ctx += f"Weak topics: {', '.join(weak_topics[:3])}.\n"
    if weak_areas:
        weak_ctx += f"Weak questions: {', '.join(wa[:40] for wa in weak_areas[:2])}.\n"

    stag        = "Student appears stuck — suggest a different approach.\n" if profile.get("stagnation") else ""
    topic_str   = topic or "General"
    memory_part = ("MEMORY:\n" + memory + "\n") if memory else ""
    rag_part    = (rag_context + "\n\n")         if rag_context else ""
    recent_part = recent or "None"

    prompt = (
        "STUDENT PROFILE:\n"
        "- Topic: " + topic_str + "\n"
        "- Level: " + level + " | Mastery: " + str(mastery) + "% | Trend: " + trend + "\n"
        + weak_ctx + stag + tone + "\n\n"
        + memory_part + rag_part
        + "RECENT CONVERSATION:\n" + recent_part + "\n\n"
        + "STUDENT ASKS: " + clean_input + "\n\n"
        "RESPOND IN THIS EXACT STRUCTURE:\n\n"
        "**Direct Answer:**\n[1-2 sentences]\n\n"
        "**Explanation:**\n[Use " + style + "] — specific to '" + topic_str + "'\n\n"
        "**Example:**\n[One concrete specific example]\n\n"
        "**Key Takeaway:**\n[One sentence to remember]\n\n"
        "RULES: 100% specific. Reference weak areas if relevant. Max 220 words."
    )
    return _call(prompt, max_tokens=450, temperature=0.45)


def tutor_post_quiz(
    topic: str,
    correct: int,
    total: int,
    wrong: List[str],
    weak_topics: List[str],
    level: str,
) -> str:
    """Short tutor message shown immediately after a quiz submission."""
    pct        = int(correct / total * 100) if total else 0
    wrong_text = "\n".join(f"- {q}" for q in wrong[:3]) if wrong else "None"
    weak_text  = ", ".join(weak_topics[:3]) if weak_topics else "None"

    prompt = (
        f"AI Tutor response after quiz on: {topic}\n"
        f"Score: {pct}% | Wrong:\n{wrong_text}\nWeak topics: {weak_text}\n\n"
        "**What I noticed:**\n[1-2 sentences on weak concepts]\n\n"
        "**Recommended next steps:**\n"
        "1. [Specific action]\n2. [Specific action]\n3. [Specific action]\n\n"
        "**Quick explanation:**\n[Brief explanation of the most-missed concept]\n\n"
        f"Be specific to {topic}. Max 150 words."
    )
    return _call(prompt, max_tokens=300, temperature=0.4)


def tutor_post_eval(
    question: str,
    score: float,
    weaknesses: str,
    missing: str,
    topic: str,
) -> str:
    """Tutor guidance shown after a subjective answer is evaluated."""
    prompt = (
        f"AI Tutor after subjective evaluation on: {topic}\n"
        f"Question: {question[:150]}\nScore: {score}/10\n"
        f"Weaknesses: {weaknesses[:200] or 'None'}\n"
        f"Missing: {missing[:200] or 'None'}\n\n"
        "**What you missed:**\n[Specific gaps]\n\n"
        "**How to improve:**\n[2-3 specific actionable steps]\n\n"
        "**Study this next:**\n[Specific subtopic or concept]\n\n"
        f"Max 130 words. Be specific to {topic}."
    )
    return _call(prompt, max_tokens=280, temperature=0.4)


def generate_study_plan(
    topic: str,
    weak_topics: List[str],
    level: str,
    goal: str,
    days: int,
    daily_hours: float,
    profile: Dict,
) -> str:
    """Generate an AI-written multi-day study plan."""
    is_valid, result = validate_topic(topic)
    if not is_valid:
        return f"⚠️ {result}"

    weak_text = ", ".join(weak_topics[:4]) if weak_topics else "None"
    mastery   = profile.get("mastery_score", 0)

    prompt = (
        f"Create a SPECIFIC {days}-day study plan.\n"
        f"Topic: {result} | Level: {level} | Goal: {goal}\n"
        f"Mastery: {mastery}% | Daily: {daily_hours}h | Weak: {weak_text}\n\n"
        f"## 📅 {days}-Day Plan for {result}\n\n"
        "Each day: main task + video search query + practice + time allocation.\n\n"
        f"## 📌 Milestones\n[Day 3, {days // 2}, {days}]\n\n"
        "## ✅ Success Criteria\n[3 measurable outcomes]\n\n"
        "## 💡 Daily Tips\n[2-3 motivational study reminders]\n\n"
        f"Make tasks SMALL, ACHIEVABLE, SPECIFIC to {result}."
    )
    return _call(prompt, max_tokens=1100, temperature=0.4)


def video_ai_note(
    topic: str,
    level: str,
    title: str,
    weak_topics: List[str],
    score: int,
) -> str:
    """Generate a 2-sentence AI note explaining why a video was recommended."""
    weak_text = ", ".join(weak_topics[:2]) if weak_topics else "None"
    prompt = (
        f"In exactly 2 sentences explain why this video is recommended:\n"
        f"Student: topic='{topic}' level={level} weak areas={weak_text}\n"
        f"Video: '{title}' | Relevance score: {score}/100\n"
        "Mention weak areas if relevant. No generic phrases."
    )
    return _call(prompt, max_tokens=70, temperature=0.3)