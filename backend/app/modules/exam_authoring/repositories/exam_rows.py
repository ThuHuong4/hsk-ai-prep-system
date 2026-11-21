from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.root_id import next_root_id

_FIELDS = "id, ma_goc_id, phien_ban, loai, cap_do_id, ten, ma_de, nguon, thoi_luong_phut, tep_audio_chung, trang_thai, nguoi_tao_id, tao_luc"


def find_exam(db: Session, bo_de_id: int, for_update: bool = False) -> dict | None:
    lock = " FOR UPDATE" if for_update else ""
    row = db.execute(
        text(f"SELECT {_FIELDS} FROM bo_de WHERE id = :id AND loai = 'de_thi'{lock}"), {"id": bo_de_id}
    ).mappings().first()
    return dict(row) if row else None


def root_code(db: Session, ma_goc_id: int) -> str | None:
    return db.execute(text("SELECT ma_de FROM bo_de WHERE id = :g"), {"g": ma_goc_id}).scalar_one_or_none()


def latest_exam_version(db: Session, ma_goc_id: int) -> int:
    return int(db.execute(
        text("SELECT MAX(phien_ban) FROM bo_de WHERE ma_goc_id = :g"), {"g": ma_goc_id}
    ).scalar_one())


def count_versions(db: Session, ma_goc_id: int) -> int:
    return int(db.execute(text("SELECT COUNT(*) FROM bo_de WHERE ma_goc_id = :g"), {"g": ma_goc_id}).scalar_one())


def insert_exam(db: Session, info, ma_goc_id: int | None, phien_ban: int, nguoi_tao_id: int) -> int:
    params = {
        "phien_ban": phien_ban, "cap_do_id": info["cap_do_id"], "ten": info["ten"], "nguon": info.get("nguon"),
        "thoi_luong_phut": info.get("thoi_luong_phut"), "tep_audio_chung": info.get("tep_audio_chung"),
        "nguoi_tao_id": nguoi_tao_id,
    }
    if ma_goc_id is None:
        new_id = next_root_id(db, "bo_de")
        params.update({"id": new_id, "ma_goc_id": new_id, "ma_de": info["ma_de"]})
        db.execute(
            text("""
                INSERT INTO bo_de (id, ma_goc_id, phien_ban, loai, cap_do_id, ten, ma_de, nguon,
                                   thoi_luong_phut, tep_audio_chung, trang_thai, nguoi_tao_id)
                VALUES (:id, :ma_goc_id, :phien_ban, 'de_thi', :cap_do_id, :ten, :ma_de, :nguon,
                        :thoi_luong_phut, :tep_audio_chung, 'nhap', :nguoi_tao_id)
            """),
            params,
        )
        return new_id
    params["ma_goc_id"] = ma_goc_id  # Mã đề chỉ lưu ở dòng gốc
    result = db.execute(
        text("""
            INSERT INTO bo_de (ma_goc_id, phien_ban, loai, cap_do_id, ten, nguon,
                               thoi_luong_phut, tep_audio_chung, trang_thai, nguoi_tao_id)
            VALUES (:ma_goc_id, :phien_ban, 'de_thi', :cap_do_id, :ten, :nguon,
                    :thoi_luong_phut, :tep_audio_chung, 'nhap', :nguoi_tao_id)
        """),
        params,
    )
    return int(result.lastrowid)


def update_exam(db: Session, bo_de_id: int, info: dict) -> None:
    db.execute(
        text("""
            UPDATE bo_de SET cap_do_id = :cap_do_id, ten = :ten, nguon = :nguon,
                   thoi_luong_phut = :thoi_luong_phut, tep_audio_chung = :tep_audio_chung
            WHERE id = :id AND trang_thai = 'nhap'
        """),
        {**{k: info.get(k) for k in ("cap_do_id", "ten", "nguon", "thoi_luong_phut", "tep_audio_chung")}, "id": bo_de_id},
    )


def update_root_code(db: Session, ma_goc_id: int, ma_de: str) -> None:
    db.execute(text("UPDATE bo_de SET ma_de = :m WHERE id = :g"), {"m": ma_de, "g": ma_goc_id})


def list_items(db: Session, bo_de_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT cau_hoi_id, thu_tu, phan, la_cau_vi_du
            FROM bo_de_cau_hoi WHERE bo_de_id = :id ORDER BY thu_tu
        """),
        {"id": bo_de_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def replace_items(db: Session, bo_de_id: int, items: list[dict]) -> None:
    db.execute(text("DELETE FROM bo_de_cau_hoi WHERE bo_de_id = :id"), {"id": bo_de_id})
    for index, item in enumerate(items, start=1):
        db.execute(
            text("""
                INSERT INTO bo_de_cau_hoi (bo_de_id, cau_hoi_id, thu_tu, phan, la_cau_vi_du)
                VALUES (:bo_de_id, :cau_hoi_id, :thu_tu, :phan, :vi_du)
            """),
            {"bo_de_id": bo_de_id, "cau_hoi_id": item["cau_hoi_id"], "thu_tu": index,
             "phan": item.get("phan"), "vi_du": bool(item.get("la_cau_vi_du"))},
        )


def set_exam_status(db: Session, bo_de_id: int, trang_thai: str) -> None:
    db.execute(text("UPDATE bo_de SET trang_thai = :s WHERE id = :id"), {"s": trang_thai, "id": bo_de_id})


def published_exam_versions(db: Session, ma_goc_id: int) -> list[int]:
    return [int(x) for x in db.execute(
        text("SELECT id FROM bo_de WHERE ma_goc_id = :g AND trang_thai = 'da_dang'"), {"g": ma_goc_id}
    ).scalars().all()]


def has_attempts(db: Session, bo_de_id: int) -> bool:
    return db.execute(
        text("SELECT EXISTS(SELECT 1 FROM luot_lam WHERE bo_de_id = :id)"), {"id": bo_de_id}
    ).scalar_one() == 1


def delete_exam_row(db: Session, bo_de_id: int) -> None:
    db.execute(text("DELETE FROM bo_de_cau_hoi WHERE bo_de_id = :id"), {"id": bo_de_id})
    db.execute(text("DELETE FROM bo_de WHERE id = :id"), {"id": bo_de_id})


def list_exams(db: Session, cap_do_id: int | None, trang_thai: str | None, q: str | None) -> list[dict]:
    where = ["b.loai = 'de_thi'",
             "b.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id)"]
    params: dict = {}
    if cap_do_id:
        where.append("b.cap_do_id = :cap_do_id")
        params["cap_do_id"] = cap_do_id
    if trang_thai:
        where.append("b.trang_thai = :trang_thai")
        params["trang_thai"] = trang_thai
    if q:
        where.append("(b.ten LIKE :q OR g.ma_de LIKE :q)")
        params["q"] = f"%{q}%"
    rows = db.execute(
        text(f"""
            SELECT b.id, b.ma_goc_id, b.phien_ban, b.ten, g.ma_de, b.cap_do_id, cd.ten AS ten_cap_do,
                   b.thoi_luong_phut, b.trang_thai, b.tao_luc,
                   (SELECT COUNT(*) FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id AND i.la_cau_vi_du = 0) AS so_cau,
                   EXISTS(SELECT 1 FROM bo_de p WHERE p.ma_goc_id = b.ma_goc_id AND p.trang_thai = 'da_dang') AS co_ban_dang_dung,
                   (SELECT u.ho_ten FROM nguoi_dung u WHERE u.id = g.nguoi_tao_id) AS nguoi_tao,
                   (SELECT u.ho_ten FROM nguoi_dung u WHERE u.id = b.nguoi_tao_id) AS nguoi_sua
            FROM bo_de b
            JOIN bo_de g ON g.id = b.ma_goc_id
            JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE {' AND '.join(where)}
            ORDER BY cd.thu_tu, b.ma_goc_id DESC
        """),
        params,
    ).mappings().all()
    return [{**dict(r), "co_ban_dang_dung": bool(r["co_ban_dang_dung"])} for r in rows]
