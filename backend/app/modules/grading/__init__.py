"""Module chấm điểm và nạp câu hỏi làm bài dùng chung toàn hệ thống."""
from app.modules.grading.objective_grader import (
    AI_GRADED_TYPES,
    CHOICE_TYPES,
    OBJECTIVE_TYPES,
    TEXT_OBJECTIVE_TYPES,
    correct_option_id,
    is_correct,
    normalize_answer_text,
)
from app.modules.grading.question_loader import (
    QUESTION_FIELDS,
    load_questions_by_ids,
    load_set_items,
    shuffle_choice_options,
)

__all__ = [
    "AI_GRADED_TYPES",
    "CHOICE_TYPES",
    "OBJECTIVE_TYPES",
    "TEXT_OBJECTIVE_TYPES",
    "QUESTION_FIELDS",
    "correct_option_id",
    "is_correct",
    "load_questions_by_ids",
    "load_set_items",
    "normalize_answer_text",
    "shuffle_choice_options",
]
