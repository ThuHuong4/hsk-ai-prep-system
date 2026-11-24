"""Bản đồ Ôn luyện của Học viên (mục 4.1): Kỹ năng → Cấp → Thửa → 5 ô.
    
- Chỉ hiện thửa/bài đang đăng. Thửa chưa có bài đăng → "Chưa xuất bản", không tạo tiến độ giả.
- Mở khóa: thửa đầu mở; thửa sau mở khi kiểm tra cuối thửa trước đạt. Trong thửa, ô sau mở khi ô trước đạt.
- Đạt = lượt đã nộp có mọi câu đúng (5/5, 10/10). Tiến độ tính theo bài gốc (mọi phiên bản).
- Vượt đến thửa: đạt kiểm tra vượt tới thửa T → các thửa trước T hiện "Đã vượt" (quyền bỏ qua, không phải đã học), T mở.
- Cấp mở sẵn: Nghe, Đọc, Từ vựng mở cấp đầu; Viết mở cấp thứ 3 (HSK 3). Cấp khác mở khi đạt
  "Bắt đầu cấp L" (mở L) hoặc "Vượt chặng L" (mở L+1), riêng từng kỹ năng (mục 4.2).
"""
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

SKILLS = ("nghe", "doc", "tu_vung", "viet")
START_ORDER = {"nghe": 1, "doc": 1, "tu_vung": 1, "viet": 1}
LESSON_SIZE = {"bai": 5, "cuoi_thua": 10}
ENERGY_BY_ORDER = {1: 5, 2: 6, 3: 8, 4: 10}
ENERGY_TIERS = [
    {"cap": "HSK 1", "thu_tu": 1, "tran": 5},
    {"cap": "HSK 2", "thu_tu": 2, "tran": 6},
    {"cap": "HSK 3", "thu_tu": 3, "tran": 8},
    {"cap": "HSK 4", "thu_tu": 4, "tran": 10},
]


def max_energy_for_order(order: int | None) -> int:
    """Trần năng lượng tối đa mở rộng theo thứ tự cấp độ HSK chính thức của học viên (5 -> 6 -> 8 -> 10)."""
    return ENERGY_BY_ORDER.get(int(order or 1), 5)


def levels(db: Session) -> list[dict]:
    rows = db.execute(
        text("SELECT id, ma, ten, thu_tu, diem_toi_da_thi, diem_dat_thi FROM cap_do WHERE trang_thai = 'da_dang' ORDER BY thu_tu")
    ).mappings().all()
    return [dict(r) for r in rows]


def assessed_level_order(db: Session, uid: int, lv: list[dict] | None = None) -> int:
    """Thứ tự cấp HSK (1..4) từ bài Đánh giá trình độ đầu vào 8 câu của học viên (mặc định 1 nếu chưa đánh giá)."""
    if not uid:
        return 1
    lv = lv if lv is not None else levels(db)
    order_by_id = {int(l["id"]): int(l["thu_tu"]) for l in lv}
    cap_id = db.execute(
        text("""
            SELECT k.cap_de_xuat_id
            FROM ket_qua_dau_vao k
            JOIN luot_lam l ON l.id = k.luot_lam_id
            WHERE l.nguoi_dung_id = :u
              AND l.loai_boc_cau = 'danh_gia_dau_vao'
              AND k.trang_thai_phan_tich = 'xong'
              AND k.cap_de_xuat_id IS NOT NULL
            ORDER BY l.id DESC LIMIT 1
        """),
        {"u": uid},
    ).scalar_one_or_none()
    if cap_id is not None and int(cap_id) in order_by_id:
        return order_by_id[int(cap_id)]
    return 1


def level_open(level: dict, skill: str, opened: set[int] | None = None) -> bool:
    """Kiểm tra cấp `level` có được mở cho học viên hay không (HSK L mở các cấp 1..L, khóa các cấp > L)."""
    if opened is not None:
        return int(level["id"]) in opened
    return int(level["thu_tu"]) == START_ORDER[skill]


def level_tests(db: Session, uid: int, skill: str) -> dict:
    """Lượt Bắt đầu cấp / Vượt chặng đã đạt của Học viên ở một kỹ năng: {'bat_dau_cap': {cap_id}, 'vuot_chang': {cap_id}}."""
    out = {"bat_dau_cap": set(), "vuot_chang": set()}
    if not uid:
        return out
    for kind, cap in db.execute(
        text("""SELECT DISTINCT loai_boc_cau, cap_do_id FROM luot_lam
                WHERE nguoi_dung_id = :u AND ky_nang = :k AND loai_boc_cau IN ('bat_dau_cap', 'vuot_chang')
                  AND trang_thai = 'da_nop' AND ap_dung_luc IS NOT NULL"""),
        {"u": uid, "k": skill},
    ).all():
        out[kind].add(int(cap))
    return out


def _mock_exam_stats(db: Session, uid: int, lv: list[dict]) -> tuple[set[int], dict[int, float]]:
    """Thống kê các kỳ Thi thử đã nộp của học viên theo thứ tự cấp `thu_tu`:
    Trả về `(tập_thứ_tự_cấp_đã_thi_đạt, điểm_thi_cao_nhất_theo_thứ_tự_cấp)` khớp công thức chuẩn HSK."""
    if not uid or not lv:
        return set(), {}
    lv_by_id = {int(l["id"]): l for l in lv}
    rows = db.execute(
        text("""
            SELECT l.id AS luot_id, b.cap_do_id,
                   COALESCE(q.ky_nang, p.ky_nang) AS ky_nang,
                   COUNT(*) AS so_cau,
                   SUM(CASE WHEN v.diem IS NULL THEN 1 ELSE 0 END) AS cho_cham,
                   SUM(
                     CASE
                       WHEN v.diem IS NULL THEN 0
                       WHEN q.dang IN ('viet_mo', 'dich_cau')
                         THEN LEAST(1.0, v.diem / GREATEST(1.0, COALESCE(q.diem_toi_da, 10.0)))
                       ELSE v.diem
                     END
                   ) AS tong_ty_le
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id AND i.la_cau_vi_du = 0
            JOIN cau_hoi q ON q.id = i.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            LEFT JOIN cau_tra_loi a ON a.luot_lam_id = l.id AND a.cau_hoi_id = i.cau_hoi_id
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE l.nguoi_dung_id = :u
              AND b.loai = 'de_thi'
              AND l.trang_thai = 'da_nop'
            GROUP BY l.id, b.cap_do_id, COALESCE(q.ky_nang, p.ky_nang)
        """),
        {"u": uid},
    ).mappings().all()

    by_attempt: dict[int, dict] = {}
    for r in rows:
        cid = int(r["cap_do_id"])
        if cid not in lv_by_id:
            continue
        att = by_attempt.setdefault(int(r["luot_id"]), {"cap_do_id": cid, "cho_cham": 0, "skills": []})
        att["cho_cham"] += int(r["cho_cham"] or 0)
        so_cau = int(r["so_cau"] or 0)
        if so_cau > 0:
            att["skills"].append(100.0 * float(r["tong_ty_le"] or 0.0) / so_cau)

    passed_orders: set[int] = set()
    best_by_order: dict[int, float] = {}
    for att in by_attempt.values():
        if att["cho_cham"] > 0 or not att["skills"]:
            continue
        level_meta = lv_by_id[att["cap_do_id"]]
        ord_no = int(level_meta["thu_tu"])
        max_exam = float(level_meta.get("diem_toi_da_thi") or (100 * len(att["skills"])))
        pass_exam = float(level_meta.get("diem_dat_thi") or (0.6 * max_exam))
        scale = max_exam / (100.0 * len(att["skills"]))
        total = round(sum(att["skills"]) * scale, 2)
        if total > best_by_order.get(ord_no, -1.0):
            best_by_order[ord_no] = total
        if total >= pass_exam:
            passed_orders.add(ord_no)

    return passed_orders, best_by_order


def _compute_proficiency_state(db: Session, uid: int, lv: list[dict]) -> dict:
    """Tính toán tập trung Trình độ HSK chính thức của học viên (1..4):
    - Khởi điểm từ cấp Đánh giá đầu vào 8 câu (`L0`).
    - Thăng từ cấp `L` lên `L+1` khi đạt 1 trong 2 cột mốc năng lực toàn diện:
        (1) Đạt chuẩn kỳ Thi thử HSK ở cấp `L` (`tong_diem >= diem_dat_thi`), HOẶC
        (2) Mở khóa vượt cấp đủ cả 4/4 kỹ năng (`nghe, doc, tu_vung, viet`) lên `L+1`.
    """
    base_order = assessed_level_order(db, uid, lv)
    raw_skill_orders: dict[str, set[int]] = {}
    id_to_order = {int(l["id"]): int(l["thu_tu"]) for l in lv}

    for skill in SKILLS:
        s_orders = {int(l["thu_tu"]) for l in lv if int(l["thu_tu"]) <= base_order}
        passed = level_tests(db, uid, skill)
        for cid in passed["bat_dau_cap"]:
            if int(cid) in id_to_order:
                s_orders.add(id_to_order[int(cid)])
        for i, level in enumerate(lv):
            if int(level["id"]) in passed["vuot_chang"] and i + 1 < len(lv):
                s_orders.add(int(lv[i + 1]["thu_tu"]))
        raw_skill_orders[skill] = s_orders

    passed_exam_orders, best_exam_by_order = _mock_exam_stats(db, uid, lv)

    cur_order = base_order
    sorted_orders = [int(l["thu_tu"]) for l in lv]
    # Nếu học viên từng thi đỗ ở một cấp `e_ord >= cur_order`, nâng tới cấp kế sau `e_ord`
    for idx, ord_no in enumerate(sorted_orders):
        if ord_no < cur_order or idx + 1 >= len(sorted_orders):
            continue
        next_ord = sorted_orders[idx + 1]
        exam_passed = any(p >= ord_no for p in passed_exam_orders)
        all_skills_unlocked = all(next_ord in raw_skill_orders[sk] for sk in SKILLS)
        if exam_passed or all_skills_unlocked:
            cur_order = next_ord
            for sk in SKILLS:
                raw_skill_orders[sk].add(next_ord)
        else:
            break

    return {
        "cur_order": cur_order,
        "skill_orders": raw_skill_orders,
        "passed_exam_orders": passed_exam_orders,
        "best_exam_by_order": best_exam_by_order,
    }


def opened_levels(db: Session, uid: int, skill: str, lv: list[dict] | None = None) -> set[int]:
    """Tập hợp ID các cấp được mở khóa của học viên ở kỹ năng `skill`:
    - Mở sẵn toàn bộ các cấp từ HSK 1 đến đúng Trình độ HSK hiện tại (`1..cur_order`), khóa chặt các cấp cao hơn.
    - Cộng thêm cấp kế tiếp nếu riêng kỹ năng `skill` đó học viên đã tự vượt qua bài Bắt đầu cấp / Vượt chặng.
    """
    lv = lv if lv is not None else levels(db)
    if not lv:
        return set()
    state = _compute_proficiency_state(db, uid, lv)
    allowed_orders = state["skill_orders"].get(skill, set()) | {
        int(l["thu_tu"]) for l in lv if int(l["thu_tu"]) <= state["cur_order"]
    }
    return {int(l["id"]) for l in lv if int(l["thu_tu"]) in allowed_orders}


def current_proficiency(db: Session, uid: int, lv: list[dict] | None = None) -> dict | None:
    """Trình độ HSK chính thức hiện tại của Học viên + thông tin tiến độ & điều kiện thăng lên cấp tiếp theo."""
    lv = lv if lv is not None else levels(db)
    if not lv:
        return None
    state = _compute_proficiency_state(db, uid, lv)
    cur_ord = state["cur_order"]
    chosen = next((l for l in lv if int(l["thu_tu"]) == cur_ord), lv[0])
    next_lv = next((l for l in lv if int(l["thu_tu"]) > cur_ord), None)

    diem_toi_da = int(chosen.get("diem_toi_da_thi") or 200)
    diem_dat = int(chosen.get("diem_dat_thi") or 120)
    best_cur = state["best_exam_by_order"].get(cur_ord)
    skills_at_next = (
        sum(1 for sk in SKILLS if int(next_lv["thu_tu"]) in state["skill_orders"].get(sk, set()))
        if next_lv else len(SKILLS)
    )

    return {
        "id": int(chosen["id"]),
        "ma": chosen["ma"],
        "ten": chosen["ten"],
        "thu_tu": cur_ord,
        "diem_toi_da_thi": diem_toi_da,
        "diem_dat_thi": diem_dat,
        "diem_thi_cao_nhat": best_cur,
        "cap_tiep_theo": next_lv["ten"] if next_lv else None,
        "so_ky_nang_vuot_cap": skills_at_next,
        "tong_ky_nang": len(SKILLS),
        "quy_tac_thang_cap": (
            f"Thi thử đạt chuẩn ≥ {diem_dat}/{diem_toi_da} điểm (hoặc vượt cấp đủ {len(SKILLS)}/{len(SKILLS)} kỹ năng trên lộ trình) để chính thức thăng lên {next_lv['ten']}."
            if next_lv
            else "Bạn đã mở khóa trọn vẹn cấp độ cao nhất trên hệ thống (HSK 4)."
        ),
    }


def lesson_progress(db: Session, uid: int, lesson_roots: list[int]) -> dict[int, dict]:
    """Theo bài gốc: đã đạt chưa, đã có lượt nộp chưa, lượt đang làm (nếu có)."""
    if not lesson_roots:
        return {}
    marks = ", ".join(f":r{i}" for i in range(len(lesson_roots)))
    params = {f"r{i}": v for i, v in enumerate(lesson_roots)}
    params["u"] = uid
    rows = db.execute(
        text(f"""
            SELECT b.ma_goc_id, l.id, l.trang_thai,
                   COUNT(a.id) AS tong,
                   SUM(
                     CASE
                       WHEN q.dang IN ('viet_mo', 'dich_cau') THEN IF(v.diem >= COALESCE(q.nguong_dat, 6.0), 1, 0)
                       WHEN v.diem >= 1 THEN 1
                       ELSE 0
                     END
                   ) AS dung
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            LEFT JOIN cau_tra_loi a ON a.luot_lam_id = l.id
            LEFT JOIN cau_hoi q ON q.id = a.cau_hoi_id
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE l.nguoi_dung_id = :u AND b.ma_goc_id IN ({marks}) AND l.trang_thai IN ('dang_lam', 'da_nop')
            GROUP BY b.ma_goc_id, l.id, l.trang_thai
        """),
        params,
    ).mappings().all()
    out: dict[int, dict] = {}
    for r in rows:
        p = out.setdefault(r["ma_goc_id"], {"dat": False, "da_nop": False, "luot_dang_lam": None})
        if r["trang_thai"] == "dang_lam":
            p["luot_dang_lam"] = r["id"]
        else:
            p["da_nop"] = True
            if r["tong"] and int(r["dung"] or 0) == int(r["tong"]):
                p["dat"] = True
    return out


def skip_targets(db: Session, uid: int) -> set[int]:
    """Thửa gốc mà Học viên đã đạt kiểm tra vượt tới (đã áp dụng quyền)."""
    if not uid:
        return set()
    rows = db.execute(
        text("""SELECT DISTINCT t.ma_goc_id FROM luot_lam l JOIN bo_de t ON t.id = l.thua_dich_id
                WHERE l.nguoi_dung_id = :u AND l.loai_boc_cau = 'vuot_thua' AND l.trang_thai = 'da_nop'
                  AND l.ap_dung_luc IS NOT NULL"""),
        {"u": uid},
    ).all()
    return {int(r[0]) for r in rows}


def land_offset(db: Session, cap_do_id: int, skill: str) -> int:
    """Số thửa đang đăng có bài của cùng kỹ năng ở các cấp thấp hơn → đánh số thửa liên tục qua các cấp."""
    return int(db.execute(
        text("""SELECT COUNT(*) FROM bo_de t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.loai = 'thua' AND t.ky_nang = :k AND t.trang_thai = 'da_dang' AND c.trang_thai = 'da_dang'
                  AND c.thu_tu < (SELECT thu_tu FROM cap_do WHERE id = :c)
                  AND EXISTS(SELECT 1 FROM bo_de b WHERE b.thua_id = t.ma_goc_id AND b.loai IN ('bai', 'cuoi_thua')
                             AND b.trang_thai = 'da_dang')"""),
        {"k": skill, "c": cap_do_id},
    ).scalar_one())


def level_passed_over(db: Session, uid: int, cap_do_id: int, skill: str) -> bool:
    """Chỉ khi đạt Vượt chặng (vuot_chang) ở chính cấp L hoặc cao hơn mới tính là vượt qua cấp L.
    Đạt Bắt đầu cấp (bat_dau_cap) ở cấp trên chỉ mở cấp trên, KHÔNG tự động gắn nhãn 'Đã vượt' cho cấp dưới (mục 6 NV.docx)."""
    if not uid:
        return False
    lv = levels(db)
    order = {l["id"]: l["thu_tu"] for l in lv}
    here = order.get(cap_do_id)
    if here is None:
        return False
    passed = level_tests(db, uid, skill)
    return any(order.get(c, 0) >= here for c in passed["vuot_chang"])


def build_map(db: Session, uid: int, cap_do_id: int, skill: str) -> list[dict]:
    lands = [dict(r) for r in db.execute(
        text("""SELECT id, ma_goc_id, ten, muc_tieu, vi_tri FROM bo_de
                WHERE loai = 'thua' AND cap_do_id = :c AND ky_nang = :k AND trang_thai = 'da_dang'
                ORDER BY vi_tri IS NULL, vi_tri, id"""),
        {"c": cap_do_id, "k": skill},
    ).mappings().all()]
    lessons_by_land: dict[int, list[dict]] = {}
    for land in lands:
        lessons_by_land[land["ma_goc_id"]] = [dict(r) for r in db.execute(
            text("""SELECT b.id, b.ma_goc_id, b.loai, b.vi_tri, b.ten, b.muc_tieu,
                           (SELECT COUNT(*) FROM bo_de_cau_hoi i WHERE i.bo_de_id = b.id) AS so_cau
                    FROM bo_de b WHERE b.thua_id = :t AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'
                    ORDER BY b.vi_tri"""),
            {"t": land["ma_goc_id"]},
        ).mappings().all()]
    progress = lesson_progress(db, uid, [l["ma_goc_id"] for ls in lessons_by_land.values() for l in ls])
    # Vượt đến thửa (mục 4.2): đạt kiểm tra vượt tới thửa T → mọi thửa trước T là "Đã vượt"
    skipped_to = skip_targets(db, uid)
    roots = [land["ma_goc_id"] for land in lands]
    skip_until = max((roots.index(g) for g in skipped_to if g in roots), default=0)
    if level_passed_over(db, uid, cap_do_id, skill):  # đã vượt lên cấp cao hơn → cả cấp này là "Đã vượt"
        skip_until = len(lands)

    result, open_land = [], True
    number = land_offset(db, cap_do_id, skill)  # số thứ tự thửa liên tục theo kỹ năng (thửa chưa có bài không đánh số)
    for li, land in enumerate(lands):
        lessons = lessons_by_land[land["ma_goc_id"]]
        skipped = li < skip_until
        slots, prev_ok = [], open_land or skipped
        for pos in range(1, 6):
            lesson = next((l for l in lessons if l["vi_tri"] == pos), None)
            if lesson is None:
                slots.append({"vi_tri": pos, "loai": "cuoi_thua" if pos == 5 else "bai", "trang_thai": "chua_xuat_ban"})
                prev_ok = False
                continue
            p = progress.get(lesson["ma_goc_id"], {})
            if p.get("dat"):
                state = "da_xong"
            elif skipped:  # thửa đã vượt: mọi ô chưa xong đều "Đã vượt", kể cả ô đang làm dở (vẫn làm tiếp được)
                state = "da_vuot"
            elif not prev_ok:
                state = "khoa"
            elif p.get("luot_dang_lam"):
                state = "dang_lam"
            elif p.get("da_nop"):
                state = "chua_dat"
            else:
                state = "chua_hoc"
            slots.append({
                "vi_tri": pos, "loai": lesson["loai"], "ma_goc_id": lesson["ma_goc_id"], "ten": lesson["ten"],
                "muc_tieu": lesson["muc_tieu"], "so_cau": int(lesson["so_cau"]) or LESSON_SIZE[lesson["loai"]], "trang_thai": state,
                "luot_dang_lam": p.get("luot_dang_lam"),
            })
            prev_ok = bool(p.get("dat")) or skipped
        harvested = bool(slots) and slots[4]["trang_thai"] == "da_xong"
        if lessons:
            number += 1
        result.append({
            "ma_goc_id": land["ma_goc_id"], "ten": land["ten"], "muc_tieu": land["muc_tieu"],
            "so_thu_tu": number if lessons else None,
            "mo": open_land or skipped, "co_bai": bool(lessons), "thu_hoach": harvested, "da_vuot": skipped, "o": slots,
        })
        open_land = harvested or li + 1 <= skip_until  # thửa kế là thửa bị vượt hoặc chính thửa đích
    return result


def summarize(lands: list[dict]) -> dict:
    lessons = [o for land in lands for o in land["o"] if o["trang_thai"] != "chua_xuat_ban"]
    nxt = None
    # Bài tiếp theo = ô chưa xong đầu tiên ở thửa đang mở xa nhất (đã vượt tới thửa sau thì Xiang đứng ở thửa sau),
    # không lùi về các ô còn lại của thửa đã vượt.
    for land in reversed(lands):
        if not land["mo"] or land.get("da_vuot"):
            continue
        for o in land["o"]:
            if o["trang_thai"] in ("dang_lam", "chua_dat", "chua_hoc"):
                nxt = {"thua": land["ten"], **{k: o[k] for k in ("ma_goc_id", "ten", "vi_tri", "loai", "trang_thai")}}
                break
        if nxt:
            break
    return {"so_bai": len(lessons), "da_xong": sum(1 for o in lessons if o["trang_thai"] == "da_xong"), "bai_tiep": nxt}


def streak_days(db: Session, uid: int) -> int:
    """Chuỗi ngày học liên tiếp (mục 8 NV.docx): ngày có hoàn tất (da_nop) ít nhất một hoạt động học/thi/đánh giá
    mà trong lượt đó học viên thực sự trả lời ít nhất 1 câu (trang_thai_thao_tac = 'da_tra_loi')."""
    today = db.execute(text("SELECT CURDATE()")).scalar_one()
    days = [r[0] for r in db.execute(
        text("""SELECT DISTINCT DATE(l.nop_luc) AS d FROM luot_lam l
                WHERE l.nguoi_dung_id = :u AND l.trang_thai = 'da_nop' AND l.nop_luc IS NOT NULL
                  AND EXISTS(SELECT 1 FROM cau_tra_loi a WHERE a.luot_lam_id = l.id
                             AND (a.trang_thai_thao_tac = 'da_tra_loi'
                                  OR a.phuong_an_chon_id IS NOT NULL OR a.van_ban IS NOT NULL))
                ORDER BY d DESC LIMIT 400"""),
        {"u": uid},
    ).all()]
    if not days or (today - days[0]).days > 1:
        return 0
    count, expected = 0, days[0]
    for d in days:
        if d != expected:
            break
        count += 1
        expected = d - timedelta(days=1)
    return count


def max_energy_for_user(db: Session, uid: int, trinh_do: dict | None = None) -> int:
    """Tính trần năng lượng tối đa hiện tại của học viên theo trình độ HSK chính thức (5 / 6 / 8 / 10)."""
    td = trinh_do if trinh_do is not None else current_proficiency(db, uid)
    return max_energy_for_order(td["thu_tu"] if td else 1)


def sync_user_energy(
    db: Session,
    uid: int,
    max_e: int | None = None,
    auto_commit: bool = False,
) -> tuple[int, int]:
    """Đồng bộ bình năng lượng của học viên (giữ cân bằng tuyệt đối với `v_doi_soat_nang_luong`):
    1) Mở rộng bình năng lượng (`thang_cap_nl`) ngay khi học viên thăng lên cấp HSK mới (5 -> 6 -> 8 -> 10).
    2) Tự động hồi đầy bình năng lượng (`hoi_ngay`) vào đầu ngày mới nếu chưa bị trừ năng lượng nào trong hôm nay.
    """
    target_max = int(max_e if max_e is not None else max_energy_for_user(db, uid))
    cur = int(db.execute(text("SELECT nang_luong FROM nguoi_dung WHERE id = :u"), {"u": uid}).scalar_one())
    granted_up = int(
        db.execute(
            text("SELECT COALESCE(SUM(so_luong), 0) FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = 'thang_cap_nl'"),
            {"u": uid},
        ).scalar_one()
    )
    prev_ceiling = 5 + granted_up
    need_up = target_max > prev_ceiling
    need_daily = False
    if not need_up and cur < target_max:
        has_daily = db.execute(
            text("SELECT 1 FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = 'hoi_ngay' AND tao_luc >= CURDATE() LIMIT 1"),
            {"u": uid},
        ).first()
        if not has_daily:
            spent_today = db.execute(
                text("""SELECT 1 FROM cau_tra_loi a JOIN luot_lam l ON l.id = a.luot_lam_id
                        WHERE l.nguoi_dung_id = :u AND a.nang_luong_tru > 0 AND a.xac_nhan_luc >= CURDATE() LIMIT 1"""),
                {"u": uid},
            ).first()
            need_daily = spent_today is None
    if not need_up and not need_daily:
        return cur, target_max

    cur = int(db.execute(text("SELECT nang_luong FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid}).scalar_one())
    granted_up = int(
        db.execute(
            text("SELECT COALESCE(SUM(so_luong), 0) FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = 'thang_cap_nl'"),
            {"u": uid},
        ).scalar_one()
    )
    prev_ceiling = 5 + granted_up
    changed = False

    if target_max > prev_ceiling:
        add_up = max(0, min(target_max - cur, target_max - prev_ceiling))
        if add_up > 0:
            db.execute(
                text("INSERT INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong) VALUES (:u, 'thang_cap_nl', :n)"),
                {"u": uid, "n": add_up},
            )
            db.execute(
                text("UPDATE nguoi_dung SET nang_luong = nang_luong + :n WHERE id = :u"),
                {"u": uid, "n": add_up},
            )
            cur += add_up
            changed = True

    if cur < target_max:
        has_daily = db.execute(
            text("SELECT 1 FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = 'hoi_ngay' AND tao_luc >= CURDATE() LIMIT 1"),
            {"u": uid},
        ).first()
        spent_today = db.execute(
            text("""SELECT 1 FROM cau_tra_loi a JOIN luot_lam l ON l.id = a.luot_lam_id
                    WHERE l.nguoi_dung_id = :u AND a.nang_luong_tru > 0 AND a.xac_nhan_luc >= CURDATE() LIMIT 1"""),
            {"u": uid},
        ).first()
        if not has_daily and spent_today is None:
            add_day = target_max - cur
            ins = db.execute(
                text("INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong) VALUES (:u, 'hoi_ngay', :n)"),
                {"u": uid, "n": add_day},
            )
            if ins.rowcount:
                db.execute(
                    text("UPDATE nguoi_dung SET nang_luong = nang_luong + :n WHERE id = :u"),
                    {"u": uid, "n": add_day},
                )
                cur += add_day
                changed = True

    if changed and auto_commit:
        db.commit()
    return cur, target_max


def energy_and_kn(db: Session, uid: int) -> dict:
    td = current_proficiency(db, uid)
    max_e = max_energy_for_order(td["thu_tu"] if td else 1)
    energy, max_e = sync_user_energy(db, uid, max_e=max_e, auto_commit=True)
    kn = int(
        db.execute(
            text("SELECT COALESCE(SUM(so_luong), 0) FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do LIKE 'kn\\_%'"),
            {"u": uid},
        ).scalar_one()
    )
    if td is not None:
        td["nang_luong_toi_da"] = max_e
        td["tran_nang_luong_tiep"] = max_energy_for_order(td["thu_tu"] + 1) if td.get("cap_tiep_theo") else None
    return {
        "nang_luong": energy,
        "nang_luong_toi_da": max_e,
        "bang_tran_nang_luong": ENERGY_TIERS,
        "kn": kn,
        "chuoi_ngay": streak_days(db, uid),
        "trinh_do": td,
    }


def overview(db: Session, uid: int) -> dict:
    lv = levels(db)
    skills = []
    for skill in SKILLS:
        opened = opened_levels(db, uid, skill, lv)
        mine = [l for l in lv if level_open(l, skill, opened)]
        # cấp đang học: cấp mở cao nhất (đã mở bằng kiểm tra thì học tiếp ở đó)
        level = mine[-1] if mine else None
        if level is None:
            skills.append({"ky_nang": skill, "cap_do": None, "so_bai": 0, "da_xong": 0, "bai_tiep": None})
            continue
        s = summarize(build_map(db, uid, level["id"], skill))
        skills.append({"ky_nang": skill, "cap_do": {"id": level["id"], "ten": level["ten"]}, **s})
    return {**energy_and_kn(db, uid), "ky_nang": skills}


def skill_levels(db: Session, skill: str) -> list[dict]:
    """Cấp có kỹ năng này: Viết chỉ từ HSK 3 trở lên, các kỹ năng khác từ HSK 1."""
    return [l for l in levels(db) if l["thu_tu"] >= START_ORDER[skill]]


def skill_path(db: Session, uid: int, skill: str, cap_do_id: int | None) -> dict:
    from app.modules.practice.services import level_test_service  # tránh vòng import

    lv = skill_levels(db, skill)
    opened = opened_levels(db, uid, skill, lv)
    passed = level_tests(db, uid, skill)
    tabs = []
    for level in lv:
        is_open = level_open(level, skill, opened)
        info = {"id": level["id"], "ten": level["ten"], "mo": is_open}
        if is_open:
            info.update(summarize(build_map(db, uid, level["id"], skill)))
        tabs.append(info)
    chosen = next((l for l in lv if l["id"] == cap_do_id), None) if cap_do_id else None
    if chosen is None:
        mine = [l for l in lv if level_open(l, skill, opened)]
        chosen = mine[-1] if mine else (lv[0] if lv else None)
    chosen_open = bool(chosen) and level_open(chosen, skill, opened)
    if chosen_open:
        lands = build_map(db, uid, chosen["id"], skill)
    else:  # cấp chưa mở: vẫn cho xem trước các thửa, mọi ô khóa
        lands = [locked_preview(land) for land in build_map(db, 0, chosen["id"], skill)] if chosen else []
    test = None
    lands_for_test = lands if chosen_open else []
    if chosen:
        test = (level_test_service.stage_info(db, uid, skill, chosen, lv, lands_for_test, passed) if chosen_open
                else level_test_service.start_info(db, uid, skill, chosen, lv))
    return {
        **energy_and_kn(db, uid), "ky_nang": skill, "cap_do": chosen and {"id": chosen["id"], "ten": chosen["ten"], "mo": chosen_open},
        "cap": tabs, "thua": lands, "kiem_tra_cap": test,
        **({"bai_tiep": summarize(lands)["bai_tiep"]} if lands and chosen_open else {"bai_tiep": None}),
    }


def locked_preview(land: dict) -> dict:
    """Thửa của cấp chưa mở: giữ tên/mục tiêu để xem trước, mọi ô khóa, không có tiến độ."""
    slots = [o if o["trang_thai"] == "chua_xuat_ban" else {**o, "trang_thai": "khoa", "luot_dang_lam": None} for o in land["o"]]
    return {**land, "mo": False, "da_vuot": False, "thu_hoach": False, "o": slots}
