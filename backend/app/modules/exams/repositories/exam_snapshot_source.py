from sqlalchemy import text
from sqlalchemy.orm import Session

PUBLISHED = 1  # bo_de_thi.trang_thai: 1 = Đã xuất bản


def find_published_exam_for_snapshot(db: Session, ma_bo_de: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT ma_bo_de, ma_cap_do, ten_bo_de, thoi_gian_giay,
                   am_thanh_url, phien_ban, quy_tac_cham
            FROM bo_de_thi
            WHERE ma_bo_de = :ma_bo_de AND trang_thai = :trang_thai
        """),
        {"ma_bo_de": ma_bo_de, "trang_thai": PUBLISHED},
    ).mappings().first()
    return dict(row) if row else None


def list_snapshot_questions(db: Session, ma_bo_de: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT ct.ma_phan, ct.diem_toi_da, p.ma_ky_nang,
                   ch.ma_cau_hoi, ch.ma_dang, ch.noi_dung, ch.ngu_lieu,
                   ch.am_thanh_url, ch.hinh_anh_url, ch.ma_nhom_cau_hoi,
                   ch.dap_an_chuan, ch.cham_tu_dong, ch.phien_ban
            FROM phan_de_thi p
            JOIN cau_hoi_trong_de ct ON ct.ma_phan = p.ma_phan
            JOIN cau_hoi ch ON ch.ma_cau_hoi = ct.ma_cau_hoi
            WHERE p.ma_bo_de = :ma_bo_de
            ORDER BY p.thu_tu, ct.thu_tu
        """),
        {"ma_bo_de": ma_bo_de},
    ).mappings().all()
    return [dict(row) for row in rows]