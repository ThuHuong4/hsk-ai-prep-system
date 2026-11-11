import json

from sqlalchemy.orm import Session

from app.modules.attempts.repositories.find_attempt import lock_exam_attempt_for_user
from app.modules.attempts.repositories.upsert_answer import (
    find_answer_for_update,
    increment_attempt_save_version,
    update_answer,
)

IN_PROGRESS = 0  # luot_hoc.trang_thai: 0 = Đang làm


class AttemptNotFoundError(Exception):
    pass


class AttemptFinishedError(Exception):
    pass


class AttemptExpiredError(Exception):
    pass


class QuestionNotInAttemptError(Exception):
    pass


class InvalidAnswerError(Exception):
    pass


class SaveConflictError(Exception):
    def __init__(self, current: dict):
        super().__init__("Xung đột phiên bản lưu")
        self.current = current


def _load_json(value):
    if value is None:
        return None
    if isinstance(value, (str, bytes, bytearray)):
        return json.loads(value)
    return value


def _validate_answer(snapshot: dict, cau_tra_loi: str | None) -> None:
    valid_symbols = {option["ky_hieu"] for option in snapshot.get("phuong_an") or []}
    if not valid_symbols:
        raise InvalidAnswerError("Dạng câu hỏi này chưa hỗ trợ lưu câu trả lời")
    if cau_tra_loi is not None and cau_tra_loi not in valid_symbols:
        raise InvalidAnswerError("Phương án không hợp lệ")


def _state(ma_cau_hoi: int, cau_tra_loi, danh_dau_xem_lai, phien_ban_luu: int) -> dict:
    return {
        "ma_cau_hoi": ma_cau_hoi,
        "cau_tra_loi": cau_tra_loi,
        "danh_dau_xem_lai": bool(danh_dau_xem_lai),
        "phien_ban_luu": phien_ban_luu,
    }


def save_answer(
    db: Session,
    ma_nguoi_dung: int,
    ma_luot: int,
    ma_cau_hoi: int,
    cau_tra_loi: str | None,
    danh_dau_xem_lai: bool,
    so_thu_tu_luu: int,
) -> dict:
    try:
        attempt = lock_exam_attempt_for_user(db, ma_luot, ma_nguoi_dung)
        if attempt is None:
            raise AttemptNotFoundError()
        if attempt["trang_thai"] != IN_PROGRESS:
            raise AttemptFinishedError()
        if attempt["da_het_han"]:
            # Tạm thời: bước nộp bài sẽ tự chấm lượt quá hạn
            raise AttemptExpiredError()

        answer = find_answer_for_update(db, ma_luot, ma_cau_hoi)
        if answer is None:
            raise QuestionNotInAttemptError()

        _validate_answer(_load_json(answer["cau_hoi_chup"]), cau_tra_loi)

        current = _state(
            ma_cau_hoi, answer["cau_tra_loi"], answer["danh_dau_xem_lai"], answer["phien_ban_luu"]
        )
        same_content = (
            current["cau_tra_loi"] == cau_tra_loi
            and current["danh_dau_xem_lai"] == danh_dau_xem_lai
        )

        if so_thu_tu_luu > current["phien_ban_luu"]:
            update_answer(db, answer["ma_chi_tiet"], cau_tra_loi, danh_dau_xem_lai, so_thu_tu_luu)
            increment_attempt_save_version(db, ma_luot)
            result = _state(ma_cau_hoi, cau_tra_loi, danh_dau_xem_lai, so_thu_tu_luu)
            result["da_ghi"] = True
        elif so_thu_tu_luu == current["phien_ban_luu"] and not same_content:
            raise SaveConflictError(current)
        else:
            # Gửi lại cùng nội dung, hoặc request cũ đến muộn: không ghi, trả trạng thái hiện tại
            result = {**current, "da_ghi": False}

        result["con_lai_giay"] = attempt["con_lai_giay"]
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise