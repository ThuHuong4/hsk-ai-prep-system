"""Nhiệm vụ ngày (mục 4.5): 3 nhiệm vụ cố định, mỗi cái +1 năng lượng, nhận 1 lần/ngày (theo ngày của máy chủ).

Tiến độ tính lại từ lượt làm (không lưu riêng); chỉ lưu việc nhận thưởng (nhat_ky_thuong, có chỉ mục duy nhất theo ngày).
Đang 5/5 thì chưa nhận được nhưng giữ quyền nhận đến hết ngày.
"""
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.practice.services import path_view

MISSIONS = [
    {"ma": "nv_so_tay", "ten": "Ôn 5 câu trong Sổ tay", "can": 5, "duong_dan": "/hoc-vien/so-tay-cau-sai", "nut": "Ôn ngay"},
    {"ma": "nv_on_luyen", "ten": "Hoàn thành 1 bài Ôn luyện", "can": 1, "duong_dan": "/hoc-vien/on-luyen", "nut": "Học tiếp"},
    {"ma": "nv_thi_thu", "ten": "Hoàn thành 1 lượt Thi thử", "can": 1, "duong_dan": "/hoc-vien/thi-thu", "nut": "Chọn đề"},
]


def _progress(db: Session, uid: int) -> dict:
    p = {"u": uid}
    so_tay = db.execute(text("""
        SELECT COUNT(DISTINCT q.ma_goc_id) FROM cau_tra_loi a
        JOIN luot_lam l ON l.id = a.luot_lam_id JOIN cau_hoi q ON q.id = a.cau_hoi_id
        WHERE l.nguoi_dung_id = :u AND l.loai_boc_cau = 'so_tay' AND a.xac_nhan_luc >= CURDATE()"""), p).scalar_one()
    on_luyen = db.execute(text("""
        SELECT COUNT(*) FROM luot_lam l LEFT JOIN bo_de b ON b.id = l.bo_de_id
        WHERE l.nguoi_dung_id = :u AND l.trang_thai = 'da_nop' AND l.nop_luc >= CURDATE()
          AND (
            b.loai IN ('bai', 'cuoi_thua')
            OR (l.loai_boc_cau IN ('vuot_thua', 'bat_dau_cap', 'vuot_chang') AND l.ap_dung_luc IS NOT NULL)
          )
          AND NOT EXISTS(
            SELECT 1 FROM cau_tra_loi a
            JOIN cau_hoi q ON q.id = a.cau_hoi_id
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE a.luot_lam_id = l.id
              AND (
                v.diem IS NULL
                OR (q.dang IN ('viet_mo', 'dich_cau') AND v.diem < COALESCE(q.nguong_dat, 6.0))
                OR (q.dang NOT IN ('viet_mo', 'dich_cau') AND v.diem < 1)
              )
          )"""), p).scalar_one()
    thi_thu = db.execute(text("""
        SELECT COUNT(*) FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
        WHERE l.nguoi_dung_id = :u AND l.trang_thai = 'da_nop' AND l.nop_luc >= CURDATE() AND b.loai = 'de_thi'
          AND EXISTS(SELECT 1 FROM cau_tra_loi a WHERE a.luot_lam_id = l.id
                     AND (a.phuong_an_chon_id IS NOT NULL OR a.van_ban IS NOT NULL))"""), p).scalar_one()
    return {"nv_so_tay": int(so_tay), "nv_on_luyen": int(on_luyen), "nv_thi_thu": int(thi_thu)}


def _effective_target(m: dict, notebook_count: int, done_raw: int) -> tuple[int, str]:
    if m["ma"] == "nv_so_tay" and 0 < max(notebook_count, done_raw) < m["can"]:
        target = max(notebook_count, done_raw)
        return target, f"Ôn hết {target} câu trong Sổ tay"
    return m["can"], m["ten"]


def list_missions(db: Session, uid: int) -> dict:
    energy, max_energy = path_view.sync_user_energy(db, uid, auto_commit=True)
    progress = _progress(db, uid)
    claimed = {r[0] for r in db.execute(text("""
        SELECT ly_do FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND tao_luc >= CURDATE()
          AND ly_do IN ('nv_so_tay', 'nv_on_luyen', 'nv_thi_thu')"""), {"u": uid}).all()}
    notebook = int(db.execute(text("""SELECT COUNT(*) FROM so_tay s JOIN cau_hoi g ON g.id = s.cau_hoi_goc_id
                                      WHERE s.nguoi_dung_id = :u AND s.trang_thai <> 'da_loai' AND g.dung_on_luyen = 1"""),
                              {"u": uid}).scalar_one())
    items = []
    for m in MISSIONS:
        can_eff, ten_eff = _effective_target(m, notebook, progress[m["ma"]])
        done = min(progress[m["ma"]], can_eff)
        items.append({**m, "ten": ten_eff, "can": can_eff, "da_lam": done, "xong": done >= can_eff, "da_nhan": m["ma"] in claimed,
                      "ghi_chu": "Sổ tay hiện đang trống (câu làm sai khi học sẽ tự lưu vào đây)" if m["ma"] == "nv_so_tay" and notebook == 0 and done == 0 else None})
    return {"nang_luong": energy, "nang_luong_toi_da": max_energy, "nhiem_vu": items}


def claim(db: Session, uid: int, ma: str) -> dict:
    mission = next((m for m in MISSIONS if m["ma"] == ma), None)
    if mission is None:
        raise NotFoundError()
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        energy, max_energy = path_view.sync_user_energy(db, uid, auto_commit=False)
        notebook = int(db.execute(text("""SELECT COUNT(*) FROM so_tay s JOIN cau_hoi g ON g.id = s.cau_hoi_goc_id
                                          WHERE s.nguoi_dung_id = :u AND s.trang_thai <> 'da_loai' AND g.dung_on_luyen = 1"""),
                                  {"u": uid}).scalar_one())
        prog = _progress(db, uid)
        can_eff, _ = _effective_target(mission, notebook, prog[ma])
        if prog[ma] < can_eff:
            raise RuleError("Chưa hoàn thành nhiệm vụ")
        if db.execute(text("SELECT 1 FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = :l AND tao_luc >= CURDATE()"),
                      {"u": uid, "l": ma}).first():
            raise ConflictError("Hôm nay đã nhận thưởng nhiệm vụ này")
        if energy >= max_energy:
            raise RuleError(f"Năng lượng đang đầy {max_energy}/{max_energy}. Quyền nhận giữ đến hết hôm nay")
        db.execute(text("UPDATE nguoi_dung SET nang_luong = nang_luong + 1 WHERE id = :u"), {"u": uid})
        db.execute(text("INSERT INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong) VALUES (:u, :l, 1)"), {"u": uid, "l": ma})
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if getattr(getattr(error, "orig", None), "args", [None])[0] == 1062:
            raise ConflictError("Hôm nay đã nhận thưởng nhiệm vụ này") from error
        raise
    except Exception:
        db.rollback()
        raise
    return {"message": "+1 năng lượng", "nang_luong": energy + 1, "nang_luong_toi_da": max_energy}
