from sqlalchemy.orm import Session

from app.modules.exams.repositories.find_exam_by_id import find_exam_by_id
from app.modules.exams.repositories.list_exam_content import (
    list_options,
    list_question_groups,
    list_questions,
    list_sections,
)


def build_exam_preview(db: Session, ma_bo_de: int) -> dict | None:
    exam = find_exam_by_id(db, ma_bo_de)
    if exam is None:
        return None

    options_by_question: dict[int, list[dict]] = {}
    for option in list_options(db, ma_bo_de):
        ma_cau_hoi = option.pop("ma_cau_hoi")
        options_by_question.setdefault(ma_cau_hoi, []).append(option)

    questions_by_section: dict[int, list[dict]] = {}
    for so_cau, question in enumerate(list_questions(db, ma_bo_de), start=1):
        ma_phan = question.pop("ma_phan")
        question["so_cau"] = so_cau
        question["phuong_an"] = options_by_question.get(question["ma_cau_hoi"], [])
        questions_by_section.setdefault(ma_phan, []).append(question)

    sections = list_sections(db, ma_bo_de)
    for section in sections:
        section["cau_hoi"] = questions_by_section.get(section["ma_phan"], [])

    exam["nhom_cau_hoi"] = list_question_groups(db, ma_bo_de)
    exam["phan"] = sections
    return exam