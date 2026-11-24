"""Hàm thuần chọn 'Bài phù hợp với bạn hôm nay' theo 5 mức ưu tiên (Mục 2.2 `docs/02_quy_tac_nghiep_vu.md` — MT02).

- Vai trò: Quyết định tất định bài học ôn luyện phù hợp nhất trong ngày từ Hồ sơ năng lực `kỹ năng × nhóm kiến thức`
  và danh sách bài đang mở của học viên, kèm câu giải thích bằng số liệu thật (`AT12, AT39, AT40, AT48–AT50, AT53`).
- Nguyên tắc thiết kế: Hàm thuần 100% (không truy cập CSDL, không gọi AI) để kiểm thử đơn vị độc lập trong mili-giây.
"""
from typing import Any

SKILL_ORDER = {"tu_vung": 0, "nghe": 1, "doc": 2, "viet": 3}
SKILL_VI = {"tu_vung": "Từ vựng", "nghe": "Nghe", "doc": "Đọc", "viet": "Viết"}

PRIORITY_LABELS = {
    1: "Ưu tiên 1 · Bù kiến thức nền còn thiếu",
    2: "Ưu tiên 2 · Khắc phục lỗi sai lặp lại",
    3: "Ưu tiên 3 · Luyện tự làm không cần gợi ý",
    4: "Ưu tiên 4 · Ôn nhắc lại chống quên",
    5: "Ưu tiên 5 · Bài mới phù hợp lộ trình",
}


def _lesson_tie_key(lesson: dict[str, Any], effective_target: int, match_score: int = 0) -> tuple:
    """Khóa sắp xếp phá hòa tất định theo đúng Mục 2.2:
    1) Điểm khớp nhóm kiến thức cao hơn
    2) Bài đang làm dở (`dang_lam`) -> chưa đạt (`chua_dat`) -> chưa học (`chua_hoc`) -> khác
    3) Cấp độ gần mục tiêu HSK nhất
    4) Thứ tự thửa và vị trí bài nhỏ hơn, rồi thứ tự kỹ năng chuẩn.
    """
    state_rank = {
        "dang_lam": 0,
        "chua_dat": 1,
        "chua_hoc": 2,
        "da_vuot": 3,
        "da_xong": 4,
    }.get(lesson.get("trang_thai", ""), 5)
    dist_target = abs(int(lesson.get("cap_thu_tu", 1)) - effective_target)
    return (
        -match_score,
        state_rank,
        dist_target,
        int(lesson.get("cap_thu_tu", 1)),
        int(lesson.get("so_thua") or 999),
        int(lesson.get("vi_tri") or 99),
        SKILL_ORDER.get(lesson.get("ky_nang", ""), 9),
        int(lesson.get("ma_goc_id", 0)),
    )


def _open_valid_lessons(candidate_lessons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """AT53: Loại bỏ tuyệt đối mọi bài bị khóa, chưa xuất bản, nháp hoặc đã ẩn."""
    valid = []
    for ls in candidate_lessons:
        if ls.get("loai", "bai") != "bai":
            continue
        if ls.get("trang_thai_dang", "da_dang") != "da_dang":
            continue
        if ls.get("trang_thai") in ("khoa", "chua_xuat_ban", None):
            continue
        valid.append(ls)
    return valid


def select_today_lesson(
    profile_groups: list[dict[str, Any]],
    target_level_order: int | None,
    candidate_lessons: list[dict[str, Any]],
    total_valid_answers: int = 0,
) -> dict[str, Any] | None:
    """Chọn đúng 1 bài học phù hợp nhất hôm nay theo 5 mức ưu tiên và trả kèm lý do số liệu thật (`AT49`)."""
    open_lessons = _open_valid_lessons(candidate_lessons)
    if not open_lessons:
        return None

    max_open_order = max(int(l.get("cap_thu_tu", 1)) for l in open_lessons)
    effective_target = min(target_level_order, max_open_order) if target_level_order else 1

    sparse_note = None
    if target_level_order is None or total_valid_answers < 3:
        sparse_note = (
            "Chưa có nhiều dữ liệu làm bài hoặc mục tiêu HSK, hệ thống đề xuất bài mở đầu phù hợp trong phạm vi đang mở."
        )

    unpassed_lessons = [l for l in open_lessons if l.get("trang_thai") != "da_xong"]

    # ------------------------------------------------------------------
    # ƯU TIÊN 1: Kiến thức nền còn thiếu (ở cấp <= mục tiêu)
    # - Nhóm kiến thức có >= 2 câu sai/bỏ qua và tỷ lệ tự làm đúng < 50% (AT39: 1 câu sai đơn lẻ chưa tính là yếu)
    # - Hoặc bài đang ở trạng thái `chua_dat` ở cấp <= mục tiêu
    # ------------------------------------------------------------------
    p1_groups = [
        g for g in profile_groups
        if int(g.get("cap_nhom_thu_tu", 1)) <= effective_target
        and int(g.get("tong", 0)) >= 2
        and (int(g.get("lam_sai", 0)) + int(g.get("bo_qua", 0))) >= 2
        and (int(g.get("tu_lam_dung", 0)) / int(g["tong"])) < 0.50
    ]
    p1_groups.sort(key=lambda g: (int(g.get("tu_lam_dung", 0)) / int(g["tong"]), -(int(g.get("lam_sai", 0)) + int(g.get("bo_qua", 0)))))

    for g in p1_groups:
        nid = int(g["nhom_kien_thuc_id"])
        pool = unpassed_lessons if unpassed_lessons else open_lessons
        matched = [
            l for l in pool
            if l.get("ky_nang") == g.get("ky_nang") and int((l.get("nhom_cau_count") or {}).get(nid, 0)) > 0
        ]
        if not matched:
            matched = [l for l in open_lessons if l.get("ky_nang") == g.get("ky_nang") and int((l.get("nhom_cau_count") or {}).get(nid, 0)) > 0]
        if matched:
            matched.sort(key=lambda l: _lesson_tie_key(l, effective_target, int((l.get("nhom_cau_count") or {}).get(nid, 0))))
            chosen = matched[0]
            err_cnt = int(g.get("lam_sai", 0)) + int(g.get("bo_qua", 0))
            pct_indep = round(100 * int(g.get("tu_lam_dung", 0)) / int(g["tong"]))
            return _format_choice(
                chosen,
                uu_tien=1,
                ly_do=f"Củng cố nhóm «{g['ten_nhom']}» ({SKILL_VI.get(g['ky_nang'], g['ky_nang'])}): bạn đang sai hoặc bỏ qua {err_cnt}/{g['tong']} câu ({pct_indep}% tự làm đúng).",
                nhom_kien_thuc=g["ten_nhom"],
                ghi_chu_du_lieu=None,
            )

    failed_lessons = [
        l for l in open_lessons
        if l.get("trang_thai") == "chua_dat" and int(l.get("cap_thu_tu", 1)) <= effective_target
    ]
    if failed_lessons:
        failed_lessons.sort(key=lambda l: _lesson_tie_key(l, effective_target, 0))
        chosen = failed_lessons[0]
        return _format_choice(
            chosen,
            uu_tien=1,
            ly_do=f"Bài này ở {chosen['ten_cap']} đang chưa đạt ở lượt làm trước — hoàn thành lại để nắm chắc nền tảng và mở bài kế tiếp.",
            nhom_kien_thuc=None,
            ghi_chu_du_lieu=None,
        )

    # ------------------------------------------------------------------
    # ƯU TIÊN 2: Lỗi sai lặp lại chưa đạt ngưỡng khắc phục (< 60% tự đúng - AT50)
    # ------------------------------------------------------------------
    p2_groups = []
    for g in profile_groups:
        tong = int(g.get("tong", 0))
        sai_gan = int(g.get("sai_gan_day", g.get("lam_sai", 0)))
        if tong < 2 or sai_gan < 2:
            continue
        recent_ratio = g.get("tu_dung_3_gan_nhat_ty_le")
        check_ratio = float(recent_ratio) if recent_ratio is not None else (int(g.get("tu_lam_dung", 0)) / tong)
        if check_ratio < 0.60:
            p2_groups.append((check_ratio, -sai_gan, g))
    p2_groups.sort(key=lambda x: (x[0], x[1]))

    for _, _, g in p2_groups:
        nid = int(g["nhom_kien_thuc_id"])
        pool = unpassed_lessons if unpassed_lessons else open_lessons
        matched = [
            l for l in pool
            if l.get("ky_nang") == g.get("ky_nang") and int((l.get("nhom_cau_count") or {}).get(nid, 0)) > 0
        ]
        if not matched:
            matched = [l for l in open_lessons if l.get("ky_nang") == g.get("ky_nang") and int((l.get("nhom_cau_count") or {}).get(nid, 0)) > 0]
        if matched:
            matched.sort(key=lambda l: _lesson_tie_key(l, effective_target, int((l.get("nhom_cau_count") or {}).get(nid, 0))))
            chosen = matched[0]
            sai_gan = int(g.get("sai_gan_day", g.get("lam_sai", 0)))
            return _format_choice(
                chosen,
                uu_tien=2,
                ly_do=f"Khắc phục lỗi lặp lại ở nhóm «{g['ten_nhom']}»: bạn đã làm sai {sai_gan} lần trong {g['tong']} câu gần đây.",
                nhom_kien_thuc=g["ten_nhom"],
                ghi_chu_du_lieu=None,
            )

    # ------------------------------------------------------------------
    # ƯU TIÊN 3: Làm đúng >= 60% nhưng phụ thuộc nhiều vào gợi ý / Hỏi Xiang (AT16)
    # ------------------------------------------------------------------
    p3_groups = []
    for g in profile_groups:
        tong = int(g.get("tong", 0))
        tu_dung = int(g.get("tu_lam_dung", 0))
        nho_ht = int(g.get("dung_nho_ho_tro", 0))
        tong_dung = tu_dung + nho_ht
        if tong < 2 or tong_dung == 0:
            continue
        if (tong_dung / tong) >= 0.60 and (nho_ht >= 2 or (tong >= 3 and (nho_ht / tong_dung) >= 0.50 and nho_ht >= 2)):
            p3_groups.append((-nho_ht, g))
    p3_groups.sort(key=lambda x: x[0])

    for _, g in p3_groups:
        nid = int(g["nhom_kien_thuc_id"])
        matched = [
            l for l in open_lessons
            if l.get("ky_nang") == g.get("ky_nang") and int((l.get("nhom_cau_count") or {}).get(nid, 0)) > 0
        ]
        if matched:
            matched.sort(key=lambda l: _lesson_tie_key(l, effective_target, int((l.get("nhom_cau_count") or {}).get(nid, 0))))
            chosen = matched[0]
            nho_ht = int(g["dung_nho_ho_tro"])
            tong_dung = int(g["tu_lam_dung"]) + nho_ht
            return _format_choice(
                chosen,
                uu_tien=3,
                ly_do=f"Tập tự làm chủ nhóm «{g['ten_nhom']}»: {nho_ht}/{tong_dung} câu đúng vừa qua cần mở gợi ý hoặc hỏi trợ giảng.",
                nhom_kien_thuc=g["ten_nhom"],
                ghi_chu_du_lieu=None,
            )

    # ------------------------------------------------------------------
    # ƯU TIÊN 4: Bài đã đạt nhưng có câu đến hạn Sổ tay hoặc cách đây >= 7 ngày
    # ------------------------------------------------------------------
    p4_lessons = [
        l for l in open_lessons
        if l.get("trang_thai") == "da_xong"
        and (int(l.get("so_cau_den_han") or 0) > 0 or (l.get("so_ngay_tu_lan_dat") is not None and int(l["so_ngay_tu_lan_dat"]) >= 7))
    ]
    if p4_lessons:
        p4_lessons.sort(
            key=lambda l: (
                -int(l.get("so_cau_den_han") or 0),
                -int(l.get("so_ngay_tu_lan_dat") or 0),
                _lesson_tie_key(l, effective_target, 0),
            )
        )
        chosen = p4_lessons[0]
        due_cnt = int(chosen.get("so_cau_den_han") or 0)
        days_ago = chosen.get("so_ngay_tu_lan_dat")
        if due_cnt > 0:
            reason = f"Bài này có {due_cnt} câu đang đến hạn củng cố trong Sổ tay câu sai hôm nay."
        else:
            reason = f"Đã {days_ago} ngày kể từ lần hoàn thành gần nhất — ôn ngắn để duy trì trí nhớ dài hạn."
        return _format_choice(chosen, uu_tien=4, ly_do=reason, nhom_kien_thuc=None, ghi_chu_du_lieu=None)

    # ------------------------------------------------------------------
    # ƯU TIÊN 5: Bài mới / đang làm dở trong phạm vi đã mở gần mục tiêu nhất (AT40)
    # ------------------------------------------------------------------
    p5_pool = [l for l in open_lessons if l.get("trang_thai") in ("dang_lam", "chua_hoc", "da_vuot")] or open_lessons
    p5_pool.sort(key=lambda l: _lesson_tie_key(l, effective_target, 0))
    chosen = p5_pool[0]
    if chosen.get("trang_thai") == "dang_lam":
        reason = f"Tiếp tục hoàn thành bài {chosen['ten_cap']} ({SKILL_VI.get(chosen['ky_nang'], chosen['ky_nang'])}) bạn đang làm dở."
    else:
        reason = f"Bài mới tiếp theo trong lộ trình {chosen['ten_cap']} ({SKILL_VI.get(chosen['ky_nang'], chosen['ky_nang'])}) đang mở cho bạn."
    return _format_choice(chosen, uu_tien=5, ly_do=reason, nhom_kien_thuc=None, ghi_chu_du_lieu=sparse_note)


def _format_choice(
    lesson: dict[str, Any],
    uu_tien: int,
    ly_do: str,
    nhom_kien_thuc: str | None,
    ghi_chu_du_lieu: str | None,
) -> dict[str, Any]:
    return {
        "uu_tien": uu_tien,
        "nhan_uu_tien": PRIORITY_LABELS[uu_tien],
        "ma_goc_id": int(lesson["ma_goc_id"]),
        "ten_bai": lesson["ten"],
        "ky_nang": lesson["ky_nang"],
        "ten_ky_nang": SKILL_VI.get(lesson["ky_nang"], lesson["ky_nang"]),
        "cap_do_id": int(lesson["cap_do_id"]),
        "ten_cap": lesson["ten_cap"],
        "ten_thua": lesson.get("ten_thua"),
        "vi_tri": lesson.get("vi_tri"),
        "so_cau": int(lesson.get("so_cau") or 5),
        "trang_thai": lesson.get("trang_thai"),
        "luot_dang_lam": lesson.get("luot_dang_lam"),
        "nhom_kien_thuc": nhom_kien_thuc,
        "ly_do": ly_do,
        "ghi_chu_du_lieu": ghi_chu_du_lieu,
    }
