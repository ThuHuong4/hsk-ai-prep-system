import hashlib
import json

from sqlalchemy.orm import Session

from app.modules.attempts.repositories.create_attempt import create_exam_attempt
from app.modules.attempts.repositories.find_attempt import find_active_exam_attempt, lock_user
from app.modules.attempts.repositories.list_attempt_answers import list_attempt_answers
from app.modules.exams.repositories.exam_snapshot_source import (
    find_published_exam_for_snapshot,
    list_snapshot_questions,
)
from app.modules.exams.repositories.list_exam_content import (
    list_options,
    list_question_groups,
    list_sections,
)

_PUBLIC_SECTION_FIELDS = ("ma_phan", "thu_tu", "ten_phan", "ma_ky_nang", "huong_dan")
_PUBLIC_GROUP_FIELDS = ("ma_nhom_cau_hoi", "noi_dung", "hinh_anh_url")
_PUBLIC_QUESTION_FIELDS = (
    "ma_cau_hoi", "so_cau", "ma_dang", "noi_dung", "ngu_lieu",
    "am_thanh_url", "hinh_anh_url", "ma_nhom_cau_hoi",
)
_PUBLIC_OPTION_FIELDS = ("ma_phuong_an", "ky_hieu", "noi_dung", "hinh_anh_url", "thu_tu")


class UserNotFoundError(Exception):
    pass


class ExamNotAvailableError(Exception):
    pass


class AttemptExpiredError(Exception):
    pass


def _canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_json(value):
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        return json.loads(value)
    return value


def _pick(data: dict, fields: tuple) -> dict:
    return {field: data.get(field) for field in fields}


def _build_snapshot(db: Session, exam: dict) -> tuple[str, list[dict]]:
    ma_bo_de = exam["ma_bo_de"]
    questions = list_snapshot_questions(db, ma_bo_de)
    if not questions:
        raise ExamNotAvailableError()

    options_by_question: dict[int, list[dict]] = {}
    for option in list_options(db, ma_bo_de):
        options_by_question.setdefault(option.pop("ma_cau_hoi"), []).append(option)

    cau_hinh = {
        "ma_bo_de": exam["ma_bo_de"],
        "ma_cap_do": exam["ma_cap_do"],
        "ten_bo_de": exam["ten_bo_de"],
        "thoi_gian_giay": exam["thoi_gian_giay"],
        "am_thanh_url": exam["am_thanh_url"],
        "phien_ban": exam["phien_ban"],
        "quy_tac_cham": _load_json(exam["quy_tac_cham"]),
        "phan": list_sections(db, ma_bo_de),
        "nhom_cau_hoi": list_question_groups(db, ma_bo_de),
    }

    chi_tiet = []
    for so_cau, question in enumerate(questions, start=1):
        snapshot = {
            "ma_cau_hoi": question["ma_cau_hoi"],
            "ma_phan": question["ma_phan"],
            "so_cau": so_cau,
            "ma_dang": question["ma_dang"],
            "noi_dung": question["noi_dung"],
            "ngu_lieu": question["ngu_lieu"],
            "am_thanh_url": question["am_thanh_url"],
            "hinh_anh_url": question["hinh_anh_url"],
            "ma_nhom_cau_hoi": question["ma_nhom_cau_hoi"],
            "phuong_an": options_by_question.get(question["ma_cau_hoi"], []),
            "dap_an_chuan": question["dap_an_chuan"],
            "cham_tu_dong": question["cham_tu_dong"],
        }
        snapshot_json = _canonical_json(snapshot)
        chi_tiet.append({
            "ma_cau_hoi": question["ma_cau_hoi"],
            "ma_ky_nang": question["ma_ky_nang"],
            "ma_dang": question["ma_dang"],
            "thu_tu": so_cau,
            "phien_ban_cau_hoi": question["phien_ban"],
            "bam_noi_dung": hashlib.sha256(snapshot_json.encode("utf-8")).digest(),
            "cau_hoi_chup": snapshot_json,
            "diem_toi_da": question["diem_toi_da"],
        })

    return _canonical_json(cau_hinh), chi_tiet


def _build_response(attempt: dict, answers: list[dict], khoi_phuc: bool) -> dict:
    cau_hinh = _load_json(attempt["cau_hinh_chup"])

    questions_by_section: dict[int, list[dict]] = {}
    for answer in answers:
        snapshot = _load_json(answer["cau_hoi_chup"])
        question = _pick(snapshot, _PUBLIC_QUESTION_FIELDS)
        question["phuong_an"] = [
            _pick(option, _PUBLIC_OPTION_FIELDS) for option in snapshot.get("phuong_an", [])
        ]
        question["cau_tra_loi"] = answer["cau_tra_loi"]
        question["danh_dau_xem_lai"] = bool(answer["danh_dau_xem_lai"])
        question["phien_ban_luu"] = answer["phien_ban_luu"]
        questions_by_section.setdefault(snapshot["ma_phan"], []).append(question)

    sections = []
    for section in sorted(cau_hinh["phan"], key=lambda item: item["thu_tu"]):
        item = _pick(section, _PUBLIC_SECTION_FIELDS)
        item["cau_hoi"] = questions_by_section.get(section["ma_phan"], [])
        sections.append(item)

    return {
        "ma_luot": attempt["ma_luot"],
        "khoi_phuc": khoi_phuc,
        "ma_bo_de": cau_hinh["ma_bo_de"],
        "ma_cap_do": cau_hinh["ma_cap_do"],
        "ten_bo_de": cau_hinh["ten_bo_de"],
        "am_thanh_url": cau_hinh["am_thanh_url"],
        "thoi_gian_giay": cau_hinh["thoi_gian_giay"],
        "bat_dau_luc": attempt["bat_dau_luc"],
        "han_nop_luc": attempt["han_nop_luc"],
        "con_lai_giay": int(attempt["con_lai_giay"]),
        "nhom_cau_hoi": [_pick(g, _PUBLIC_GROUP_FIELDS) for g in cau_hinh.get("nhom_cau_hoi", [])],
        "phan": sections,
    }


def start_exam_attempt(db: Session, ma_nguoi_dung: int, ma_bo_de: int) -> dict:
    try:
        if not lock_user(db, ma_nguoi_dung):
            raise UserNotFoundError()

        attempt = find_active_exam_attempt(db, ma_nguoi_dung, ma_bo_de)
        khoi_phuc = attempt is not None

        if attempt is None:
            exam = find_published_exam_for_snapshot(db, ma_bo_de)
            if exam is None:
                raise ExamNotAvailableError()
            cau_hinh_chup, chi_tiet = _build_snapshot(db, exam)
            create_exam_attempt(
                db, ma_nguoi_dung, exam["ma_cap_do"], ma_bo_de,
                exam["thoi_gian_giay"], cau_hinh_chup, chi_tiet,
            )
            attempt = find_active_exam_attempt(db, ma_nguoi_dung, ma_bo_de)
        elif attempt["da_het_han"]:
            # Tạm thời: bước nộp bài sẽ tự chấm lượt quá hạn thay cho lỗi này
            raise AttemptExpiredError()

        response = _build_response(attempt, list_attempt_answers(db, attempt["ma_luot"]), khoi_phuc)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise