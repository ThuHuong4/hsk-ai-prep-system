"""Lộ trình Ôn luyện do Giảng viên soạn: thửa (bo_de.loai='thua') theo cấp + kỹ năng,
mỗi thửa có bài 1–4 (loai='bai') và kiểm tra cuối thửa (loai='cuoi_thua', vị trí 5).

- Bài trỏ thua_id tới dòng gốc của thửa (ổn định qua các phiên bản thửa).
- Phiên bản: nháp sửa trực tiếp; bản đã đăng muốn sửa thì tạo bản nháp mới; đăng bản mới thì bản đang dùng cũ chuyển đã ẩn.
- Thứ tự thửa (vi_tri) chỉ là sắp xếp hiển thị nên đổi trực tiếp, không tạo phiên bản.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.root_id import next_root_id
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.exam_authoring.repositories.exam_rows import (
    delete_exam_row,
    has_attempts,
    list_items,
    replace_items,
    set_exam_status,
)
from app.modules.questions.repositories.question_rows import find_question, list_options
from app.modules.questions.services.get_question import _shape

LESSON_MIN = {"bai": 5, "cuoi_thua": 10}
_FIELDS = "id, ma_goc_id, phien_ban, loai, thua_id, cap_do_id, ky_nang, ten, muc_tieu, vi_tri, tai_lieu_id, trang_thai, tao_luc"


def find_set(db: Session, bo_de_id: int, kinds: tuple[str, ...], for_update: bool = False) -> dict:
    lock = " FOR UPDATE" if for_update else ""
    marks = ", ".join(f"'{k}'" for k in kinds)
    row = db.execute(text(f"SELECT {_FIELDS} FROM bo_de WHERE id = :id AND loai IN ({marks}){lock}"), {"id": bo_de_id}).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def _latest(db: Session, ma_goc_id: int) -> int:
    return int(db.execute(text("SELECT MAX(phien_ban) FROM bo_de WHERE ma_goc_id = :g"), {"g": ma_goc_id}).scalar_one())


def _insert(db: Session, v: dict, ma_goc_id: int | None, phien_ban: int, uid: int) -> int:
    params = {k: v.get(k) for k in ("loai", "thua_id", "cap_do_id", "ky_nang", "ten", "muc_tieu", "vi_tri", "tai_lieu_id")}
    params.update({"phien_ban": phien_ban, "uid": uid})
    if ma_goc_id is None:
        new_id = next_root_id(db, "bo_de")
        params.update({"id": new_id, "ma_goc_id": new_id})
        cols, vals = "id, ", ":id, "
    else:
        params["ma_goc_id"] = ma_goc_id
        cols, vals = "", ""
    result = db.execute(
        text(f"""
            INSERT INTO bo_de ({cols}ma_goc_id, phien_ban, loai, thua_id, cap_do_id, ky_nang, ten, muc_tieu,
                               vi_tri, tai_lieu_id, trang_thai, nguoi_tao_id)
            VALUES ({vals}:ma_goc_id, :phien_ban, :loai, :thua_id, :cap_do_id, :ky_nang, :ten, :muc_tieu,
                    :vi_tri, :tai_lieu_id, 'nhap', :uid)
        """),
        params,
    )
    return params.get("id") or int(result.lastrowid)


def _publish(db: Session, row: dict) -> None:
    db.execute(text("UPDATE bo_de SET trang_thai = 'da_an' WHERE ma_goc_id = :g AND trang_thai = 'da_dang'"), {"g": row["ma_goc_id"]})
    set_exam_status(db, row["id"], "da_dang")


def _status_change(db: Session, row: dict, action: str) -> None:
    if action == "an":
        if row["trang_thai"] != "da_dang":
            raise ConflictError("Chỉ ẩn được mục đang đăng")
        set_exam_status(db, row["id"], "da_an")
    elif action == "hien":
        if row["trang_thai"] != "da_an":
            raise ConflictError("Chỉ hiện lại được mục đã ẩn")
        if row["phien_ban"] != _latest(db, row["ma_goc_id"]):
            raise ConflictError("Chỉ hiện lại được phiên bản mới nhất")
        set_exam_status(db, row["id"], "da_dang")


# ---------------- Bản đồ lộ trình ----------------

def get_path(db: Session, cap_do_id: int, ky_nang: str) -> dict:
    lands = db.execute(
        text("""
            SELECT b.id, b.ma_goc_id, b.phien_ban, b.ten, b.muc_tieu, b.vi_tri, b.trang_thai,
                   EXISTS(SELECT 1 FROM bo_de p WHERE p.ma_goc_id = b.ma_goc_id AND p.trang_thai = 'da_dang') AS co_ban_dang_dung
            FROM bo_de b
            WHERE b.loai = 'thua' AND b.cap_do_id = :cap AND b.ky_nang = :ky
              AND b.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id)
            ORDER BY b.vi_tri IS NULL, b.vi_tri, b.id
        """),
        {"cap": cap_do_id, "ky": ky_nang},
    ).mappings().all()
    result = []
    for land in lands:
        lessons = db.execute(
            text("""
                SELECT b.id, b.ma_goc_id, b.phien_ban, b.loai, b.vi_tri, b.ten, b.trang_thai, b.tai_lieu_id,
                       t.ten AS ten_tai_lieu,
                       (SELECT COUNT(*) FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id AND i.la_cau_vi_du = 0) AS so_cau,
                       EXISTS(SELECT 1 FROM bo_de p WHERE p.ma_goc_id = b.ma_goc_id AND p.trang_thai = 'da_dang') AS co_ban_dang_dung
                FROM bo_de b LEFT JOIN tai_lieu t ON t.id = b.tai_lieu_id
                WHERE b.thua_id = :thua AND b.loai IN ('bai', 'cuoi_thua')
                  AND b.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id)
                ORDER BY b.vi_tri
            """),
            {"thua": land["ma_goc_id"]},
        ).mappings().all()
        result.append({
            **dict(land),
            "co_ban_dang_dung": bool(land["co_ban_dang_dung"]),
            "bai": [{**dict(x), "co_ban_dang_dung": bool(x["co_ban_dang_dung"]), "can_toi_thieu": LESSON_MIN[x["loai"]]} for x in lessons],
        })
    return {"cap_do_id": cap_do_id, "ky_nang": ky_nang, "thua": result}


# ---------------- Thửa ----------------

def create_land(db: Session, body, uid: int) -> int:
    try:
        if not db.execute(text("SELECT EXISTS(SELECT 1 FROM cap_do WHERE id = :id)"), {"id": body.cap_do_id}).scalar_one():
            raise RuleError("Cấp độ không tồn tại")
        next_pos = db.execute(
            text("""SELECT COALESCE(MAX(vi_tri), 0) + 1 FROM bo_de
                    WHERE loai = 'thua' AND cap_do_id = :cap AND ky_nang = :ky FOR UPDATE"""),
            {"cap": body.cap_do_id, "ky": body.ky_nang},
        ).scalar_one()
        new_id = _insert(db, {"loai": "thua", "cap_do_id": body.cap_do_id, "ky_nang": body.ky_nang,
                              "ten": body.ten, "muc_tieu": body.muc_tieu, "vi_tri": int(next_pos)}, None, 1, uid)
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_land(db: Session, bo_de_id: int, body, uid: int) -> int:
    try:
        row = find_set(db, bo_de_id, ("thua",), for_update=True)
        if row["phien_ban"] != _latest(db, row["ma_goc_id"]):
            raise ConflictError("Đây không phải phiên bản mới nhất")
        if row["trang_thai"] == "nhap":
            db.execute(text("UPDATE bo_de SET ten = :ten, muc_tieu = :mt WHERE id = :id"),
                       {"ten": body.ten, "mt": body.muc_tieu, "id": row["id"]})
            result = row["id"]
        else:
            result = _insert(db, {**row, "ten": body.ten, "muc_tieu": body.muc_tieu}, row["ma_goc_id"], row["phien_ban"] + 1, uid)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def move_land(db: Session, bo_de_id: int, direction: str) -> None:
    """Đổi chỗ với thửa liền kề (cùng cấp, kỹ năng); đổi vi_tri trên mọi phiên bản của hai thửa."""
    try:
        row = find_set(db, bo_de_id, ("thua",), for_update=True)
        op, order = ("<", "DESC") if direction == "len" else (">", "ASC")
        neighbour = db.execute(
            text(f"""
                SELECT b.ma_goc_id, b.vi_tri FROM bo_de b
                WHERE b.loai = 'thua' AND b.cap_do_id = :cap AND b.ky_nang = :ky AND b.ma_goc_id <> :g
                  AND b.vi_tri {op} :pos
                  AND b.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id)
                ORDER BY b.vi_tri {order} LIMIT 1 FOR UPDATE
            """),
            {"cap": row["cap_do_id"], "ky": row["ky_nang"], "g": row["ma_goc_id"], "pos": row["vi_tri"] or 0},
        ).mappings().first()
        if neighbour is None:
            raise ConflictError("Thửa đã ở đầu/cuối danh sách")
        db.execute(text("UPDATE bo_de SET vi_tri = :p WHERE ma_goc_id = :g"), {"p": neighbour["vi_tri"], "g": row["ma_goc_id"]})
        db.execute(text("UPDATE bo_de SET vi_tri = :p WHERE ma_goc_id = :g"), {"p": row["vi_tri"], "g": neighbour["ma_goc_id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise


def land_status(db: Session, bo_de_id: int, action: str) -> None:
    try:
        row = find_set(db, bo_de_id, ("thua",), for_update=True)
        if action == "dang":
            if row["trang_thai"] != "nhap":
                raise ConflictError("Chỉ đăng được bản nháp")
            _publish(db, row)
        else:
            _status_change(db, row, action)
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_land(db: Session, bo_de_id: int) -> None:
    try:
        row = find_set(db, bo_de_id, ("thua",), for_update=True)
        if row["trang_thai"] != "nhap":
            raise ConflictError("Chỉ xóa được thửa nháp; thửa đã đăng thì dùng Ẩn")
        if row["phien_ban"] == 1:
            if db.execute(text("SELECT EXISTS(SELECT 1 FROM bo_de WHERE thua_id = :g)"), {"g": row["ma_goc_id"]}).scalar_one():
                raise ConflictError("Thửa còn bài, xóa các bài trước")
            if db.execute(text("SELECT EXISTS(SELECT 1 FROM luot_lam WHERE thua_dich_id = :g)"), {"g": row["ma_goc_id"]}).scalar_one():
                raise ConflictError("Thửa đã có lượt làm, không xóa được")
            if db.execute(text("SELECT COUNT(*) FROM bo_de WHERE ma_goc_id = :g"), {"g": row["ma_goc_id"]}).scalar_one() > 1:
                raise ConflictError("Không xóa được phiên bản gốc khi đã có phiên bản sau")
        delete_exam_row(db, row["id"])
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------- Bài và kiểm tra cuối thửa ----------------

def _check_material(db: Session, tai_lieu_id: int | None) -> None:
    if tai_lieu_id and not db.execute(text("SELECT EXISTS(SELECT 1 FROM tai_lieu WHERE id = :id)"), {"id": tai_lieu_id}).scalar_one():
        raise RuleError("Tài liệu không tồn tại")


def _slot_taken(db: Session, thua_goc: int, vi_tri: int, except_goc: int | None = None) -> bool:
    return bool(db.execute(
        text("""SELECT 1 FROM bo_de WHERE thua_id = :t AND vi_tri = :v AND ma_goc_id <> COALESCE(:g, 0)
                AND loai IN ('bai', 'cuoi_thua') LIMIT 1"""),
        {"t": thua_goc, "v": vi_tri, "g": except_goc},
    ).first())


def create_lesson(db: Session, body, uid: int) -> int:
    try:
        land = find_set(db, body.thua_id, ("thua",), for_update=True)
        thua_goc = land["ma_goc_id"]
        loai = "cuoi_thua" if body.vi_tri == 5 else "bai"
        if _slot_taken(db, thua_goc, body.vi_tri):
            raise ConflictError("Vị trí này trong thửa đã có bài")
        _check_material(db, body.tai_lieu_id)
        new_id = _insert(db, {"loai": loai, "thua_id": thua_goc, "ten": body.ten, "muc_tieu": body.muc_tieu,
                              "vi_tri": body.vi_tri, "tai_lieu_id": body.tai_lieu_id}, None, 1, uid)
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def _load_draft_lesson(db: Session, bo_de_id: int) -> dict:
    row = find_set(db, bo_de_id, ("bai", "cuoi_thua"), for_update=True)
    if row["trang_thai"] != "nhap":
        raise ConflictError("Bài đã đăng. Bấm “Tạo bản nháp để sửa” trước khi chỉnh.")
    return row


def update_lesson(db: Session, bo_de_id: int, body) -> None:
    try:
        row = _load_draft_lesson(db, bo_de_id)
        _check_material(db, body.tai_lieu_id)
        db.execute(text("UPDATE bo_de SET ten = :ten, muc_tieu = :mt, tai_lieu_id = :tl WHERE id = :id"),
                   {"ten": body.ten, "mt": body.muc_tieu, "tl": body.tai_lieu_id, "id": row["id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise


def _land_of(db: Session, lesson: dict) -> dict:
    land = db.execute(
        text(f"SELECT {_FIELDS} FROM bo_de WHERE ma_goc_id = :g ORDER BY phien_ban DESC LIMIT 1"),
        {"g": lesson["thua_id"]},
    ).mappings().first()
    return dict(land)


def _scope(db: Session, cau_hoi_id: int) -> tuple[dict, dict]:
    row = find_question(db, cau_hoi_id)
    if row is None:
        raise RuleError(f"Câu hỏi #{cau_hoi_id} không tồn tại")
    if row["dang"] == "ngu_lieu":
        raise RuleError(f"Câu #{cau_hoi_id} là ngữ liệu: hãy thêm các câu con của nó")
    owner = find_question(db, row["cau_cha_id"]) if row["cau_cha_id"] else row
    return row, owner


def set_lesson_items(db: Session, bo_de_id: int, items) -> None:
    try:
        lesson = _load_draft_lesson(db, bo_de_id)
        land = _land_of(db, lesson)
        seen, prepared = set(), []
        for item in items:
            if item.cau_hoi_id in seen:
                raise RuleError(f"Câu #{item.cau_hoi_id} bị thêm 2 lần")
            seen.add(item.cau_hoi_id)
            row, owner = _scope(db, item.cau_hoi_id)
            if owner["cap_do_id"] != land["cap_do_id"] or owner["ky_nang"] != land["ky_nang"]:
                raise RuleError(f"Câu #{item.cau_hoi_id} không cùng cấp và kỹ năng với thửa")
            if lesson["loai"] == "cuoi_thua" and row["dang"] == "viet_mo":
                raise RuleError("Kiểm tra cuối thửa chỉ dùng câu có đáp án xác định (không dùng Viết mở)")
            prepared.append({"cau_hoi_id": item.cau_hoi_id, "phan": None, "la_cau_vi_du": False})
        replace_items(db, bo_de_id, prepared)
        db.commit()
    except Exception:
        db.rollback()
        raise


def lesson_draft(db: Session, bo_de_id: int, uid: int) -> int:
    try:
        row = find_set(db, bo_de_id, ("bai", "cuoi_thua"), for_update=True)
        if row["trang_thai"] == "nhap":
            return row["id"]
        if row["phien_ban"] != _latest(db, row["ma_goc_id"]):
            raise ConflictError("Đã có phiên bản mới hơn của bài này")
        new_id = _insert(db, row, row["ma_goc_id"], row["phien_ban"] + 1, uid)
        replace_items(db, new_id, list_items(db, row["id"]))
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def lesson_status(db: Session, bo_de_id: int, action: str) -> None:
    try:
        row = find_set(db, bo_de_id, ("bai", "cuoi_thua"), for_update=True)
        if action == "dang":
            if row["trang_thai"] != "nhap":
                raise ConflictError("Chỉ đăng được bản nháp")
            land = _land_of(db, row)
            items = list_items(db, row["id"])
            need = LESSON_MIN[row["loai"]]
            if len(items) < need:
                raise RuleError(f"{'Kiểm tra cuối thửa' if row['loai'] == 'cuoi_thua' else 'Bài'} cần ít nhất {need} câu")
            for item in items:
                q, owner = _scope(db, item["cau_hoi_id"])
                if q["trang_thai"] != "da_dang" or owner["trang_thai"] != "da_dang":
                    raise RuleError(f"Câu #{owner['ma_goc_id']} chưa đăng hoặc đã ẩn")
                if not owner["dung_on_luyen"]:
                    raise RuleError(f"Câu #{owner['ma_goc_id']} chưa bật “Dùng cho Ôn luyện”")
                if owner["cap_do_id"] != land["cap_do_id"] or owner["ky_nang"] != land["ky_nang"]:
                    raise RuleError(f"Câu #{owner['ma_goc_id']} không cùng cấp và kỹ năng với thửa")
            if row["tai_lieu_id"]:
                ok = db.execute(
                    text("""SELECT EXISTS(SELECT 1 FROM tai_lieu t JOIN tai_lieu v ON v.ma_goc_id = t.ma_goc_id
                            WHERE t.id = :id AND v.trang_thai = 'da_dang')"""),
                    {"id": row["tai_lieu_id"]},
                ).scalar_one()
                if not ok:
                    raise RuleError("Tài liệu gắn với bài chưa được đăng")
            _publish(db, row)
        else:
            _status_change(db, row, action)
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_lesson(db: Session, bo_de_id: int) -> None:
    try:
        row = _load_draft_lesson(db, bo_de_id)
        if has_attempts(db, row["id"]):
            raise ConflictError("Bài đã có người làm, không xóa được")
        if row["phien_ban"] == 1 and db.execute(text("SELECT COUNT(*) FROM bo_de WHERE ma_goc_id = :g"), {"g": row["ma_goc_id"]}).scalar_one() > 1:
            raise ConflictError("Không xóa được phiên bản gốc khi đã có phiên bản sau")
        delete_exam_row(db, row["id"])
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_lesson_detail(db: Session, bo_de_id: int) -> dict:
    row = find_set(db, bo_de_id, ("bai", "cuoi_thua"))
    land = _land_of(db, row)
    row["thua"] = {k: land[k] for k in ("id", "ma_goc_id", "ten", "cap_do_id", "ky_nang", "trang_thai")}
    row["phien_ban_moi_nhat"] = _latest(db, row["ma_goc_id"])
    row["can_toi_thieu"] = LESSON_MIN[row["loai"]]
    row["tai_lieu"] = None
    if row["tai_lieu_id"]:
        doc = db.execute(text("SELECT id, ten, trang_thai FROM tai_lieu WHERE id = :id"), {"id": row["tai_lieu_id"]}).mappings().first()
        row["tai_lieu"] = dict(doc) if doc else None
    items = list_items(db, bo_de_id)
    rows, parents = {}, {}
    for item in items:
        q = find_question(db, item["cau_hoi_id"])
        rows[q["id"]] = q
        if q["cau_cha_id"] and q["cau_cha_id"] not in parents:
            parents[q["cau_cha_id"]] = find_question(db, q["cau_cha_id"])
    options = list_options(db, list(rows) + list(parents))
    row["cau_hoi"] = [{
        "cau_hoi_id": i["cau_hoi_id"], "thu_tu": i["thu_tu"], "cau_cha_id": rows[i["cau_hoi_id"]]["cau_cha_id"],
        "ky_nang": (parents.get(rows[i["cau_hoi_id"]]["cau_cha_id"]) or rows[i["cau_hoi_id"]])["ky_nang"],
        "cau_hoi": _shape(rows[i["cau_hoi_id"]], options),
    } for i in items]
    row["ngu_lieu"] = {pid: _shape(p, options) for pid, p in parents.items()}
    return row
