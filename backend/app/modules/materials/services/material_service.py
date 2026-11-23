"""Tài liệu ôn tập (bảng tai_lieu, mỗi dòng một phiên bản).

Nháp sửa trực tiếp; bản đã đăng/ẩn sửa thì tạo phiên bản nháp mới (tệp mới hoặc bản sao tệp cũ,
không ghi đè tệp cũ). Đăng bản mới thì bản đang dùng cũ chuyển đã ẩn.
"""
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.root_id import next_root_id
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.storage.private_files import copy_document, delete_file, resolve

_FIELDS = "id, ma_goc_id, phien_ban, ten, mo_ta, nguon, cap_do_id, ky_nang, loai_tep, duong_dan, kich_thuoc, trang_thai, nguoi_tao_id, tao_luc"
EXT_TO_TYPE = {"pdf": "pdf", "png": "png", "jpg": "jpg", "jpeg": "jpg", "mp3": "mp3", "wav": "wav"}
MAX_SIZE = 20 * 1024 * 1024
MAX_EXTERNAL = 3

# Nguồn học thêm bên ngoài (miễn phí xem, chỉ dẫn liên kết tới đơn vị gốc, không sao chép nội dung)
EXTERNAL = [
    {
        "ten": "Mandarin Corner (YouTube)",
        "mo_ta": "Hội thoại thật có phụ đề Trung–Anh; có khóa từ vựng HSK 1 và HSK 2 theo chủ đề.",
        "url": "https://www.youtube.com/channel/UC2fAiRQHRQT9aj9P_ijYeow/playlists",
        "cap": {"HSK1", "HSK2", "HSK3", "HSK4"},
        "ky_nang": {"nghe", "tu_vung"},
    },
    {
        "ten": "Chinese Zero to Hero (YouTube)",
        "mo_ta": "Bài giảng theo từng cấp HSK 1–6: từ vựng, ngữ pháp, đọc hiểu (giảng bằng tiếng Anh).",
        "url": "https://www.youtube.com/@ChineseZeroToHero",
        "cap": {"HSK1", "HSK2", "HSK3", "HSK4"},
        "ky_nang": {"doc", "nghe", "viet", "tu_vung"},
    },
    {
        "ten": "Chinese for HSK 1 – Đại học Bắc Kinh (Coursera)",
        "mo_ta": "Khóa học trực tuyến của Đại học Bắc Kinh bám theo HSK 1.",
        "url": "https://www.coursera.org/learn/hsk-1",
        "cap": {"HSK1"},
        "ky_nang": {"nghe", "doc", "tu_vung"},
    },
    {
        "ten": "Chinese for HSK 2 – Đại học Bắc Kinh (Coursera)",
        "mo_ta": "Khóa học trực tuyến của Đại học Bắc Kinh bám theo HSK 2.",
        "url": "https://www.coursera.org/learn/hsk-2",
        "cap": {"HSK2"},
        "ky_nang": {"nghe", "doc", "tu_vung"},
    },
    {
        "ten": "Trang chính thức kỳ thi HSK (汉考国际)",
        "mo_ta": "Thông tin kỳ thi và đề mẫu chính thức để luyện thêm.",
        "url": "https://www.chinesetest.cn",
        "cap": {"HSK1", "HSK2", "HSK3", "HSK4"},
        "ky_nang": {"nghe", "doc", "viet"},
    },
]


def external_for(cap_ma: str, skill: str) -> list[dict]:
    """Lọc tối đa 3 nguồn học ngoài phù hợp với mã cấp HSK và kỹ năng."""
    return [
        {"ten": x["ten"], "mo_ta": x["mo_ta"], "url": x["url"]}
        for x in EXTERNAL
        if cap_ma in x["cap"] and skill in x["ky_nang"]
    ][:MAX_EXTERNAL]


def published_material_file(db: Session, tai_lieu_id: int) -> dict:
    """Lấy thông tin tệp tài liệu đang đăng để Học viên mở xem an toàn."""
    row = db.execute(
        text("SELECT id, duong_dan, loai_tep, ten FROM tai_lieu WHERE id = :id AND trang_thai = 'da_dang'"),
        {"id": tai_lieu_id},
    ).mappings().first()
    db.rollback()
    if row is None:
        raise NotFoundError()
    return dict(row)


def find_material(db: Session, tai_lieu_id: int, for_update: bool = False) -> dict | None:
    lock = " FOR UPDATE" if for_update else ""
    row = db.execute(text(f"SELECT {_FIELDS} FROM tai_lieu WHERE id = :id{lock}"), {"id": tai_lieu_id}).mappings().first()
    return dict(row) if row else None


def _latest(db: Session, ma_goc_id: int) -> int:
    return int(db.execute(text("SELECT MAX(phien_ban) FROM tai_lieu WHERE ma_goc_id = :g"), {"g": ma_goc_id}).scalar_one())


def usage(db: Session, ma_goc_id: int) -> dict:
    """Số bài/đề và gợi ý lộ trình đang trỏ tới bất kỳ phiên bản nào của tài liệu."""
    row = db.execute(
        text("""
            SELECT (SELECT COUNT(*) FROM bo_de b JOIN tai_lieu t ON t.id = b.tai_lieu_id WHERE t.ma_goc_id = :g) AS so_bai,
                   (SELECT COUNT(*) FROM goi_y_lo_trinh x JOIN tai_lieu t ON t.id = x.tai_lieu_id WHERE t.ma_goc_id = :g) AS so_goi_y
        """),
        {"g": ma_goc_id},
    ).mappings().one()
    return {"so_bai": int(row["so_bai"]), "so_goi_y": int(row["so_goi_y"])}


def _check_file(relative: str) -> tuple[str, int]:
    try:
        path = resolve(relative)
    except ValueError:
        raise RuleError("Tệp không hợp lệ")
    if not path.is_file():
        raise RuleError("Không tìm thấy tệp đã tải lên, hãy tải lại")
    ext = Path(relative).suffix.lstrip(".").lower()
    if ext not in EXT_TO_TYPE:
        raise RuleError("Loại tệp không được hỗ trợ")
    size = path.stat().st_size
    if size <= 0 or size > MAX_SIZE:
        raise RuleError("Tệp rỗng hoặc vượt quá 20 MB")
    return EXT_TO_TYPE[ext], size


def _check_level(db: Session, cap_do_id: int | None) -> None:
    if cap_do_id and not db.execute(text("SELECT EXISTS(SELECT 1 FROM cap_do WHERE id = :id)"), {"id": cap_do_id}).scalar_one():
        raise RuleError("Cấp độ không tồn tại")


def _path_in_use(db: Session, relative: str, except_id: int | None = None) -> bool:
    return bool(db.execute(
        text("SELECT 1 FROM tai_lieu WHERE duong_dan = :p AND id <> COALESCE(:id, 0)"),
        {"p": relative, "id": except_id},
    ).first())


def _insert(db: Session, info: dict, ma_goc_id: int | None, phien_ban: int, uid: int) -> int:
    params = {**info, "phien_ban": phien_ban, "uid": uid}
    if ma_goc_id is None:
        new_id = next_root_id(db, "tai_lieu")
        params.update({"id": new_id, "ma_goc_id": new_id})
        id_col, id_val = "id, ", ":id, "
    else:
        params["ma_goc_id"] = ma_goc_id
        id_col, id_val = "", ""
    result = db.execute(
        text(f"""
            INSERT INTO tai_lieu ({id_col}ma_goc_id, phien_ban, ten, mo_ta, nguon, cap_do_id, ky_nang,
                                  loai_tep, duong_dan, kich_thuoc, trang_thai, nguoi_tao_id)
            VALUES ({id_val}:ma_goc_id, :phien_ban, :ten, :mo_ta, :nguon, :cap_do_id, :ky_nang,
                    :loai_tep, :duong_dan, :kich_thuoc, 'nhap', :uid)
        """),
        params,
    )
    return params.get("id") or int(result.lastrowid)


def create_material(db: Session, body, uid: int) -> int:
    try:
        _check_level(db, body.cap_do_id)
        loai, size = _check_file(body.duong_dan)
        if _path_in_use(db, body.duong_dan):
            raise RuleError("Tệp này đã thuộc tài liệu khác, hãy tải tệp mới")
        info = body.model_dump()
        info.update({"loai_tep": loai, "kich_thuoc": size})
        new_id = _insert(db, info, None, 1, uid)
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise


def update_material(db: Session, tai_lieu_id: int, body, uid: int) -> int:
    try:
        _check_level(db, body.cap_do_id)
        row = find_material(db, tai_lieu_id, for_update=True)
        if row is None:
            raise NotFoundError()
        if row["phien_ban"] != _latest(db, row["ma_goc_id"]):
            raise ConflictError("Đây không phải phiên bản mới nhất")
        file_changed = body.duong_dan != row["duong_dan"]
        if file_changed:
            loai, size = _check_file(body.duong_dan)
            if _path_in_use(db, body.duong_dan, row["id"]):
                raise RuleError("Tệp này đã thuộc tài liệu khác, hãy tải tệp mới")
        else:
            loai, size = row["loai_tep"], row["kich_thuoc"]
        info = body.model_dump()
        info.update({"loai_tep": loai, "kich_thuoc": size})

        if row["trang_thai"] == "nhap":
            db.execute(
                text("""
                    UPDATE tai_lieu SET ten = :ten, mo_ta = :mo_ta, nguon = :nguon, cap_do_id = :cap_do_id,
                           ky_nang = :ky_nang, loai_tep = :loai_tep, duong_dan = :duong_dan, kich_thuoc = :kich_thuoc
                    WHERE id = :id
                """),
                {**info, "id": row["id"]},
            )
            result_id = row["id"]
            old_file = row["duong_dan"] if file_changed else None
        else:
            if not file_changed:
                info["duong_dan"] = copy_document(row["duong_dan"])  # Không dùng chung tệp giữa hai phiên bản
            result_id = _insert(db, info, row["ma_goc_id"], row["phien_ban"] + 1, uid)
            old_file = None
        db.commit()
    except Exception:
        db.rollback()
        raise
    if old_file:
        delete_file(old_file)  # Tệp nháp cũ không còn dòng nào trỏ tới
    return result_id


def change_status(db: Session, tai_lieu_id: int, action: str) -> None:
    try:
        row = find_material(db, tai_lieu_id, for_update=True)
        if row is None:
            raise NotFoundError()
        if action == "dang":
            if row["trang_thai"] != "nhap":
                raise ConflictError("Chỉ đăng được bản nháp")
            _check_file(row["duong_dan"])
            db.execute(text("UPDATE tai_lieu SET trang_thai = 'da_an' WHERE ma_goc_id = :g AND trang_thai = 'da_dang'"),
                       {"g": row["ma_goc_id"]})
            new_status = "da_dang"
        elif action == "an":
            if row["trang_thai"] != "da_dang":
                raise ConflictError("Chỉ ẩn được tài liệu đang đăng")
            new_status = "da_an"
        else:
            if row["trang_thai"] != "da_an":
                raise ConflictError("Chỉ hiện lại được tài liệu đã ẩn")
            if row["phien_ban"] != _latest(db, row["ma_goc_id"]):
                raise ConflictError("Chỉ hiện lại được phiên bản mới nhất")
            new_status = "da_dang"
        db.execute(text("UPDATE tai_lieu SET trang_thai = :s WHERE id = :id"), {"s": new_status, "id": row["id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise


def delete_material(db: Session, tai_lieu_id: int) -> None:
    try:
        row = find_material(db, tai_lieu_id, for_update=True)
        if row is None:
            raise NotFoundError()
        if row["trang_thai"] != "nhap":
            raise ConflictError("Chỉ xóa được bản nháp; tài liệu đã đăng thì dùng Ẩn")
        used = db.execute(
            text("""SELECT (SELECT COUNT(*) FROM bo_de WHERE tai_lieu_id = :id)
                         + (SELECT COUNT(*) FROM goi_y_lo_trinh WHERE tai_lieu_id = :id)"""),
            {"id": row["id"]},
        ).scalar_one()
        if used:
            raise ConflictError("Tài liệu đang được dùng, chỉ ẩn được")
        if row["phien_ban"] == 1 and db.execute(text("SELECT COUNT(*) FROM tai_lieu WHERE ma_goc_id = :g"), {"g": row["ma_goc_id"]}).scalar_one() > 1:
            raise ConflictError("Không xóa được phiên bản gốc khi đã có phiên bản sau")
        db.execute(text("DELETE FROM tai_lieu WHERE id = :id"), {"id": row["id"]})
        db.commit()
    except Exception:
        db.rollback()
        raise
    delete_file(row["duong_dan"])


def list_materials(db: Session, filters: dict) -> list[dict]:
    where = ["t.phien_ban = (SELECT MAX(x.phien_ban) FROM tai_lieu x WHERE x.ma_goc_id = t.ma_goc_id)"]
    params: dict = {}
    for key in ("cap_do_id", "ky_nang", "trang_thai"):
        if filters.get(key):
            where.append(f"t.{key} = :{key}")
            params[key] = filters[key]
    if filters.get("q"):
        where.append("(t.ten LIKE :q OR t.mo_ta LIKE :q OR t.nguon LIKE :q)")
        params["q"] = f"%{filters['q']}%"
    rows = db.execute(
        text(f"""
            SELECT t.id, t.ma_goc_id, t.phien_ban, t.ten, t.mo_ta, t.nguon, t.cap_do_id, cd.ten AS ten_cap_do,
                   t.ky_nang, t.loai_tep, t.kich_thuoc, t.trang_thai, t.tao_luc,
                   (SELECT COUNT(*) FROM bo_de b JOIN tai_lieu v ON v.id = b.tai_lieu_id WHERE v.ma_goc_id = t.ma_goc_id) AS so_bai,
                   EXISTS(SELECT 1 FROM tai_lieu p WHERE p.ma_goc_id = t.ma_goc_id AND p.trang_thai = 'da_dang') AS co_ban_dang_dung,
                   (SELECT u.ho_ten FROM tai_lieu g JOIN nguoi_dung u ON u.id = g.nguoi_tao_id WHERE g.id = t.ma_goc_id) AS nguoi_tao,
                   (SELECT u.ho_ten FROM nguoi_dung u WHERE u.id = t.nguoi_tao_id) AS nguoi_sua
            FROM tai_lieu t LEFT JOIN cap_do cd ON cd.id = t.cap_do_id
            WHERE {' AND '.join(where)}
            ORDER BY t.ma_goc_id DESC
        """),
        params,
    ).mappings().all()
    return [{**dict(r), "co_ban_dang_dung": bool(r["co_ban_dang_dung"])} for r in rows]
