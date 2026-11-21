from sqlalchemy import text
from sqlalchemy.orm import Session


def list_questions(db: Session, filters: dict, limit: int, offset: int) -> dict:
    """Câu cấp cao nhất (không phải câu con).
    trang_thai = 'da_dang' → bản đang dùng (mỗi câu tối đa 1); còn lại → phiên bản mới nhất."""
    where = ["c.cau_cha_id IS NULL"]
    params: dict = {"limit": limit, "offset": offset}
    if filters.get("trang_thai") == "da_dang":
        where.append("c.trang_thai = 'da_dang'")
    else:
        where.append("c.phien_ban = (SELECT MAX(x.phien_ban) FROM cau_hoi x WHERE x.ma_goc_id = c.ma_goc_id)")
        if filters.get("trang_thai"):
            where.append("c.trang_thai = :trang_thai")
            params["trang_thai"] = filters["trang_thai"]
    for key in ("cap_do_id", "ky_nang", "dang"):
        if filters.get(key):
            where.append(f"c.{key} = :{key}")
            params[key] = filters[key]
    if filters.get("dung_thi_thu"):
        where.append("c.dung_thi_thu = 1")
    if filters.get("dung_on_luyen"):
        where.append("c.dung_on_luyen = 1")
    if filters.get("q"):
        where.append("(c.noi_dung LIKE :q OR c.loi_nghe LIKE :q OR c.ma_goc_id = :q_id)")
        params["q"] = f"%{filters['q']}%"
        params["q_id"] = int(filters["q"]) if str(filters["q"]).isdigit() else -1
    condition = " AND ".join(where)

    total = db.execute(text(f"SELECT COUNT(*) FROM cau_hoi c WHERE {condition}"), params).scalar_one()
    rows = db.execute(
        text(f"""
            SELECT c.id, c.ma_goc_id, c.phien_ban, c.dang, c.cap_do_id, cd.ten AS ten_cap_do, c.ky_nang,
                   c.trang_thai, c.dung_on_luyen, c.dung_thi_thu, c.dung_dau_vao,
                   LEFT(COALESCE(c.noi_dung, c.loi_nghe, ''), 160) AS tom_tat,
                   c.tep_audio IS NOT NULL AS co_audio, c.tep_hinh IS NOT NULL AS co_hinh,
                   (SELECT COUNT(*) FROM cau_hoi k WHERE k.cau_cha_id = c.id) AS so_cau_con,
                   EXISTS(SELECT 1 FROM cau_hoi p WHERE p.ma_goc_id = c.ma_goc_id
                          AND p.trang_thai = 'da_dang') AS co_ban_dang_dung,
                   c.tao_luc,
                   (SELECT u.ho_ten FROM cau_hoi g JOIN nguoi_dung u ON u.id = g.nguoi_tao_id WHERE g.id = c.ma_goc_id) AS nguoi_tao,
                   (SELECT u.ho_ten FROM nguoi_dung u WHERE u.id = c.nguoi_tao_id) AS nguoi_sua
            FROM cau_hoi c JOIN cap_do cd ON cd.id = c.cap_do_id
            WHERE {condition}
            ORDER BY c.ma_goc_id DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).mappings().all()
    items = []
    for r in rows:
        item = dict(r)
        for flag in ("dung_on_luyen", "dung_thi_thu", "dung_dau_vao", "co_audio", "co_hinh", "co_ban_dang_dung"):
            item[flag] = bool(item[flag])
        items.append(item)
    return {"tong": int(total), "muc": items}
