from .llm_service import (
    generate_notes, notes_from_document,
    generate_quiz, parse_quiz, analyze_quiz,
    generate_important_questions, parse_questions,
    evaluate_answer, extract_score,
    tutor_chat, tutor_post_quiz, tutor_post_eval,
    generate_study_plan, video_ai_note,
)
from .youtube_service import search_videos, build_placeholders
from .ranking_service import rank_video, build_explanation, LEVEL_KEYWORDS, IDEAL_DURATION
from .learning_engine import (
    compute_profile, update_weak_areas, smart_recommend,
    get_prerequisites, get_learning_gaps, get_unlocked_by,
    get_learning_path, build_study_structure,
)
from .rag_service import (
    index_note, retrieve_context, build_rag_context_block,
    get_indexed_topics, delete_user_index, is_available as rag_available,
)
from .spaced_repetition import (
    new_card, update_card, get_due_cards, get_upcoming_cards,
    days_until_review, format_due_label, srs_stats,
)
from .streak_service import compute_streak, streak_message, BADGES
