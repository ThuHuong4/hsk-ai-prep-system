from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.questions.repositories.question_rows import (
    exams_using,
    find_question,
    latest_version,
    list_children,
    list_options,
)

_PUBLIC = (
    "id", "ma_goc_id", "phien_ban", "dang", "trang_thai", "noi_dung", "tep_audio", "tep_hinh",
    "mo_ta_hinh", "loi_nghe", "pinyin", "dich_nghia", "goi_y", "goi_y_2", "giai_thich", "dap_an_thu_tu",
    "tu_bat_buoc", "tieu_chi_mo_ta", "diem_toi_da", "nguong_dat",
)


def _shape(row: dict, options: dict) -> dict:
    item = {k: row[k] for k in _PUBLIC}
    for key in ("diem_toi_da", "nguong_dat"):
        if item[key] is not None:
            item[key] = float(item[key])
    item.update(options[row["id"]])
    return item


def _word(db: Session, tu_vung_id: int | None) -> dict | None:
    if not tu_vung_id:
        return None
    row = db.execute(text("SELECT id, chu_han, pinyin, nghia, trang_thai FROM tu_vung WHERE id = :id"), {"id": tu_vung_id}).mappings().first()
    return dict(row) if row else None


def get_question_detail(db: Session, cau_hoi_id: int) -> dict | None:
    row = find_question(db, cau_hoi_id)
    if row is None or row["cau_cha_id"] is not None:
        return None
    children = list_children(db, row["id"])
    options = list_options(db, [row["id"]] + [c["id"] for c in children])

    item = _shape(row, options)
    item.update({
        "cap_do_id": row["cap_do_id"],
        "ky_nang": row["ky_nang"],
        "dung_on_luyen": bool(row["dung_on_luyen"]),
        "dung_thi_thu": bool(row["dung_thi_thu"]),
        "dung_dau_vao": bool(row["dung_dau_vao"]),
        "tu_vung_id": row["tu_vung_id"],
        "tu_vung": _word(db, row["tu_vung_id"]),
        "nguon_noi_dung": row["nguon_noi_dung"],
        "nhom_kien_thuc_id": row["nhom_kien_thuc_id"],
        "tao_luc": row["tao_luc"],
        "cau_con": [_shape(c, options) for c in children],
        "phien_ban_moi_nhat": latest_version(db, row["ma_goc_id"]),
        "de_dang_dung": exams_using(db, [row["id"]] + [c["id"] for c in children]),
    })
    versions = db.execute(
        text("SELECT id, phien_ban, trang_thai, tao_luc FROM cau_hoi WHERE ma_goc_id = :g ORDER BY phien_ban DESC"),
        {"g": row["ma_goc_id"]},
    ).mappings().all()
    item["cac_phien_ban"] = [dict(v) for v in versions]
    return item
