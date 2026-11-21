"""Kiểm tra "Bắt đầu cấp" và "Vượt chặng" (mục 4.2), riêng từng kỹ năng.

- Bắt đầu cấp L: cấp L đang khóa và không phải cấp mở sẵn; 10 câu rút từ bài/cuối thửa đang đăng của cấp ngay dưới L
  (cùng kỹ năng), không kiểm tra lại các cấp thấp hơn nữa. Viết mở sẵn HSK 3 nên chỉ có từ HSK 4.
  Đúng 10/10 → mở cấp L của kỹ năng đó.
- Vượt chặng L: cấp L đang mở và mọi thửa có bài của L đã xong hoặc đã vượt; 15 câu rút từ toàn cấp L.
  Đúng 15/15 → mở cấp kế; L là cấp cuối → ghi hoàn thành lộ trình kỹ năng.
- Chung: Học viên xác nhận trước khi bắt đầu; không tốn năng lượng, không đếm ngược; giấu đáp án đến khi nộp;
  chỉ dùng câu có đáp án xác định; thiếu câu thì không mở, không lấy câu cấp/kỹ năng khác bù.
  Thoát giữ câu đã lưu; chưa đạt giữ quyền cũ; mỗi lượt độc lập. Đạt lần đầu +20 KN (mỗi cấp × kỹ năng).
- Lưu bằng cột có sẵn: luot_lam.loai_boc_cau = 'bat_dau_cap' | 'vuot_chang', cap_do_id, ky_nang, ap_dung_luc.
  Lấy bài, lưu câu, nộp, Hỏi Xiang dùng chung với kiểm tra vượt thửa (skip_service).
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.practice.services import path_view

SIZE = {"bat_dau_cap": 10, "vuot_chang": 15}
GRADABLE_SQL = "('chon_mot', 'dung_sai', 'chon_bo_chung', 'sap_xep', 'dien_chu')"


def _pool(db: Session, cap_do_id: int, skill: str) -> list[int]:
    """Câu có đáp án xác định trong bài/cuối thửa đang đăng của mọi thửa đang đăng ở cấp × kỹ năng."""
    rows = db.execute(
        text(f"""SELECT DISTINCT q.id FROM bo_de t
                 JOIN bo_de b ON b.thua_id = t.ma_goc_id AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'
                 JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
                 JOIN cau_hoi q ON q.id = i.cau_hoi_id
                 WHERE t.loai = 'thua' AND t.trang_thai = 'da_dang' AND t.cap_do_id = :c AND t.ky_nang = :k
                   AND q.dang IN {GRADABLE_SQL}"""),
        {"c": cap_do_id, "k": skill},
    ).all()
    return [int(r[0]) for r in rows]


def _open_attempt(db: Session, uid: int, kind: str, cap_do_id: int, skill: str) -> int | None:
    return db.execute(
        text("""SELECT id FROM luot_lam WHERE nguoi_dung_id = :u AND loai_boc_cau = :t AND cap_do_id = :c AND ky_nang = :k
                AND trang_thai = 'dang_lam' ORDER BY id DESC LIMIT 1"""),
        {"u": uid, "t": kind, "c": cap_do_id, "k": skill},
    ).scalar_one_or_none()


def _below(lv: list[dict], level: dict) -> dict | None:
    i = next(k for k, l in enumerate(lv) if l["id"] == level["id"])
    return lv[i - 1] if i > 0 else None


def start_info(db: Session, uid: int, skill: str, level: dict, lv: list[dict]) -> dict:
    """Thông tin nút "Bắt đầu cấp" cho một cấp đang khóa."""
    info = {"loai": "bat_dau_cap", "so_cau": SIZE["bat_dau_cap"], "duoc_lam": False, "ly_do": None,
            "cap_kiem_tra": None, "luot_dang_lam": None}
    below = _below(lv, level)
    if below is None or below["thu_tu"] < path_view.START_ORDER[skill]:
        info["ly_do"] = "Cấp này không có kiểm tra bắt đầu cấp cho kỹ năng này"
        return info
    info["cap_kiem_tra"] = {"id": below["id"], "ten": below["ten"]}
    if len(_pool(db, below["id"], skill)) < SIZE["bat_dau_cap"]:
        info["ly_do"] = f"{below['ten']} chưa đủ câu hỏi để mở kiểm tra"
        return info
    info["duoc_lam"] = True
    info["luot_dang_lam"] = _open_attempt(db, uid, "bat_dau_cap", level["id"], skill)
    return info


def stage_info(db: Session, uid: int, skill: str, level: dict, lv: list[dict], lands: list[dict], passed: dict) -> dict:
    """Thông tin "Vượt chặng" cho một cấp đang mở."""
    i = next(k for k, l in enumerate(lv) if l["id"] == level["id"])
    nxt = lv[i + 1] if i + 1 < len(lv) else None
    info = {"loai": "vuot_chang", "so_cau": SIZE["vuot_chang"], "duoc_lam": False, "ly_do": None,
            "da_dat": level["id"] in passed["vuot_chang"], "cap_ke": nxt and {"id": nxt["id"], "ten": nxt["ten"]},
            "luot_dang_lam": None}
    real = [land for land in lands if land["co_bai"]]
    if not real:
        info["ly_do"] = "Cấp này chưa có thửa nào"
        return info
    left = [land["ten"] for land in real if not (land["thu_hoach"] or land["da_vuot"])]
    if left:
        info["ly_do"] = f"Hoàn thành hoặc vượt hết các thửa trước (còn {len(left)} thửa)"
        return info
    if len(_pool(db, level["id"], skill)) < SIZE["vuot_chang"]:
        info["ly_do"] = "Cấp này chưa đủ câu hỏi để mở kiểm tra vượt cấp"
        return info
    info["duoc_lam"] = True
    info["luot_dang_lam"] = _open_attempt(db, uid, "vuot_chang", level["id"], skill)
    return info


def start(db: Session, uid: int, kind: str, cap_do_id: int, skill: str) -> int:
    if kind not in SIZE or skill not in path_view.SKILLS:
        raise NotFoundError()
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        lv = path_view.levels(db)
        level = next((l for l in lv if l["id"] == cap_do_id), None)
        if level is None:
            raise NotFoundError()
        opened = path_view.opened_levels(db, uid, skill, lv)
        is_open = path_view.level_open(level, skill, opened)
        if kind == "bat_dau_cap":
            if is_open:
                raise ConflictError("Cấp này đã mở, không cần kiểm tra bắt đầu cấp")
            info = start_info(db, uid, skill, level, lv)
            source = info["cap_kiem_tra"]["id"] if info["cap_kiem_tra"] else None
        else:
            if not is_open:
                raise ConflictError("Cấp này chưa mở")
            lands = path_view.build_map(db, uid, level["id"], skill)
            info = stage_info(db, uid, skill, level, lv, lands, path_view.level_tests(db, uid, skill))
            source = level["id"]
        if info["luot_dang_lam"]:  # làm tiếp lượt đang dở, đúng bộ câu cũ
            db.commit()
            return int(info["luot_dang_lam"])
        if not info["duoc_lam"]:
            raise RuleError(info["ly_do"] or "Chưa mở được bài kiểm tra này")
        rng = random.SystemRandom()
        picked = rng.sample(_pool(db, source, skill), SIZE[kind])
        luot_id = int(db.execute(
            text("""INSERT INTO luot_lam (nguoi_dung_id, loai_boc_cau, cap_do_id, ky_nang, trang_thai, vi_tri_hien_tai)
                    VALUES (:u, :t, :c, :k, 'dang_lam', 1)"""),
            {"u": uid, "t": kind, "c": level["id"], "k": skill},
        ).lastrowid)
        for pos, qid in enumerate(picked, start=1):
            db.execute(
                text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, seed_xao) VALUES (:l, :q, :t, :s)"),
                {"l": luot_id, "q": qid, "t": pos, "s": rng.randrange(1, 2**31)},
            )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise
