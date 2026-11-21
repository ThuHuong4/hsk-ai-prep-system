"""Đọc/ghi dòng cau_hoi và phuong_an (mỗi dòng cau_hoi là một phiên bản)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.root_id import next_root_id

ROW_FIELDS = (
    "dang", "cap_do_id", "ky_nang", "dung_on_luyen", "dung_thi_thu", "dung_dau_vao",
    "noi_dung", "tep_audio", "tep_hinh", "mo_ta_hinh", "loi_nghe", "pinyin", "dich_nghia",
    "goi_y", "giai_thich", "dap_an_thu_tu", "tu_bat_buoc", "tieu_chi_mo_ta", "diem_toi_da", "nguong_dat",
    "tu_vung_id",
)
SELECT_FIELDS = (
    "id, ma_goc_id, phien_ban, cau_cha_id, trang_thai, nguoi_tao_id, tao_luc, " + ", ".join(ROW_FIELDS)
)


def find_question(db: Session, cau_hoi_id: int, for_update: bool = False) -> dict | None:
    lock = " FOR UPDATE" if for_update else ""
    row = db.execute(
        text(f"SELECT {SELECT_FIELDS} FROM cau_hoi WHERE id = :id{lock}"), {"id": cau_hoi_id}
    ).mappings().first()
    return dict(row) if row else None


def list_children(db: Session, parent_id: int, for_update: bool = False) -> list[dict]:
    lock = " FOR UPDATE" if for_update else ""
    rows = db.execute(
        text(f"SELECT {SELECT_FIELDS} FROM cau_hoi WHERE cau_cha_id = :id ORDER BY id{lock}"),
        {"id": parent_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def latest_version(db: Session, ma_goc_id: int) -> int:
    return int(db.execute(
        text("SELECT MAX(phien_ban) FROM cau_hoi WHERE ma_goc_id = :g"), {"g": ma_goc_id}
    ).scalar_one())


def list_options(db: Session, cau_hoi_ids: list[int]) -> dict[int, dict]:
    """{cau_hoi_id: {"phuong_an": [...], "dap_an_chap_nhan": [...]}}"""
    result = {i: {"phuong_an": [], "dap_an_chap_nhan": []} for i in cau_hoi_ids}
    if not cau_hoi_ids:
        return result
    params = {f"i{n}": v for n, v in enumerate(cau_hoi_ids)}
    marks = ", ".join(f":{k}" for k in params)
    rows = db.execute(
        text(f"""
            SELECT id, cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung, tep_hinh
            FROM phuong_an WHERE cau_hoi_id IN ({marks})
            ORDER BY cau_hoi_id, vai_tro, thu_tu
        """),
        params,
    ).mappings().all()
    for r in rows:
        bucket = result[r["cau_hoi_id"]]
        if r["vai_tro"] == "lua_chon":
            bucket["phuong_an"].append({
                "id": r["id"], "thu_tu": r["thu_tu"], "noi_dung": r["noi_dung"],
                "tep_hinh": r["tep_hinh"], "la_dap_an_dung": bool(r["la_dap_an_dung"]),
            })
        else:
            bucket["dap_an_chap_nhan"].append(r["noi_dung"])
    return result


def insert_question(db: Session, values: dict, ma_goc_id: int | None, phien_ban: int,
                    cau_cha_id: int | None, nguoi_tao_id: int) -> int:
    """ma_goc_id None = câu mới: dòng gốc tự trỏ (ma_goc_id = id)."""
    params = {f: values.get(f) for f in ROW_FIELDS}
    params.update({"phien_ban": phien_ban, "cau_cha_id": cau_cha_id, "nguoi_tao_id": nguoi_tao_id})
    columns = ", ".join(ROW_FIELDS)
    marks = ", ".join(f":{f}" for f in ROW_FIELDS)
    if ma_goc_id is None:
        new_id = next_root_id(db, "cau_hoi")
        params.update({"id": new_id, "ma_goc_id": new_id})
        db.execute(
            text(f"""
                INSERT INTO cau_hoi (id, ma_goc_id, phien_ban, cau_cha_id, trang_thai, nguoi_tao_id, {columns})
                VALUES (:id, :ma_goc_id, :phien_ban, :cau_cha_id, 'nhap', :nguoi_tao_id, {marks})
            """),
            params,
        )
        return new_id
    params["ma_goc_id"] = ma_goc_id
    result = db.execute(
        text(f"""
            INSERT INTO cau_hoi (ma_goc_id, phien_ban, cau_cha_id, trang_thai, nguoi_tao_id, {columns})
            VALUES (:ma_goc_id, :phien_ban, :cau_cha_id, 'nhap', :nguoi_tao_id, {marks})
        """),
        params,
    )
    return int(result.lastrowid)


def update_question(db: Session, cau_hoi_id: int, values: dict) -> None:
    params = {f: values.get(f) for f in ROW_FIELDS}
    params["id"] = cau_hoi_id
    sets = ", ".join(f"{f} = :{f}" for f in ROW_FIELDS)
    db.execute(text(f"UPDATE cau_hoi SET {sets} WHERE id = :id AND trang_thai = 'nhap'"), params)


def replace_options(db: Session, cau_hoi_id: int, options: list, accepted: list[str]) -> None:
    db.execute(text("DELETE FROM phuong_an WHERE cau_hoi_id = :id"), {"id": cau_hoi_id})
    for index, option in enumerate(options, start=1):
        db.execute(
            text("""
                INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung, tep_hinh)
                VALUES (:id, 'lua_chon', :thu_tu, :dung, :noi_dung, :tep_hinh)
            """),
            {"id": cau_hoi_id, "thu_tu": index, "dung": bool(option.la_dap_an_dung),
             "noi_dung": option.noi_dung, "tep_hinh": option.tep_hinh},
        )
    for index, answer in enumerate(accepted, start=1):
        db.execute(
            text("""
                INSERT INTO phuong_an (cau_hoi_id, vai_tro, thu_tu, la_dap_an_dung, noi_dung)
                VALUES (:id, 'dap_an_chap_nhan', :thu_tu, 0, :noi_dung)
            """),
            {"id": cau_hoi_id, "thu_tu": index, "noi_dung": answer},
        )


def delete_question_row(db: Session, cau_hoi_id: int) -> None:
    db.execute(text("DELETE FROM phuong_an WHERE cau_hoi_id = :id"), {"id": cau_hoi_id})
    db.execute(text("DELETE FROM cau_hoi WHERE id = :id"), {"id": cau_hoi_id})


def set_status(db: Session, ids: list[int], trang_thai: str) -> None:
    for cau_hoi_id in ids:
        db.execute(text("UPDATE cau_hoi SET trang_thai = :s WHERE id = :id"), {"s": trang_thai, "id": cau_hoi_id})


def published_versions(db: Session, ma_goc_id: int) -> list[int]:
    rows = db.execute(
        text("SELECT id FROM cau_hoi WHERE ma_goc_id = :g AND trang_thai = 'da_dang'"), {"g": ma_goc_id}
    ).scalars().all()
    return [int(r) for r in rows]


def is_answered(db: Session, ids: list[int]) -> bool:
    if not ids:
        return False
    params = {f"i{n}": v for n, v in enumerate(ids)}
    marks = ", ".join(f":{k}" for k in params)
    return db.execute(
        text(f"SELECT EXISTS(SELECT 1 FROM cau_tra_loi WHERE cau_hoi_id IN ({marks}))"), params
    ).scalar_one() == 1


def exams_using(db: Session, ids: list[int]) -> list[dict]:
    if not ids:
        return []
    params = {f"i{n}": v for n, v in enumerate(ids)}
    marks = ", ".join(f":{k}" for k in params)
    rows = db.execute(
        text(f"""
            SELECT DISTINCT b.id, b.ten, b.phien_ban, b.trang_thai
            FROM bo_de_cau_hoi x JOIN bo_de b ON b.id = x.bo_de_id
            WHERE x.cau_hoi_id IN ({marks})
            ORDER BY b.id
        """),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]
