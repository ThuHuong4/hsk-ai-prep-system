from sqlalchemy.orm import Session

from app.modules.questions.repositories.question_rows import (
    delete_question_row,
    exams_using,
    find_question,
    is_answered,
    latest_version,
    list_children,
    mark_approved,
    published_versions,
    set_status,
)
from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.question_rules import QuestionRuleError


def _load_top(db: Session, cau_hoi_id: int) -> dict:
    row = find_question(db, cau_hoi_id, for_update=True)
    if row is None or row["cau_cha_id"] is not None:
        raise NotFoundError()
    return row


def _family(db: Session, row: dict) -> list[int]:
    return [row["id"]] + [c["id"] for c in list_children(db, row["id"], for_update=True)]


def publish_question(db: Session, cau_hoi_id: int, nguoi_duyet_id: int | None = None) -> None:
    """Đăng bản nháp (= Giảng viên duyệt); bản đang dùng trước đó chuyển sang đã ẩn (lượt mới dùng bản mới).
    Lượt đang làm và lịch sử vẫn giữ phiên bản cũ đã ghim."""
    try:
        row = _load_top(db, cau_hoi_id)
        if row["trang_thai"] != "nhap":
            raise ConflictError("Chỉ đăng được bản nháp")
        # Câu Nghe do AI soạn chỉ có lời thoại: phải tải tệp âm thanh thật trước khi đăng
        if row["ky_nang"] == "nghe" and row["nguon_noi_dung"] == "soan_voi_ai":
            children = list_children(db, row["id"])
            if not row["tep_audio"] and not any(c["tep_audio"] for c in children):
                raise QuestionRuleError("Câu Nghe soạn với AI cần tải tệp âm thanh thật khớp lời nghe trước khi đăng")
        for old_id in published_versions(db, row["ma_goc_id"]):
            old = find_question(db, old_id, for_update=True)
            set_status(db, _family(db, old), "da_an")
        set_status(db, _family(db, row), "da_dang")
        if nguoi_duyet_id is not None:  # script nạp dữ liệu không có người duyệt
            mark_approved(db, row["id"], nguoi_duyet_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def hide_question(db: Session, cau_hoi_id: int) -> None:
    try:
        row = _load_top(db, cau_hoi_id)
        if row["trang_thai"] != "da_dang":
            raise ConflictError("Chỉ ẩn được câu đang đăng")
        set_status(db, _family(db, row), "da_an")
        db.commit()
    except Exception:
        db.rollback()
        raise


def show_question(db: Session, cau_hoi_id: int) -> None:
    try:
        row = _load_top(db, cau_hoi_id)
        if row["trang_thai"] != "da_an":
            raise ConflictError("Chỉ hiện lại được câu đã ẩn")
        if row["phien_ban"] != latest_version(db, row["ma_goc_id"]):
            raise ConflictError("Chỉ hiện lại được phiên bản mới nhất")
        if published_versions(db, row["ma_goc_id"]):
            raise ConflictError("Câu này đã có một phiên bản đang đăng")
        set_status(db, _family(db, row), "da_dang")
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_draft_question(db: Session, cau_hoi_id: int) -> None:
    try:
        row = _load_top(db, cau_hoi_id)
        if row["trang_thai"] != "nhap":
            raise ConflictError("Chỉ xóa được bản nháp. Câu đã đăng thì dùng Ẩn.")
        family = _family(db, row)
        used = exams_using(db, family)
        if used:
            names = ", ".join(e["ten"] for e in used)
            raise ConflictError(f"Câu đang nằm trong đề: {names}. Gỡ khỏi đề trước khi xóa.")
        if is_answered(db, family):
            raise ConflictError("Câu đã có người làm, không xóa được")
        for cid in family[1:]:
            delete_question_row(db, cid)
        delete_question_row(db, row["id"])
        db.commit()
    except Exception:
        db.rollback()
        raise
