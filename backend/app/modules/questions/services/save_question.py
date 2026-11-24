"""Tạo và sửa câu hỏi.

Quy tắc phiên bản: bản nháp sửa trực tiếp; bản đã đăng/đã ẩn thì lưu thành phiên bản nháp mới
(phien_ban + 1, cùng ma_goc_id). Câu con đi theo câu cha và giữ ma_goc_id của chính nó.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.questions.repositories.question_rows import (
    exams_using,
    find_question,
    insert_question,
    latest_version,
    list_children,
    replace_options,
    update_question,
    delete_question_row,
)
from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.question_rules import QuestionRuleError, validate_question


def _parent_values(q) -> dict:
    values = q.model_dump(exclude={"phuong_an", "dap_an_chap_nhan", "cau_con"})
    return values


def _child_values(child) -> dict:
    values = child.model_dump(exclude={"id", "phuong_an", "dap_an_chap_nhan"})
    # Câu con không tự phân loại (theo câu cha) và không có cờ mục đích riêng
    values.update({"cap_do_id": None, "ky_nang": None, "dung_on_luyen": False,
                   "dung_thi_thu": False, "dung_dau_vao": False, "tu_vung_id": None})
    return values


def _check_level(db: Session, cap_do_id: int, tu_vung_id: int | None = None) -> None:
    exists = db.execute(text("SELECT EXISTS(SELECT 1 FROM cap_do WHERE id = :id)"), {"id": cap_do_id}).scalar_one()
    if not exists:
        raise QuestionRuleError("Cấp độ không tồn tại")
    if tu_vung_id is not None:
        word_level = db.execute(text("SELECT cap_do_id FROM tu_vung WHERE id = :id"), {"id": tu_vung_id}).scalar_one_or_none()
        if word_level is None:
            raise QuestionRuleError("Từ vựng được gắn không tồn tại")
        if word_level != cap_do_id:
            raise QuestionRuleError("Từ vựng được gắn phải cùng cấp với câu hỏi")


def _check_group(db: Session, q) -> None:
    group = getattr(q, "nhom_kien_thuc_id", None)
    if group is None:
        return
    if q.dang == "ngu_lieu":
        raise QuestionRuleError("Ngữ liệu chung không gắn nhóm kiến thức; gắn ở từng câu đơn")
    ok = db.execute(text("SELECT EXISTS(SELECT 1 FROM nhom_kien_thuc WHERE id = :id AND trang_thai = 'hoat_dong')"),
                    {"id": group}).scalar_one()
    if not ok:
        raise QuestionRuleError("Nhóm kiến thức không tồn tại hoặc đã ẩn")


def create_question(db: Session, q, nguoi_tao_id: int) -> int:
    validate_question(q)
    try:
        _check_level(db, q.cap_do_id, q.tu_vung_id)
        _check_group(db, q)
        parent_id = insert_question(db, _parent_values(q), None, 1, None, nguoi_tao_id)
        replace_options(db, parent_id, q.phuong_an, q.dap_an_chap_nhan)
        for child in q.cau_con:
            if child.id is not None:
                raise QuestionRuleError("Câu mới không được mang id câu con")
            child_id = insert_question(db, _child_values(child), None, 1, parent_id, nguoi_tao_id)
            replace_options(db, child_id, child.phuong_an, child.dap_an_chap_nhan)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return parent_id


def update_question_content(db: Session, cau_hoi_id: int, q, nguoi_tao_id: int) -> int:
    """Trả id của phiên bản sau khi lưu (giữ nguyên nếu là nháp, id mới nếu tạo phiên bản)."""
    validate_question(q)
    try:
        _check_level(db, q.cap_do_id, q.tu_vung_id)
        _check_group(db, q)
        row = find_question(db, cau_hoi_id, for_update=True)
        if row is None or row["cau_cha_id"] is not None:
            raise NotFoundError()
        if row["phien_ban"] != latest_version(db, row["ma_goc_id"]):
            raise ConflictError("Đây không phải phiên bản mới nhất. Hãy mở phiên bản mới nhất để sửa.")

        old_children = {c["id"]: c for c in list_children(db, row["id"], for_update=True)}
        for child in q.cau_con:
            if child.id is not None and child.id not in old_children:
                raise QuestionRuleError("Câu con không thuộc câu hỏi này")

        if row["trang_thai"] == "nhap":
            result_id = _edit_draft(db, row, q, old_children, nguoi_tao_id)
        else:
            result_id = _new_version(db, row, q, old_children, nguoi_tao_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result_id


def _edit_draft(db: Session, row: dict, q, old_children: dict, nguoi_tao_id: int) -> int:
    update_question(db, row["id"], _parent_values(q))
    replace_options(db, row["id"], q.phuong_an, q.dap_an_chap_nhan)

    kept = {child.id for child in q.cau_con if child.id is not None}
    removed = [cid for cid in old_children if cid not in kept]
    if removed:
        used = exams_using(db, removed)
        if used:
            names = ", ".join(e["ten"] for e in used)
            raise ConflictError(f"Không xóa được câu con đang nằm trong đề: {names}. Gỡ khỏi đề trước.")
        for cid in removed:
            delete_question_row(db, cid)

    for child in q.cau_con:
        if child.id is not None:
            update_question(db, child.id, _child_values(child))
            replace_options(db, child.id, child.phuong_an, child.dap_an_chap_nhan)
        else:
            child_id = insert_question(db, _child_values(child), None, 1, row["id"], nguoi_tao_id)
            replace_options(db, child_id, child.phuong_an, child.dap_an_chap_nhan)
    return row["id"]


def _new_version(db: Session, row: dict, q, old_children: dict, nguoi_tao_id: int) -> int:
    parent_id = insert_question(db, _parent_values(q), row["ma_goc_id"], row["phien_ban"] + 1, None, nguoi_tao_id)
    replace_options(db, parent_id, q.phuong_an, q.dap_an_chap_nhan)
    for child in q.cau_con:
        if child.id is not None:
            old = old_children[child.id]
            version = latest_version(db, old["ma_goc_id"]) + 1
            child_id = insert_question(db, _child_values(child), old["ma_goc_id"], version, parent_id, nguoi_tao_id)
        else:
            child_id = insert_question(db, _child_values(child), None, 1, parent_id, nguoi_tao_id)
        replace_options(db, child_id, child.phuong_an, child.dap_an_chap_nhan)
    return parent_id
