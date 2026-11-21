"""Quản trị viên (mục 6.7): tài khoản, nhật ký quản trị, tổng quan.

Quy tắc:
- Tìm/lọc tài khoản; đổi Học viên ↔ Giảng viên; khóa/mở khóa.
- Không tự sửa tài khoản mình, không sửa tài khoản Quản trị viên khác, không nâng ai lên Quản trị viên.
- Mỗi thao tác ghi nhat_ky_quan_tri (người thao tác, tài khoản bị tác động, loại, vai trò cũ → mới, lý do, thời điểm).
- Khóa: tăng phien_ban_phien để phiên đăng nhập cũ mất hiệu lực; mọi API đã kiểm tra trạng thái tài khoản mỗi lần gọi.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.security.roles import Role

PAGE_SIZE = 20
ASSIGNABLE = {int(Role.HOC_VIEN), int(Role.GIANG_VIEN)}


def overview(db: Session) -> dict:
    roles = {int(r[0]): int(r[1]) for r in db.execute(text("SELECT vai_tro_id, COUNT(*) FROM nguoi_dung GROUP BY vai_tro_id")).all()}
    row = db.execute(text("""
        SELECT SUM(trang_thai = 'hoat_dong') AS hoat_dong, SUM(trang_thai = 'khoa') AS khoa,
               SUM(tao_luc >= CURDATE() - INTERVAL 6 DAY) AS moi_7_ngay, SUM(tao_luc >= CURDATE() - INTERVAL 29 DAY) AS moi_30_ngay,
               SUM(vai_tro_id = :hv AND ks_trang_thai = 'da_tra_loi') AS da_khao_sat
        FROM nguoi_dung"""), {"hv": int(Role.HOC_VIEN)}).mappings().one()
    recent = recent_logs(db, limit=5)
    return {
        "hoc_vien": roles.get(int(Role.HOC_VIEN), 0), "giang_vien": roles.get(int(Role.GIANG_VIEN), 0),
        "quan_tri_vien": roles.get(int(Role.QUAN_TRI_VIEN), 0),
        **{k: int(v or 0) for k, v in row.items()},
        "nhat_ky_gan_day": recent,
    }


def list_accounts(db: Session, q: str | None, vai_tro: int | None, trang_thai: str | None, page: int) -> dict:
    where, params = ["1 = 1"], {}
    if q:
        where.append("(n.email LIKE :q OR n.ho_ten LIKE :q)")
        params["q"] = f"%{q}%"
    if vai_tro:
        where.append("n.vai_tro_id = :vt")
        params["vt"] = vai_tro
    if trang_thai:
        where.append("n.trang_thai = :tt")
        params["tt"] = trang_thai
    cond = " AND ".join(where)
    total = db.execute(text(f"SELECT COUNT(*) FROM nguoi_dung n WHERE {cond}"), params).scalar_one()
    rows = db.execute(text(f"""
        SELECT n.id, n.email, n.ho_ten, n.vai_tro_id, v.ten AS ten_vai_tro, n.trang_thai, n.tao_luc,
               n.email_xac_minh_luc IS NOT NULL AS da_xac_minh, n.mat_khau_bam IS NOT NULL AS co_mat_khau,
               n.google_sub IS NOT NULL AS co_google
        FROM nguoi_dung n JOIN vai_tro v ON v.id = n.vai_tro_id
        WHERE {cond} ORDER BY n.id DESC LIMIT :lim OFFSET :off"""),
        {**params, "lim": PAGE_SIZE, "off": (page - 1) * PAGE_SIZE}).mappings().all()
    items = [{**dict(r), "da_xac_minh": bool(r["da_xac_minh"]), "co_mat_khau": bool(r["co_mat_khau"]),
              "co_google": bool(r["co_google"]), "tao_luc": r["tao_luc"].isoformat() if r["tao_luc"] else None} for r in rows]
    return {"tong": int(total), "trang": page, "so_moi_trang": PAGE_SIZE, "tai_khoan": items}


def _target(db: Session, admin_id: int, user_id: int) -> dict:
    if user_id == admin_id:
        raise RuleError("Không tự sửa tài khoản của mình")
    row = db.execute(text("SELECT id, vai_tro_id, trang_thai FROM nguoi_dung WHERE id = :id FOR UPDATE"), {"id": user_id}).mappings().first()
    if row is None:
        raise NotFoundError()
    if row["vai_tro_id"] == int(Role.QUAN_TRI_VIEN):
        raise RuleError("Không sửa tài khoản Quản trị viên khác")
    return dict(row)


def _log(db: Session, admin_id: int, user_id: int, action: str, old: int | None, new: int | None, reason: str | None) -> None:
    db.execute(text("""
        INSERT INTO nhat_ky_quan_tri (nguoi_thao_tac_id, nguoi_bi_tac_dong_id, hanh_dong, vai_tro_cu_id, vai_tro_moi_id, ly_do)
        VALUES (:a, :u, :h, :o, :n, :r)"""), {"a": admin_id, "u": user_id, "h": action, "o": old, "n": new, "r": reason})


def set_locked(db: Session, admin_id: int, user_id: int, lock: bool, reason: str | None) -> str:
    try:
        target = _target(db, admin_id, user_id)
        wanted = "khoa" if lock else "hoat_dong"
        if target["trang_thai"] == wanted:
            raise ConflictError("Tài khoản đã bị khóa" if lock else "Tài khoản đang hoạt động")
        db.execute(text(f"""UPDATE nguoi_dung SET trang_thai = :t{', phien_ban_phien = phien_ban_phien + 1' if lock else ''}
                            WHERE id = :id"""), {"t": wanted, "id": user_id})
        _log(db, admin_id, user_id, "khoa" if lock else "mo_khoa", None, None, reason)
        db.commit()
        return "Đã khóa tài khoản" if lock else "Đã mở khóa tài khoản"
    except Exception:
        db.rollback()
        raise


def set_role(db: Session, admin_id: int, user_id: int, role_id: int, reason: str | None) -> str:
    try:
        if role_id not in ASSIGNABLE:
            raise RuleError("Chỉ đổi giữa Học viên và Giảng viên")
        target = _target(db, admin_id, user_id)
        if target["vai_tro_id"] == role_id:
            raise ConflictError("Tài khoản đã có vai trò này")
        db.execute(text("UPDATE nguoi_dung SET vai_tro_id = :v WHERE id = :id"), {"v": role_id, "id": user_id})
        _log(db, admin_id, user_id, "doi_vai_tro", target["vai_tro_id"], role_id, reason)
        db.commit()
        return "Đã đổi vai trò"
    except Exception:
        db.rollback()
        raise


def recent_logs(db: Session, hanh_dong: str | None = None, q: str | None = None, limit: int = 100) -> list[dict]:
    where, params = ["1 = 1"], {"lim": limit}
    if hanh_dong:
        where.append("k.hanh_dong = :h")
        params["h"] = hanh_dong
    if q:
        where.append("(b.email LIKE :q OR b.ho_ten LIKE :q OR a.email LIKE :q OR a.ho_ten LIKE :q)")
        params["q"] = f"%{q}%"
    rows = db.execute(text(f"""
        SELECT k.id, k.hanh_dong, k.ly_do, k.tao_luc,
               a.ho_ten AS nguoi_thao_tac, a.email AS email_thao_tac,
               b.ho_ten AS nguoi_bi_tac_dong, b.email AS email_bi_tac_dong,
               vc.ten AS vai_tro_cu, vm.ten AS vai_tro_moi
        FROM nhat_ky_quan_tri k
        JOIN nguoi_dung a ON a.id = k.nguoi_thao_tac_id
        JOIN nguoi_dung b ON b.id = k.nguoi_bi_tac_dong_id
        LEFT JOIN vai_tro vc ON vc.id = k.vai_tro_cu_id
        LEFT JOIN vai_tro vm ON vm.id = k.vai_tro_moi_id
        WHERE {' AND '.join(where)} ORDER BY k.id DESC LIMIT :lim"""), params).mappings().all()
    return [{**dict(r), "tao_luc": r["tao_luc"].isoformat() if r["tao_luc"] else None} for r in rows]


ROLE_INFO = {
    int(Role.HOC_VIEN): "Ôn luyện, Thi thử, Sổ tay, Lịch sử thi, Hỏi Xiang. Tự đăng ký là vai trò này.",
    int(Role.GIANG_VIEN): "Quản lý cấp độ, câu hỏi, đề thi thử, thửa và bài ôn, từ vựng, tài liệu; chấm Viết; xử lý báo lỗi.",
    int(Role.QUAN_TRI_VIEN): "Quản lý tài khoản và vai trò, xem nhật ký quản trị; không quản lý nội dung chuyên môn.",
}


def list_roles(db: Session) -> list[dict]:
    rows = db.execute(text("""SELECT v.id, v.ma, v.ten, COUNT(n.id) AS so_tai_khoan
                              FROM vai_tro v LEFT JOIN nguoi_dung n ON n.vai_tro_id = v.id
                              GROUP BY v.id, v.ma, v.ten ORDER BY v.id""")).mappings().all()
    return [{**dict(r), "so_tai_khoan": int(r["so_tai_khoan"]), "mo_ta": ROLE_INFO.get(r["id"], "Chưa định nghĩa quyền")} for r in rows]


def rename_role(db: Session, role_id: int, ten: str) -> str:
    try:
        if db.execute(text("SELECT id FROM vai_tro WHERE id = :id FOR UPDATE"), {"id": role_id}).first() is None:
            raise NotFoundError()
        if db.execute(text("SELECT 1 FROM vai_tro WHERE ten = :t AND id <> :id"), {"t": ten, "id": role_id}).first():
            raise ConflictError("Tên vai trò đã được dùng")
        db.execute(text("UPDATE vai_tro SET ten = :t WHERE id = :id"), {"t": ten, "id": role_id})
        db.commit()
        return "Đã đổi tên vai trò"
    except Exception:
        db.rollback()
        raise


def account_detail(db: Session, user_id: int) -> dict:
    row = db.execute(text("""
        SELECT n.id, n.email, n.ho_ten, n.vai_tro_id, v.ten AS ten_vai_tro, n.trang_thai, n.tao_luc,
               n.email_xac_minh_luc, n.mat_khau_bam IS NOT NULL AS co_mat_khau, n.google_sub IS NOT NULL AS co_google,
               n.ks_trang_thai
        FROM nguoi_dung n JOIN vai_tro v ON v.id = n.vai_tro_id WHERE n.id = :id"""), {"id": user_id}).mappings().first()
    if row is None:
        raise NotFoundError()
    logs = db.execute(text("""
        SELECT k.id, k.hanh_dong, k.ly_do, k.tao_luc, a.ho_ten AS nguoi_thao_tac, vc.ten AS vai_tro_cu, vm.ten AS vai_tro_moi
        FROM nhat_ky_quan_tri k JOIN nguoi_dung a ON a.id = k.nguoi_thao_tac_id
        LEFT JOIN vai_tro vc ON vc.id = k.vai_tro_cu_id LEFT JOIN vai_tro vm ON vm.id = k.vai_tro_moi_id
        WHERE k.nguoi_bi_tac_dong_id = :id ORDER BY k.id DESC LIMIT 20"""), {"id": user_id}).mappings().all()
    iso = lambda d: d.isoformat() if d else None
    return {
        **{k: row[k] for k in ("id", "email", "ho_ten", "vai_tro_id", "ten_vai_tro", "trang_thai", "ks_trang_thai")},
        "tao_luc": iso(row["tao_luc"]), "email_xac_minh_luc": iso(row["email_xac_minh_luc"]),
        "co_mat_khau": bool(row["co_mat_khau"]), "co_google": bool(row["co_google"]),
        "nhat_ky": [{**dict(l), "tao_luc": iso(l["tao_luc"])} for l in logs],
    }
