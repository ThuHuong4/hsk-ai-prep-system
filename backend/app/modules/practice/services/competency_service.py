"""Dịch vụ tổng hợp Hồ sơ năng lực cá nhân hóa & gợi ý 'Bài phù hợp hôm nay' (Mục 2 `docs/02_quy_tac_nghiep_vu.md`).

- Vai trò: Đọc lịch sử trả lời thật từ CSDL (loại bỏ `loi_ky_thuat` và câu chưa chấm – AT38), phân loại 3 chiều
  (Tự làm đúng, Làm đúng nhờ hỗ trợ, Làm sai/Bỏ qua), gom nhóm theo `kỹ năng × nhóm kiến thức`, rồi ủy quyền cho
  hàm thuần `select_today_lesson()` chọn bài học tối ưu nhất hôm nay.
- Luồng gọi: `StudentHomePage.jsx` -> `practiceApi.getPersonalDashboard()` -> `GET /api/on-luyen/ho-so-ca-nhan` -> `competency_service.py`.
"""
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.sql_helpers import in_params
from app.modules.practice.services import path_view
from app.modules.practice.services.recommendation_rules import SKILL_VI, select_today_lesson


def _load_competency_matrix(db: Session, uid: int, level_order_by_id: dict[int, int]) -> tuple[list[dict], int]:
    """Đọc toàn bộ câu trả lời đã chốt của học viên trên các lượt `da_nop` (loại trừ `loi_ky_thuat` – AT38)."""
    rows = db.execute(
        text("""
            SELECT a.id AS cau_tra_loi_id, a.trang_thai_thao_tac, a.muc_goi_y, a.xac_nhan_luc,
                   q.ma_goc_id AS cau_goc_id, q.cap_do_id,
                   COALESCE(q.ky_nang, p.ky_nang) AS ky_nang,
                   q.dang, q.nguong_dat,
                   COALESCE(q.nhom_kien_thuc_id, p.nhom_kien_thuc_id) AS nhom_id,
                   nkt.ten AS ten_nhom,
                   v.diem,
                   l.nop_luc,
                   EXISTS(
                       SELECT 1 FROM hoi_thoai h
                       JOIN tin_nhan tm ON tm.hoi_thoai_id = h.id
                       WHERE h.cau_tra_loi_id = a.id
                         AND (a.xac_nhan_luc IS NULL OR tm.tao_luc <= a.xac_nhan_luc)
                   ) AS hoi_truoc_kiem_tra,
                   EXISTS(
                       SELECT 1 FROM cau_tra_loi prev
                       JOIN luot_lam pl ON pl.id = prev.luot_lam_id
                       JOIN cau_hoi pq ON pq.id = prev.cau_hoi_id
                       WHERE pl.nguoi_dung_id = l.nguoi_dung_id
                         AND pq.ma_goc_id = q.ma_goc_id
                         AND prev.id <> a.id
                         AND prev.xem_loi_giai_luc IS NOT NULL
                         AND DATE(prev.xem_loi_giai_luc) = DATE(COALESCE(a.xac_nhan_luc, l.nop_luc))
                         AND prev.xem_loi_giai_luc < COALESCE(a.xac_nhan_luc, l.nop_luc)
                   ) AS vua_xem_loi_giai_cung_ngay
            FROM cau_tra_loi a
            JOIN luot_lam l ON l.id = a.luot_lam_id
            JOIN cau_hoi q ON q.id = a.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            LEFT JOIN nhom_kien_thuc nkt ON nkt.id = COALESCE(q.nhom_kien_thuc_id, p.nhom_kien_thuc_id)
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE l.nguoi_dung_id = :u
              AND l.trang_thai = 'da_nop'
              AND a.trang_thai_thao_tac <> 'loi_ky_thuat'
            ORDER BY COALESCE(a.xac_nhan_luc, l.nop_luc) ASC, a.id ASC
        """),
        {"u": uid},
    ).mappings().all()

    buckets: dict[tuple[str, int], dict] = {}
    valid_count = 0

    for r in rows:
        tt = r["trang_thai_thao_tac"]
        diem = float(r["diem"]) if r["diem"] is not None else None
        # Bỏ qua câu chưa chấm xong (ví dụ câu viết đang chờ chấm) hoặc chưa thao tác không có điểm
        if tt == "chua_thao_tac" and diem is None:
            continue
        if tt == "da_tra_loi" and diem is None:
            continue

        valid_count += 1
        nhom_id = r["nhom_id"]
        ky_nang = r["ky_nang"]
        if not nhom_id or not ky_nang:
            continue

        pass_mark = float(r["nguong_dat"]) if r["dang"] in ("viet_mo", "dich_cau") and r["nguong_dat"] else 1.0
        is_right = tt == "da_tra_loi" and diem is not None and diem >= pass_mark
        used_support = int(r["muc_goi_y"] or 0) > 0 or bool(r["hoi_truoc_kiem_tra"]) or bool(r["vua_xem_loi_giai_cung_ngay"])

        key = (ky_nang, int(nhom_id))
        cap_ord = level_order_by_id.get(int(r["cap_do_id"]), 1) if r["cap_do_id"] else 1
        b = buckets.setdefault(key, {
            "ky_nang": ky_nang,
            "ten_ky_nang": SKILL_VI.get(ky_nang, ky_nang),
            "nhom_kien_thuc_id": int(nhom_id),
            "ten_nhom": r["ten_nhom"] or f"Nhóm #{nhom_id}",
            "cap_nhom_thu_tu": cap_ord,
            "tong": 0,
            "tu_lam_dung": 0,
            "dung_nho_ho_tro": 0,
            "lam_sai": 0,
            "bo_qua": 0,
            "_history": [],  # lưu ('tu_dung' | 'ho_tro' | 'sai' | 'bo_qua') theo trình tự thời gian
        })
        b["cap_nhom_thu_tu"] = min(b["cap_nhom_thu_tu"], cap_ord)
        b["tong"] += 1
        if tt == "bo_qua":
            b["bo_qua"] += 1
            b["_history"].append("bo_qua")
        elif is_right:
            if used_support:
                b["dung_nho_ho_tro"] += 1
                b["_history"].append("ho_tro")
            else:
                b["tu_lam_dung"] += 1
                b["_history"].append("tu_dung")
        else:
            b["lam_sai"] += 1
            b["_history"].append("sai")

    groups = []
    for b in buckets.values():
        hist = b.pop("_history")
        recent_window = hist[-6:]
        b["sai_gan_day"] = sum(1 for x in recent_window if x == "sai")
        if len(hist) >= 3:
            last3 = hist[-3:]
            b["tu_dung_3_gan_nhat_ty_le"] = round(sum(1 for x in last3 if x == "tu_dung") / len(last3), 3)
        else:
            b["tu_dung_3_gan_nhat_ty_le"] = None
        groups.append(b)

    return groups, valid_count


def _collect_open_candidate_lessons(db: Session, uid: int, all_levels: list[dict]) -> list[dict]:
    """Thu thập toàn bộ bài ôn thường (`loai = 'bai'`) đã xuất bản và đang mở khóa với học viên (`AT53`)."""
    candidates: list[dict] = []
    root_ids: list[int] = []

    for skill in ("tu_vung", "nghe", "doc", "viet"):
        opened = path_view.opened_levels(db, uid, skill, all_levels)
        for lv in all_levels:
            if not path_view.level_open(lv, skill, opened):
                continue
            lands = path_view.build_map(db, uid, lv["id"], skill)
            for land in lands:
                if not land.get("mo"):
                    continue
                for slot in land["o"]:
                    if slot.get("loai") != "bai":
                        continue
                    if slot.get("trang_thai") in ("khoa", "chua_xuat_ban", None):
                        continue
                    root_id = int(slot["ma_goc_id"])
                    root_ids.append(root_id)
                    candidates.append({
                        "ma_goc_id": root_id,
                        "loai": "bai",
                        "trang_thai_dang": "da_dang",
                        "ten": slot["ten"],
                        "ky_nang": skill,
                        "cap_do_id": int(lv["id"]),
                        "ten_cap": lv["ten"],
                        "cap_thu_tu": int(lv["thu_tu"]),
                        "ten_thua": land["ten"],
                        "so_thua": land.get("so_thu_tu") or 999,
                        "vi_tri": slot["vi_tri"],
                        "so_cau": int(slot.get("so_cau") or 5),
                        "trang_thai": slot["trang_thai"],
                        "luot_dang_lam": slot.get("luot_dang_lam"),
                        "nhom_cau_count": {},
                        "so_cau_den_han": 0,
                        "so_ngay_tu_lan_dat": None,
                    })

    if not root_ids:
        return []

    marks, params = in_params("r", list(set(root_ids)))

    # Đếm phân bố `nhom_kien_thuc_id` của từng bài `da_dang` và số câu đang đến hạn trong Sổ tay
    q_rows = db.execute(
        text(f"""
            SELECT b.ma_goc_id,
                   COALESCE(q.nhom_kien_thuc_id, p.nhom_kien_thuc_id) AS nhom_id,
                   q.ma_goc_id AS cau_goc_id
            FROM bo_de b
            JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id AND i.la_cau_vi_du = 0
            JOIN cau_hoi q ON q.id = i.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            WHERE b.ma_goc_id IN ({marks}) AND b.loai = 'bai' AND b.trang_thai = 'da_dang'
        """),
        params,
    ).mappings().all()

    due_roots = set(
        int(x)
        for x in db.execute(
            text("""
                SELECT cau_hoi_goc_id
                FROM so_tay
                WHERE nguoi_dung_id = :u AND trang_thai <> 'da_cung_co'
                  AND (han_on IS NULL OR han_on <= CURDATE())
            """),
            {"u": uid},
        ).scalars().all()
    )

    nhom_by_lesson: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    due_by_lesson: dict[int, int] = defaultdict(int)
    for r in q_rows:
        lroot = int(r["ma_goc_id"])
        if r["nhom_id"] is not None:
            nhom_by_lesson[lroot][int(r["nhom_id"])] += 1
        if int(r["cau_goc_id"]) in due_roots:
            due_by_lesson[lroot] += 1

    # Tính số ngày từ lần nộp gần nhất cho các bài đã xong
    done_rows = db.execute(
        text(f"""
            SELECT b.ma_goc_id, DATEDIFF(CURDATE(), MAX(DATE(l.nop_luc))) AS so_ngay
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.nguoi_dung_id = :u AND b.ma_goc_id IN ({marks}) AND l.trang_thai = 'da_nop'
            GROUP BY b.ma_goc_id
        """),
        {"u": uid, **params},
    ).mappings().all()
    days_by_lesson = {int(r["ma_goc_id"]): int(r["so_ngay"]) for r in done_rows if r["so_ngay"] is not None}

    for c in candidates:
        lid = c["ma_goc_id"]
        c["nhom_cau_count"] = dict(nhom_by_lesson.get(lid, {}))
        c["so_cau_den_han"] = int(due_by_lesson.get(lid, 0))
        if c["trang_thai"] == "da_xong":
            c["so_ngay_tu_lan_dat"] = days_by_lesson.get(lid)

    return candidates


def get_personal_dashboard(db: Session, uid: int) -> dict:
    """Trả dữ liệu Bảng điều khiển Cá nhân hóa duy nhất cho Trang chủ Học viên (không trùng lặp dữ liệu thừa)."""
    all_levels = path_view.levels(db)
    level_by_id = {int(l["id"]): l for l in all_levels}
    level_order_by_id = {int(l["id"]): int(l["thu_tu"]) for l in all_levels}

    user_row = db.execute(
        text("SELECT ks_cap_muc_tieu_id, ks_phut_moi_ngay FROM nguoi_dung WHERE id = :u"),
        {"u": uid},
    ).mappings().one()
    target_cap_id = int(user_row["ks_cap_muc_tieu_id"]) if user_row["ks_cap_muc_tieu_id"] else None
    target_lv = level_by_id.get(target_cap_id) if target_cap_id else None
    target_order = int(target_lv["thu_tu"]) if target_lv else None

    placement_row = db.execute(
        text("""
            SELECT l.id AS luot_id, k.cap_de_xuat_id, cd.ten AS ten_cap_de_xuat
            FROM ket_qua_dau_vao k
            JOIN luot_lam l ON l.id = k.luot_lam_id
            LEFT JOIN cap_do cd ON cd.id = k.cap_de_xuat_id
            WHERE l.nguoi_dung_id = :u AND k.trang_thai_phan_tich = 'xong'
            ORDER BY l.id DESC LIMIT 1
        """),
        {"u": uid},
    ).mappings().first()

    # Nếu chưa lưu mục tiêu riêng nhưng đã có cấp đề xuất từ Đánh giá đầu vào -> dùng làm mốc định hướng
    effective_target_order = target_order
    if effective_target_order is None and placement_row and placement_row["cap_de_xuat_id"]:
        effective_target_order = level_order_by_id.get(int(placement_row["cap_de_xuat_id"]))

    profile_groups, total_valid_answers = _load_competency_matrix(db, uid, level_order_by_id)
    candidates = _collect_open_candidate_lessons(db, uid, all_levels)
    trinh_do = path_view.current_proficiency(db, uid, all_levels)
    max_unlocked_ord = int(trinh_do["thu_tu"]) if trinh_do else 1
    cac_cap_da_mo = [l["ten"] for l in all_levels if int(l["thu_tu"]) <= max_unlocked_ord]
    cac_cap_dang_khoa = [l["ten"] for l in all_levels if int(l["thu_tu"]) > max_unlocked_ord]

    # Tách nhóm Điểm cần ưu tiên cải thiện và Điểm mạnh từ quá trình luyện tập
    weak_spots = []
    strengths = []
    mastered_keys: set[tuple[str, int]] = set()
    seen_weak_keys: set[tuple[str, int | None]] = set()

    for g in profile_groups:
        tong = g["tong"]
        if tong < 2:
            continue
        err_cnt = g["lam_sai"] + g["bo_qua"]
        indep_pct = round(100 * g["tu_lam_dung"] / tong)
        if err_cnt >= 2 and indep_pct < 60:
            seen_weak_keys.add((g["ky_nang"], g["nhom_kien_thuc_id"]))
            weak_spots.append({
                "ky_nang": g["ky_nang"],
                "ten_ky_nang": g["ten_ky_nang"],
                "nhom_kien_thuc_id": g["nhom_kien_thuc_id"],
                "ten_nhom": g["ten_nhom"],
                "loai": "loi_kien_thuc",
                "mo_ta": f"Sai/bỏ qua {err_cnt}/{tong} câu · {indep_pct}% tự làm đúng",
                "phan_tich_ai": None,
                "muc_do": err_cnt + 2,
            })
        elif g["dung_nho_ho_tro"] >= 2 and indep_pct < 60:
            seen_weak_keys.add((g["ky_nang"], g["nhom_kien_thuc_id"]))
            weak_spots.append({
                "ky_nang": g["ky_nang"],
                "ten_ky_nang": g["ten_ky_nang"],
                "nhom_kien_thuc_id": g["nhom_kien_thuc_id"],
                "ten_nhom": g["ten_nhom"],
                "loai": "can_goi_y",
                "mo_ta": f"Đúng nhờ gợi ý/hỏi đáp {g['dung_nho_ho_tro']}/{tong} câu",
                "phan_tich_ai": None,
                "muc_do": g["dung_nho_ho_tro"],
            })
        elif indep_pct >= 75:
            mastered_keys.add((g["ky_nang"], g["nhom_kien_thuc_id"]))
            strengths.append({
                "ky_nang": g["ky_nang"],
                "ten_ky_nang": g["ten_ky_nang"],
                "ten_nhom": g["ten_nhom"],
                "mo_ta": f"Tự làm đúng {g['tu_lam_dung']}/{tong} câu ({indep_pct}%)",
                "ty_le": indep_pct,
            })

    # Nối trực tiếp các điểm yếu AI vừa phát hiện trong bài Khảo sát đánh giá 8 câu (nếu học viên chưa khắc phục xong)
    if placement_row:
        pl_rows = db.execute(
            text("""
                SELECT a.thu_tu, a.trang_thai_thao_tac, q.ky_nang, q.dang, q.nguong_dat,
                       q.nhom_kien_thuc_id, nkt.ten AS ten_nhom, cd.ten AS ten_cap,
                       v.diem, v.nhan_xet
                FROM cau_tra_loi a
                JOIN cau_hoi q ON q.id = a.cau_hoi_id
                LEFT JOIN nhom_kien_thuc nkt ON nkt.id = q.nhom_kien_thuc_id
                LEFT JOIN cap_do cd ON cd.id = q.cap_do_id
                LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l AND a.trang_thai_thao_tac <> 'loi_ky_thuat'
                ORDER BY a.thu_tu
            """),
            {"l": int(placement_row["luot_id"])},
        ).mappings().all()
        for r in pl_rows:
            pass_mark = float(r["nguong_dat"] or 6.0) if r["dang"] in ("viet_mo", "dich_cau") else 1.0
            is_right = r["trang_thai_thao_tac"] == "da_tra_loi" and r["diem"] is not None and float(r["diem"]) >= pass_mark
            if is_right:
                continue
            kn = r["ky_nang"]
            nid = int(r["nhom_kien_thuc_id"]) if r["nhom_kien_thuc_id"] else None
            if nid and (kn, nid) in mastered_keys:
                continue
            if (kn, nid) in seen_weak_keys:
                continue
            seen_weak_keys.add((kn, nid))
            act_txt = "chưa biết (đã bỏ qua)" if r["trang_thai_thao_tac"] == "bo_qua" else "trả lời chưa đúng"
            weak_spots.append({
                "ky_nang": kn,
                "ten_ky_nang": SKILL_VI.get(kn, kn),
                "nhom_kien_thuc_id": nid,
                "ten_nhom": r["ten_nhom"] or SKILL_VI.get(kn, kn),
                "loai": "khao_sat_dau_vao",
                "mo_ta": f"Câu {r['thu_tu']}/8 khảo sát ({r['ten_cap'] or 'HSK'}) — {act_txt}",
                "phan_tich_ai": r["nhan_xet"],
                "muc_do": 2 if r["trang_thai_thao_tac"] == "bo_qua" else 3,
            })

    weak_spots.sort(key=lambda x: -x["muc_do"])
    strengths.sort(key=lambda x: -x["ty_le"])

    # Ghép danh sách bài ôn ưu tiên bám sát đúng từng điểm yếu phát hiện được (chỉ lấy bài đang mở và chưa xong)
    unpassed_open = [c for c in candidates if c["trang_thai"] != "da_xong"] or candidates
    prioritized_lessons: list[dict] = []
    used_lesson_roots: set[int] = set()

    for w in weak_spots:
        nid = w.get("nhom_kien_thuc_id")
        kn = w["ky_nang"]
        matches = [
            c for c in unpassed_open
            if c["ma_goc_id"] not in used_lesson_roots
            and c["ky_nang"] == kn
            and (nid is not None and int((c.get("nhom_cau_count") or {}).get(nid, 0)) > 0)
        ]
        if not matches:
            matches = [c for c in unpassed_open if c["ma_goc_id"] not in used_lesson_roots and c["ky_nang"] == kn]
        if not matches:
            w["bai_on_khac_phuc"] = None
            continue
        matches.sort(key=lambda c: (-int((c.get("nhom_cau_count") or {}).get(nid or -1, 0)), -c["cap_thu_tu"], c["so_thua"], c["vi_tri"]))
        picked = matches[0]
        lesson_info = {
            "ma_goc_id": picked["ma_goc_id"],
            "ten_bai": picked["ten"],
            "ky_nang": picked["ky_nang"],
            "ten_ky_nang": SKILL_VI.get(picked["ky_nang"], picked["ky_nang"]),
            "cap_do_id": picked["cap_do_id"],
            "ten_cap": picked["ten_cap"],
            "ten_thua": picked["ten_thua"],
            "trang_thai": picked["trang_thai"],
            "luot_dang_lam": picked["luot_dang_lam"],
            "diem_yeu_muc_tieu": w["ten_nhom"],
            "ly_do": f"Ưu tiên bù điểm yếu «{w['ten_nhom']}» ({w['mo_ta']}).",
        }
        w["bai_on_khac_phuc"] = lesson_info
        if len(prioritized_lessons) < 4:
            used_lesson_roots.add(picked["ma_goc_id"])
            prioritized_lessons.append(lesson_info)

    # Tính thanh chỉ số năng lực 4 kỹ năng (Từ vựng, Nghe, Đọc, Viết) để trực quan hóa kiểu WriteMate Studio
    skill_totals: dict[str, dict[str, int]] = {
        sk: {"tong": 0, "dung": 0, "yeu": 0} for sk in ("tu_vung", "nghe", "doc", "viet")
    }
    for g in profile_groups:
        sk = g["ky_nang"]
        if sk in skill_totals:
            skill_totals[sk]["tong"] += int(g["tong"])
            skill_totals[sk]["dung"] += int(g["tu_lam_dung"]) + int(g["dung_nho_ho_tro"])
            skill_totals[sk]["yeu"] += int(g["lam_sai"]) + int(g["bo_qua"])

    ky_nang_4_chieu = []
    weak_skill_set = {w["ky_nang"] for w in weak_spots}
    for sk in ("tu_vung", "nghe", "doc", "viet"):
        st = skill_totals[sk]
        pct = round(100 * st["dung"] / st["tong"]) if st["tong"] > 0 else 0
        if st["tong"] == 0:
            nhan = "Mới mở"
        elif sk in weak_skill_set and pct < 70:
            nhan = "Cần ưu tiên bù"
        elif pct >= 75:
            nhan = "Nắm vững"
        else:
            nhan = "Đang củng cố"
        ky_nang_4_chieu.append({
            "ky_nang": sk,
            "ten_ky_nang": SKILL_VI.get(sk, sk),
            "so_cau_da_lam": st["tong"],
            "so_cau_dung": st["dung"],
            "ty_le_vung": pct,
            "trang_thai_nhan": nhan,
        })

    today_lesson = select_today_lesson(profile_groups, effective_target_order, candidates, total_valid_answers)
    # Nếu mới hoàn thành khảo sát 8 câu (select_today_lesson rơi vào Ưu tiên 5 chung) mà có bài khớp thẳng điểm yếu -> ưu tiên bài điểm yếu lên đầu!
    if prioritized_lessons and (today_lesson is None or today_lesson.get("uu_tien") == 5):
        top_w = prioritized_lessons[0]
        today_lesson = {
            "uu_tien": 1,
            "nhan_uu_tien": "Ưu tiên theo điểm yếu khảo sát đánh giá",
            "ma_goc_id": top_w["ma_goc_id"],
            "ten_bai": top_w["ten_bai"],
            "ky_nang": top_w["ky_nang"],
            "ten_ky_nang": top_w["ten_ky_nang"],
            "cap_do_id": top_w["cap_do_id"],
            "ten_cap": top_w["ten_cap"],
            "ten_thua": top_w["ten_thua"],
            "vi_tri": None,
            "so_cau": 5,
            "trang_thai": top_w["trang_thai"],
            "luot_dang_lam": top_w["luot_dang_lam"],
            "nhom_kien_thuc": top_w["diem_yeu_muc_tieu"],
            "ly_do": top_w["ly_do"],
            "ghi_chu_du_lieu": None,
        }

    # Đếm nhanh Sổ tay đến hạn
    nb_row = db.execute(
        text("""
            SELECT
                SUM(CASE WHEN trang_thai <> 'da_cung_co' AND (han_on IS NULL OR han_on <= CURDATE()) THEN 1 ELSE 0 END) AS den_han,
                SUM(CASE WHEN trang_thai IN ('can_on', 'cho_on_lai') THEN 1 ELSE 0 END) AS chua_cung_co,
                SUM(CASE WHEN trang_thai = 'da_cung_co' THEN 1 ELSE 0 END) AS da_cung_co
            FROM so_tay WHERE nguoi_dung_id = :u
        """),
        {"u": uid},
    ).mappings().one()

    # Phiên Thi thử đang làm dở còn giờ (nếu có)
    open_exam = db.execute(
        text("""
            SELECT l.id AS luot_id, cd.ten AS ten_cap_do,
                   TIMESTAMPDIFF(SECOND, NOW(), l.bat_dau_luc + INTERVAL b.thoi_luong_phut MINUTE) AS con_lai_giay
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND l.trang_thai = 'dang_lam'
            HAVING con_lai_giay > 0
            ORDER BY l.id DESC LIMIT 1
        """),
        {"u": uid},
    ).mappings().first()

    # Đọc các nhận định tổng hợp của AI từ bài đánh giá đầu vào (để hiện rõ khối Phân tích AI ngay trên Trang chủ)
    nhan_dinh_ai = []
    if placement_row:
        nd_rows = db.execute(
            text("""
                SELECT nd.thu_tu, nd.ky_nang, nkt.ten AS ten_nhom, nd.loai, nd.noi_dung
                FROM nhan_dinh_dau_vao nd
                LEFT JOIN nhom_kien_thuc nkt ON nkt.id = nd.nhom_kien_thuc_id
                WHERE nd.luot_lam_id = :l
                ORDER BY nd.thu_tu
            """),
            {"l": int(placement_row["luot_id"])},
        ).mappings().all()
        nhan_dinh_ai = [
            {
                "thu_tu": int(r["thu_tu"]),
                "ky_nang": r["ky_nang"],
                "ten_ky_nang": SKILL_VI.get(r["ky_nang"], r["ky_nang"]) if r["ky_nang"] else "Tổng quan",
                "ten_nhom": r["ten_nhom"],
                "loai": r["loai"],
                "noi_dung": r["noi_dung"],
            }
            for r in nd_rows
        ]

    db.rollback()
    return {
        "trinh_do_hien_tai": {
            **(trinh_do or {"id": 1, "ma": "HSK1", "ten": "HSK 1", "thu_tu": 1}),
            "cac_cap_da_mo": cac_cap_da_mo,
            "cac_cap_dang_khoa": cac_cap_dang_khoa,
        },
        "bai_hom_nay": today_lesson,
        "bai_on_uu_tien": prioritized_lessons,
        "ho_so_nang_luc": {
            "tong_cau_da_phan_tich": total_valid_answers,
            "nhan_dinh_ai": nhan_dinh_ai,
            "ky_nang_4_chieu": ky_nang_4_chieu,
            "diem_can_cai_thien": weak_spots[:5],
            "diem_manh": strengths[:4],
        },
        "muc_tieu": {
            "cap_muc_tieu_id": target_cap_id,
            "ten_cap_muc_tieu": target_lv["ten"] if target_lv else None,
            "phut_moi_ngay": int(user_row["ks_phut_moi_ngay"]) if user_row["ks_phut_moi_ngay"] else None,
            "danh_sach_cap": all_levels,
        },
        "dau_vao_gan_nhat": dict(placement_row) if placement_row else None,
        "so_tay": {
            "den_han": int(nb_row["den_han"] or 0),
            "chua_cung_co": int(nb_row["chua_cung_co"] or 0),
            "da_cung_co": int(nb_row["da_cung_co"] or 0),
        },
        "luot_thi_dang_lam": dict(open_exam) if open_exam else None,
    }
