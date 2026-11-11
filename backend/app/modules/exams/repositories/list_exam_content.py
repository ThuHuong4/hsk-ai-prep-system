from sqlalchemy import text
from sqlalchemy.orm import Session

_EXAM_QUESTION_IDS = """
    SELECT ct.ma_cau_hoi
    FROM cau_hoi_trong_de ct
    JOIN phan_de_thi p ON p.ma_phan = ct.ma_phan
    WHERE p.ma_bo_de = :ma_bo_de
"""


def _rows(db: Session, sql: str, ma_bo_de: int) -> list[dict]:
    result = db.execute(text(sql), {"ma_bo_de": ma_bo_de}).mappings().all()
    return [dict(row) for row in result]


def list_sections(db: Session, ma_bo_de: int) -> list[dict]:
    return _rows(db, """
        SELECT ma_phan, ma_ky_nang, ten_phan, thu_tu, huong_dan
        FROM phan_de_thi
        WHERE ma_bo_de = :ma_bo_de
        ORDER BY thu_tu
    """, ma_bo_de)


def list_questions(db: Session, ma_bo_de: int) -> list[dict]:
    return _rows(db, """
        SELECT ct.ma_phan, ct.thu_tu,
               ch.ma_cau_hoi, ch.ma_dang, ch.noi_dung, ch.ngu_lieu,
               ch.am_thanh_url, ch.hinh_anh_url, ch.ma_nhom_cau_hoi
        FROM phan_de_thi p
        JOIN cau_hoi_trong_de ct ON ct.ma_phan = p.ma_phan
        JOIN cau_hoi ch ON ch.ma_cau_hoi = ct.ma_cau_hoi
        WHERE p.ma_bo_de = :ma_bo_de
        ORDER BY p.thu_tu, ct.thu_tu
    """, ma_bo_de)


def list_question_groups(db: Session, ma_bo_de: int) -> list[dict]:
    return _rows(db, f"""
        SELECT n.ma_nhom_cau_hoi, n.noi_dung, n.hinh_anh_url
        FROM nhom_cau_hoi n
        WHERE n.ma_nhom_cau_hoi IN (
            SELECT ch.ma_nhom_cau_hoi
            FROM cau_hoi ch
            WHERE ch.ma_cau_hoi IN ({_EXAM_QUESTION_IDS})
        )
        ORDER BY n.ma_nhom_cau_hoi
    """, ma_bo_de)


def list_options(db: Session, ma_bo_de: int) -> list[dict]:
    return _rows(db, f"""
        SELECT pa.ma_cau_hoi, pa.ma_phuong_an, pa.ky_hieu,
               pa.noi_dung, pa.hinh_anh_url, pa.thu_tu
        FROM phuong_an pa
        WHERE pa.ma_cau_hoi IN ({_EXAM_QUESTION_IDS})
        ORDER BY pa.ma_cau_hoi, pa.thu_tu
    """, ma_bo_de)