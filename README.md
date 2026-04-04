# 🎓 LEARNIFY AI

> **Personalized AI Learning · Resource Intelligence Engine · Adaptive Tutor**

[![CI](https://github.com/Richasinhaaa/LEARNIFY-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Richasinhaaa/LEARNIFY-AI/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-FF4B4B)](https://streamlit.io)

---

## What it does

Learnify AI is a full-stack adaptive learning platform that:

- **YouTube Engine** — Ranks videos 0-100 across 5 explicit criteria (topic relevance, level match, duration fit, weak topic boost, popularity)
- **AI Notes** — Generates structured, goal-aware notes via Groq LLaMA 3.3 70B
- **Quiz Engine** — Creates topic-specific MCQs and tracks weak areas across sessions
- **Answer Evaluation** — Grades subjective answers with rubric scoring (0-10)
- **AI Tutor** — Personalised chat that adapts to your mastery level and quiz history
- **Study Planner** — Rule-based day structure + AI narrative, exportable
- **Progress Analytics** — Mastery score, trend detection, stagnation alerts, per-topic scores

---

## Architecture

```
learnify/
├── app.py                    # Router only (~30 lines)
├── pages/                    # One file per page, each exports render()
│   ├── login.py
│   ├── dashboard.py
│   ├── youtube.py
│   ├── notes.py
│   ├── quiz.py
│   ├── questions.py
│   ├── chat.py
│   ├── planner.py
│   ├── upload.py
│   └── progress.py
├── services/                 # Business logic — no Streamlit, fully testable
│   ├── llm_service.py        # All Groq/LLM calls + prompt construction
│   ├── youtube_service.py    # YouTube search + normalisation
│   ├── ranking_service.py    # Video scoring engine (pure functions)
│   └── learning_engine.py    # Concept graph, profile, recommendations
├── database/
│   ├── db.py                 # MongoDB connection singleton
│   └── user_repo.py          # All queries (repository pattern)
├── models/
│   └── user_model.py         # Typed dataclasses for all domain objects
├── ui/
│   ├── styles.py             # Global CSS (single source of truth)
│   ├── session.py            # Session state bootstrap
│   ├── sidebar.py            # Navigation sidebar
│   └── components.py         # Shared reusable UI fragments
├── tests/
│   ├── test_ranking_service.py
│   └── test_llm_service.py
└── requirements.txt          # Pinned versions
```

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/Richasinhaaa/LEARNIFY-AI.git
cd LEARNIFY-AI

# 2. Install
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
# Edit .env with your keys

# 4. Run
streamlit run app.py

# 5. Test
pytest tests/ -v
```

---

## Environment variables

```env
GROQ_API_KEY=your_groq_key_here
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
```

For Streamlit Cloud, add these in **App Settings → Secrets**.

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit 1.35 |
| LLM | Groq (LLaMA 3.3 70B) |
| Database | MongoDB Atlas (pymongo) |
| YouTube | youtube-search-python |
| PDF | PyPDF2 |
| Tests | pytest |
| CI | GitHub Actions |

---

## Ranking engine (how videos are scored)

The Resource Intelligence Engine scores each video across 5 weighted criteria:

| Criterion | Weight | How scored |
|---|---|---|
| Topic Relevance | 30 pts | Keyword hits in title + description |
| Level Match | 25 pts | Beginner/intermediate/advanced keyword detection |
| Duration Fit | 20 pts | Ideal range: Beginner 4-22min, Intermediate 10-50min, Advanced 20-120min |
| Weak Topic Boost | 15 pts | Matches quiz-derived weak areas |
| Popularity Signal | 10 pts | View count (M/K normalised) |

Videos are sorted descending by total score; top 5 displayed.
