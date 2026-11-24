"""Giảng viên soạn đề thi thử (bo_de.loai = 'de_thi').

Phiên bản: bản nháp sửa trực tiếp; đề đã đăng muốn sửa thì tạo bản nháp mới (sao chép danh sách câu).
Đăng bản mới thì bản đang dùng cũ chuyển đã ẩn; lượt đang làm vẫn giữ phiên bản đã ghim.
"""
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.integrity import is_duplicate_key
from app.modules.exam_authoring.repositories.exam_rows import (
    count_versions,
    delete_exam_row,
    find_exam,
    has_attempts,
    insert_exam,
    latest_exam_version,
    list_items,
    published_exam_versions,
    replace_items,
    root_code,
    set_exam_status,
    update_exam,
    update_root_code,
)
from app.modules.questions.repositories.question_rows import find_question, list_options
from app.modules.questions.services.errors import ConflictError, NotFoundError
from app.modules.questions.services.get_question import _shape
from app.modules.questions.services.question_rules import QuestionRuleError

_DEFAULT_PART = {"nghe": 1, "doc": 2, "viet": 3, "tu_vung": 4}


def _check_level(db: Session, cap_do_id: int) -> None:
    if not db.execute(text("SELECT EXISTS(SELECT 1 FROM cap_do WHERE id = :id)"), {"id": cap_do_id}).scalar_one():
        raise QuestionRuleError("Cấp độ không tồn tại")


def _load(db: Session, bo_de_id: int) -> dict:
    exam = find_exam(db, bo_de_id, for_update=True)
    if exam is None:
        raise NotFoundError()
    return exam


def _load_draft(db: Session, bo_de_id: int) -> dict:
    exam = _load(db, bo_de_id)
    if exam["trang_thai"] != "nhap":
        raise ConflictError("Đề đã đăng. Bấm “Tạo bản nháp để sửa” trước khi chỉnh.")
    return exam


def _duplicate_code(error: IntegrityError) -> bool:
    return is_duplicate_key(error, "uq_bo_de_ma_de")


def create_exam(db: Session, info, nguoi_tao_id: int) -> int:
    try:
        _check_level(db, info.cap_do_id)
        new_id = insert_exam(db, info.model_dump(), None, 1, nguoi_tao_id)
        db.commit()
        return new_id
    except IntegrityError as error:
        db.rollback()
        if _duplicate_code(error):
            raise ConflictError("Mã đề đã tồn tại") from error
        raise
    except Exception:
        db.rollback()
        raise


def update_exam_info(db: Session, bo_de_id: int, info) -> None:
    try:
        _check_level(db, info.cap_do_id)
        exam = _load_draft(db, bo_de_id)
        current_code = root_code(db, exam["ma_goc_id"])
        if info.ma_de != current_code:
            if count_versions(db, exam["ma_goc_id"]) > 1:
                raise ConflictError("Mã đề cố định sau khi đề đã có phiên bản trước")
            update_root_code(db, exam["ma_goc_id"], info.ma_de)
        if info.cap_do_id != exam["cap_do_id"] and list_items(db, bo_de_id):
            raise ConflictError("Gỡ hết câu hỏi trước khi đổi cấp độ của đề")
        update_exam(db, bo_de_id, info.model_dump())
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if _duplicate_code(error):
            raise ConflictError("Mã đề đã tồn tại") from error
        raise
    except Exception:
        db.rollback()
        raise


def create_draft_version(db: Session, bo_de_id: int, nguoi_tao_id: int) -> int:
    try:
        exam = _load(db, bo_de_id)
        if exam["trang_thai"] == "nhap":
            return exam["id"]
        if exam["phien_ban"] != latest_exam_version(db, exam["ma_goc_id"]):
            raise ConflictError("Đã có phiên bản mới hơn của đề này")
        new_id = insert_exam(db, exam, exam["ma_goc_id"], exam["phien_ban"] + 1, nguoi_tao_id)
        replace_items(db, new_id, list_items(db, exam["id"]))
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def _question_scope(db: Session, cau_hoi_id: int) -> tuple[dict, dict | None]:
    """(câu, câu cha hoặc None); câu cha mang cấp độ/kỹ năng/cờ dùng."""
    row = find_question(db, cau_hoi_id)
    if row is None:
        raise QuestionRuleError(f"Câu hỏi #{cau_hoi_id} không tồn tại")
    if row["dang"] == "ngu_lieu":
        raise QuestionRuleError(f"Câu #{cau_hoi_id} là ngữ liệu: hãy thêm các câu con của nó")
    parent = find_question(db, row["cau_cha_id"]) if row["cau_cha_id"] else None
    return row, parent


def set_exam_items(db: Session, bo_de_id: int, items) -> None:
    try:
        exam = _load_draft(db, bo_de_id)
        seen = set()
        prepared = []
        for item in items:
            if item.cau_hoi_id in seen:
                raise QuestionRuleError(f"Câu #{item.cau_hoi_id} bị thêm 2 lần")
            seen.add(item.cau_hoi_id)
            row, parent = _question_scope(db, item.cau_hoi_id)
            owner = parent or row
            if owner["cap_do_id"] != exam["cap_do_id"]:
                raise QuestionRuleError(f"Câu #{item.cau_hoi_id} không cùng cấp độ với đề")
            prepared.append({
                "cau_hoi_id": item.cau_hoi_id,
                "phan": item.phan or _DEFAULT_PART.get(owner["ky_nang"]),
                "la_cau_vi_du": item.la_cau_vi_du,
            })
        replace_items(db, bo_de_id, prepared)
        db.commit()
    except Exception:
        db.rollback()
        raise


def publish_exam(db: Session, bo_de_id: int) -> None:
    # Nếu đề có câu Nghe mà chưa có băng Nghe liên tiếp chung, tự ghép 1 băng MP3 liên tiếp trước khi mở giao dịch đăng
    pre = find_exam(db, bo_de_id)
    if pre and pre["trang_thai"] == "nhap" and not pre["tep_audio_chung"]:
        has_listen = db.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM bo_de_cau_hoi i
                    JOIN cau_hoi q ON q.id = i.cau_hoi_id
                    LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
                    WHERE i.bo_de_id = :id AND i.la_cau_vi_du = 0 AND COALESCE(q.ky_nang, p.ky_nang) = 'nghe'
                )
            """),
            {"id": bo_de_id},
        ).scalar_one()
        if has_listen:
            from app.modules.exam_authoring.services import listening_audio
            from app.modules.exam_authoring.services.ai_media_service import AiMediaError
            try:
                listening_audio.build_for_exam_db(db, bo_de_id)
            except AiMediaError as err:
                raise QuestionRuleError(err.message) from err
    try:
        exam = _load_draft(db, bo_de_id)
        if not exam["thoi_luong_phut"]:
            raise QuestionRuleError("Cần nhập thời lượng (phút) trước khi đăng")
        items = list_items(db, bo_de_id)
        if not any(not i["la_cau_vi_du"] for i in items):
            raise QuestionRuleError("Đề cần ít nhất 1 câu tính điểm")
        for item in items:
            row, parent = _question_scope(db, item["cau_hoi_id"])
            owner = parent or row
            if row["trang_thai"] != "da_dang" or owner["trang_thai"] != "da_dang":
                raise QuestionRuleError(f"Câu #{owner['ma_goc_id']} chưa đăng hoặc đã ẩn: đăng câu đó trước")
            if not owner["dung_thi_thu"]:
                raise QuestionRuleError(f"Câu #{owner['ma_goc_id']} chưa bật “Dùng cho Thi thử”")
        for old_id in published_exam_versions(db, exam["ma_goc_id"]):
            set_exam_status(db, old_id, "da_an")
        set_exam_status(db, bo_de_id, "da_dang")
        db.commit()
    except Exception:
        db.rollback()
        raise


def hide_exam(db: Session, bo_de_id: int) -> None:
    try:
        exam = _load(db, bo_de_id)
        if exam["trang_thai"] != "da_dang":
            raise ConflictError("Chỉ ẩn được đề đang đăng")
        set_exam_status(db, bo_de_id, "da_an")
        db.commit()
    except Exception:
        db.rollback()
        raise


def show_exam(db: Session, bo_de_id: int) -> None:
    try:
        exam = _load(db, bo_de_id)
        if exam["trang_thai"] != "da_an":
            raise ConflictError("Chỉ hiện lại được đề đã ẩn")
        if exam["phien_ban"] != latest_exam_version(db, exam["ma_goc_id"]):
            raise ConflictError("Chỉ hiện lại được phiên bản mới nhất")
        if published_exam_versions(db, exam["ma_goc_id"]):
            raise ConflictError("Đề này đã có một phiên bản đang đăng")
        set_exam_status(db, bo_de_id, "da_dang")
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_draft_exam(db: Session, bo_de_id: int) -> None:
    try:
        exam = _load_draft(db, bo_de_id)
        if has_attempts(db, bo_de_id):
            raise ConflictError("Đề đã có người làm, không xóa được")
        if exam["phien_ban"] == 1 and count_versions(db, exam["ma_goc_id"]) > 1:
            raise ConflictError("Không xóa được phiên bản gốc khi đã có phiên bản sau")
        delete_exam_row(db, bo_de_id)
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_exam_detail(db: Session, bo_de_id: int) -> dict | None:
    exam = find_exam(db, bo_de_id)
    if exam is None:
        return None
    exam["ma_de"] = root_code(db, exam["ma_goc_id"])
    exam["phien_ban_moi_nhat"] = latest_exam_version(db, exam["ma_goc_id"])
    exam["co_luot_lam"] = has_attempts(db, bo_de_id)
    items = list_items(db, bo_de_id)

    rows, parents = {}, {}
    for item in items:
        row = find_question(db, item["cau_hoi_id"])
        rows[row["id"]] = row
        if row["cau_cha_id"] and row["cau_cha_id"] not in parents:
            parents[row["cau_cha_id"]] = find_question(db, row["cau_cha_id"])
    options = list_options(db, list(rows) + list(parents))

    shaped = []
    for item in items:
        row = rows[item["cau_hoi_id"]]
        owner = parents.get(row["cau_cha_id"]) or row
        shaped.append({
            **item,
            "la_cau_vi_du": bool(item["la_cau_vi_du"]),
            "ky_nang": owner["ky_nang"],
            "trang_thai_cau": row["trang_thai"],
            "dung_thi_thu": bool(owner["dung_thi_thu"]),
            "cau_hoi": _shape(row, options),
            "cau_cha_id": row["cau_cha_id"],
        })
    exam["cau_hoi"] = shaped
    exam["ngu_lieu"] = {pid: _shape(p, options) for pid, p in parents.items()}
    return exam
