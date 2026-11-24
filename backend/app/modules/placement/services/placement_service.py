"""Điều phối phiên Đánh giá trình độ đầu vào thích ứng 8 câu (Mục 1 nghiệp vụ bổ sung).

- Vai trò:
  1) Kiểm tra cổng phân luồng Ưu tiên 1–4 khi Học viên vào hệ thống (`entry_gate`).
  2) Mở hoặc khôi phục phiên 8 câu đang làm dở (`start_placement`, `get_session`).
  3) Nhận câu trả lời / Bỏ qua từng câu, chấm ngay các câu khách quan, tính nhánh thích ứng cho câu kế tiếp (`submit_step`).
  4) Xử lý đổi câu tại chỗ khi lỗi âm thanh / hình ảnh và ghi vết `lich_su_thay_cau` (`replace_broken_question`).
  5) Lưu mục tiêu cấp HSK tùy chọn của học viên vào `nguoi_dung.ks_cap_muc_tieu_id` (`save_target_level`).
- Bảng CSDL tác động: `luot_lam`, `cau_tra_loi`, `ket_qua_cham`, `lich_su_thay_cau`, `ket_qua_dau_vao`, `nguoi_dung`.
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.common.sql_helpers import in_params
from app.modules.grading import (
    CHOICE_TYPES,
    OBJECTIVE_TYPES,
    is_correct,
    load_questions_by_ids,
    shuffle_choice_options,
)
from app.modules.placement.services.adaptive_rules import (
    SLOT_SPEC,
    compute_slot_target_order,
    fallback_level_orders,
)

TOTAL_QUESTIONS = 8


def _levels_by_order(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text("SELECT id, ma, ten, thu_tu FROM cap_do WHERE trang_thai = 'da_dang' ORDER BY thu_tu")
    ).mappings().all()
    return {int(r["thu_tu"]): dict(r) for r in rows}


def _levels_by_id(db: Session) -> dict[int, dict]:
    rows = db.execute(text("SELECT id, ma, ten, thu_tu FROM cap_do ORDER BY thu_tu")).mappings().all()
    return {int(r["id"]): dict(r) for r in rows}


def has_learning_progress(db: Session, uid: int) -> bool:
    """Ưu tiên 1: Học viên đã có ít nhất 1 lượt học/ôn/vượt/thi thử hợp lệ (không tính đánh giá đầu vào)."""
    row = db.execute(
        text("""
            SELECT 1
            FROM luot_lam l
            LEFT JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.nguoi_dung_id = :u
              AND l.trang_thai = 'da_nop'
              AND COALESCE(l.loai_boc_cau, '') <> 'danh_gia_dau_vao'
              AND (
                b.loai IN ('bai', 'cuoi_thua')
                OR l.ap_dung_luc IS NOT NULL
                OR l.loai_boc_cau = 'so_tay'
                OR EXISTS (
                    SELECT 1 FROM cau_tra_loi a
                    WHERE a.luot_lam_id = l.id AND a.trang_thai_thao_tac = 'da_tra_loi'
                )
              )
            LIMIT 1
        """),
        {"u": uid},
    ).first()
    return row is not None


def entry_gate(db: Session, uid: int) -> dict:
    """Cổng bắt buộc 1 lần cho Học viên:
    - Chưa hoàn tất bài Đánh giá đầu vào 8 câu + AI phân tích -> bắt buộc đưa vào bài đánh giá / màn phân tích.
    - Đã hoàn tất phân tích ('xong') -> mở toàn bộ hệ thống theo cấp trình độ đã đánh giá, không làm lại bài 8 câu nữa.
    """
    open_luot_id = db.execute(
        text("""
            SELECT id FROM luot_lam
            WHERE nguoi_dung_id = :u AND loai_boc_cau = 'danh_gia_dau_vao' AND trang_thai = 'dang_lam'
            ORDER BY id DESC LIMIT 1
        """),
        {"u": uid},
    ).scalar_one_or_none()

    latest_done = db.execute(
        text("""
            SELECT l.id AS luot_id, l.nop_luc,
                   COALESCE(k.trang_thai_phan_tich, 'chua') AS trang_thai_phan_tich,
                   k.cap_de_xuat_id, cd.ten AS ten_cap_de_xuat
            FROM luot_lam l
            LEFT JOIN ket_qua_dau_vao k ON k.luot_lam_id = l.id
            LEFT JOIN cap_do cd ON cd.id = k.cap_de_xuat_id
            WHERE l.nguoi_dung_id = :u AND l.loai_boc_cau = 'danh_gia_dau_vao' AND l.trang_thai = 'da_nop'
            ORDER BY l.id DESC LIMIT 1
        """),
        {"u": uid},
    ).mappings().first()

    target_row = db.execute(
        text("SELECT ks_cap_muc_tieu_id FROM nguoi_dung WHERE id = :u"),
        {"u": uid},
    ).mappings().first()
    cap_muc_tieu_id = target_row["ks_cap_muc_tieu_id"] if target_row else None

    if latest_done:
        st = latest_done["trang_thai_phan_tich"]
        is_completed = st == "xong"
        redirect = None if is_completed else f"/danh-gia-dau-vao/lam-bai/{int(latest_done['luot_id'])}"
        return {
            "uu_tien": 1 if is_completed else 2,
            "da_danh_gia_xong": is_completed,
            "tu_dong_chuyen_huong": redirect,
            "da_co_tien_do": is_completed,
            "luot_dang_lam_id": None,
            "ket_qua_gan_nhat": dict(latest_done),
            "cap_muc_tieu_id": cap_muc_tieu_id,
        }

    if open_luot_id:
        return {
            "uu_tien": 3,
            "da_danh_gia_xong": False,
            "tu_dong_chuyen_huong": f"/danh-gia-dau-vao/lam-bai/{int(open_luot_id)}",
            "da_co_tien_do": False,
            "luot_dang_lam_id": int(open_luot_id),
            "ket_qua_gan_nhat": None,
            "cap_muc_tieu_id": cap_muc_tieu_id,
        }

    return {
        "uu_tien": 4,
        "da_danh_gia_xong": False,
        "tu_dong_chuyen_huong": "/danh-gia-dau-vao",
        "da_co_tien_do": False,
        "luot_dang_lam_id": None,
        "ket_qua_gan_nhat": None,
        "cap_muc_tieu_id": cap_muc_tieu_id,
    }


def _used_question_ids(db: Session, luot_id: int) -> set[int]:
    """Tập hợp toàn bộ câu hỏi đã xuất hiện trong phiên (cả câu đang giữ và câu đã bị thay do lỗi kỹ thuật)."""
    used = {
        int(r[0])
        for r in db.execute(text("SELECT cau_hoi_id FROM cau_tra_loi WHERE luot_lam_id = :l"), {"l": luot_id}).all()
    }
    for cu, moi in db.execute(
        text("SELECT cau_hoi_cu_id, cau_hoi_moi_id FROM lich_su_thay_cau WHERE luot_lam_id = :l"),
        {"l": luot_id},
    ).all():
        used.add(int(cu))
        used.add(int(moi))
    return used


def _pick_question_for_slot(
    db: Session,
    slot_pos: int,
    target_order: int,
    levels_map: dict[int, dict],
    used_ids: set[int],
) -> tuple[int, int]:
    """Rút ngẫu nhiên 1 câu hợp lệ cho vị trí `slot_pos`, trả về `(cau_hoi_id, cap_tham_do_id)`.

    Thử lần lượt theo `fallback_level_orders(target_order)` (AT47).
    Nếu cả dải HSK 1–4 đều hết câu phù hợp thì ném `RuleError` rõ ràng.
    """
    spec = SLOT_SPEC[slot_pos]
    dang_marks, dang_params = in_params("d", list(spec["dang"]))
    audio_clause = "AND q.tep_audio IS NOT NULL" if spec["require_audio"] else ""
    max_order = max(levels_map) if levels_map else 4
    target_cap = levels_map.get(target_order) or next(iter(levels_map.values()))

    for try_order in fallback_level_orders(target_order, max_order):
        lv = levels_map.get(try_order)
        if not lv:
            continue
        rows = db.execute(
            text(f"""
                SELECT q.id
                FROM cau_hoi q
                WHERE q.trang_thai = 'da_dang'
                  AND q.dung_dau_vao = 1
                  AND q.cau_cha_id IS NULL
                  AND q.cap_do_id = :cap
                  AND q.ky_nang = :kn
                  AND q.dang IN ({dang_marks})
                  {audio_clause}
            """),
            {"cap": lv["id"], "kn": spec["ky_nang"], **dang_params},
        ).scalars().all()
        candidates = [int(qid) for qid in rows if int(qid) not in used_ids]
        if candidates:
            picked = random.SystemRandom().choice(candidates)
            return picked, int(target_cap["id"])

    raise RuleError("Ngân hàng câu hỏi hiện chưa đủ học liệu cho bài đánh giá đầu vào. Bạn có thể vào học ngay từ HSK 1.")


def _prior_outcomes(db: Session, luot_id: int, levels_by_id: dict[int, dict]) -> dict[int, dict]:
    rows = db.execute(
        text("""
            SELECT a.thu_tu, a.trang_thai_thao_tac, a.cap_tham_do_id, q.cap_do_id AS cap_thuc_te_id,
                   q.dang, q.nguong_dat, v.diem
            FROM cau_tra_loi a
            JOIN cau_hoi q ON q.id = a.cau_hoi_id
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE a.luot_lam_id = :l
            ORDER BY a.thu_tu
        """),
        {"l": luot_id},
    ).mappings().all()
    out: dict[int, dict] = {}
    for r in rows:
        pass_mark = float(r["nguong_dat"]) if r["dang"] in ("viet_mo", "dich_cau") and r["nguong_dat"] else 1.0
        dung = r["diem"] is not None and float(r["diem"]) >= pass_mark
        target_lv = levels_by_id.get(int(r["cap_tham_do_id"])) if r["cap_tham_do_id"] else None
        actual_lv = levels_by_id.get(int(r["cap_thuc_te_id"])) if r["cap_thuc_te_id"] else None
        out[int(r["thu_tu"])] = {
            "trang_thai_thao_tac": r["trang_thai_thao_tac"],
            "dung": dung,
            "cap_muc_tieu_thu_tu": target_lv["thu_tu"] if target_lv else 2,
            "cap_thuc_te_thu_tu": actual_lv["thu_tu"] if actual_lv else 1,
        }
    return out


def start_placement(db: Session, uid: int) -> int:
    """Mở phiên đánh giá đầu vào 8 câu duy nhất lần đầu hoặc trả lại phiên đang làm dở (F5 giữ nguyên câu).
    Nếu học viên đã hoàn thành bài đánh giá đầu vào 1 lần trước đó thì từ chối tạo lượt mới (tránh làm lại nhiều lần để mở tắt cấp cao)."""
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        already_done = db.execute(
            text("""
                SELECT id FROM luot_lam
                WHERE nguoi_dung_id = :u AND loai_boc_cau = 'danh_gia_dau_vao' AND trang_thai = 'da_nop'
                LIMIT 1
            """),
            {"u": uid},
        ).scalar_one_or_none()
        if already_done:
            raise ConflictError(
                "Bài Đánh giá trình độ đầu vào 8 câu chỉ làm 1 lần khi bắt đầu. Bạn hãy học theo lộ trình hoặc thi Vượt cấp để nâng trình độ."
            )

        open_id = db.execute(
            text("""
                SELECT id FROM luot_lam
                WHERE nguoi_dung_id = :u AND loai_boc_cau = 'danh_gia_dau_vao' AND trang_thai = 'dang_lam'
                ORDER BY id DESC LIMIT 1
            """),
            {"u": uid},
        ).scalar_one_or_none()
        if open_id:
            db.commit()
            return int(open_id)

        levels_map = _levels_by_order(db)
        if not levels_map:
            raise RuleError("Chưa có cấp độ HSK nào được xuất bản")

        q1_id, cap_tham_do_id = _pick_question_for_slot(db, 1, 2, levels_map, set())
        res = db.execute(
            text("""
                INSERT INTO luot_lam (nguoi_dung_id, loai_boc_cau, trang_thai, vi_tri_hien_tai)
                VALUES (:u, 'danh_gia_dau_vao', 'dang_lam', 1)
            """),
            {"u": uid},
        )
        luot_id = int(res.lastrowid)
        seed = random.SystemRandom().randrange(1, 2**31)
        db.execute(
            text("""
                INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, cap_tham_do_id, seed_xao, trang_thai_thao_tac)
                VALUES (:l, :q, 1, :cap, :s, 'chua_thao_tac')
            """),
            {"l": luot_id, "q": q1_id, "cap": cap_tham_do_id, "s": seed},
        )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _lock_attempt(db: Session, luot_id: int, uid: int, for_update: bool = True) -> dict:
    lock = " FOR UPDATE" if for_update else ""
    row = db.execute(
        text(f"""
            SELECT id, nguoi_dung_id, trang_thai, vi_tri_hien_tai, bat_dau_luc, nop_luc
            FROM luot_lam
            WHERE id = :id AND loai_boc_cau = 'danh_gia_dau_vao'{lock}
        """),
        {"id": luot_id},
    ).mappings().first()
    if row is None or int(row["nguoi_dung_id"]) != uid:
        raise NotFoundError()
    return dict(row)


def _shape_current_step(db: Session, row: dict) -> dict:
    questions, options = load_questions_by_ids(db, [int(row["cau_hoi_id"])])
    q = questions[int(row["cau_hoi_id"])]
    levels_by_id = _levels_by_id(db)
    actual_lv = levels_by_id.get(int(q["cap_do_id"]))
    return {
        "thu_tu": int(row["thu_tu"]),
        "tong_so_cau": TOTAL_QUESTIONS,
        "ky_nang": q["ky_nang"],
        "cap_hien_thi": actual_lv["ten"] if actual_lv else None,
        "cho_phep_doi_cau": q["ky_nang"] == "nghe" or bool(q["tep_audio"] or q["tep_hinh"]),
        "cau_hoi": {
            "id": q["id"],
            "dang": q["dang"],
            "noi_dung": q["noi_dung"],
            "pinyin": q["pinyin"],
            "tep_hinh": q["tep_hinh"],
            "tep_audio": q["tep_audio"],
            "mo_ta_hinh": q["mo_ta_hinh"],
            # Ẩn hoàn toàn đáp án, lời giải và dịch nghĩa của câu đọc/nghe; riêng câu sap_xep cần câu tiếng Việt để ghép từ
            "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None,
        },
        "phuong_an": shuffle_choice_options(q, options, row["seed_xao"]),
    }


def get_session(db: Session, luot_id: int, uid: int) -> dict:
    """Lấy trạng thái hiện tại của phiên đánh giá đầu vào kèm lịch sử các bước trước để giữ vạch tiến độ 1..8 khi F5."""
    attempt = _lock_attempt(db, luot_id, uid, for_update=False)
    if attempt["trang_thai"] != "dang_lam":
        db.rollback()
        return {"id": luot_id, "trang_thai": attempt["trang_thai"], "tong_so_cau": TOTAL_QUESTIONS, "hien_tai": None, "lich_su_buoc": []}

    done_rows = db.execute(
        text("""
            SELECT a.thu_tu, a.trang_thai_thao_tac
            FROM cau_tra_loi a
            WHERE a.luot_lam_id = :l AND a.trang_thai_thao_tac <> 'chua_thao_tac'
            ORDER BY a.thu_tu
        """),
        {"l": luot_id},
    ).mappings().all()
    # Không trả cờ đúng/sai khi đang làm khảo sát để giữ tuyệt đối tính khách quan (chuẩn Cambridge Placement)
    lich_su_buoc = [
        {
            "thu_tu": int(r["thu_tu"]),
            "trang_thai_thao_tac": r["trang_thai_thao_tac"],
        }
        for r in done_rows
    ]

    cur_row = db.execute(
        text("""
            SELECT id, cau_hoi_id, thu_tu, seed_xao, trang_thai_thao_tac
            FROM cau_tra_loi
            WHERE luot_lam_id = :l AND trang_thai_thao_tac = 'chua_thao_tac'
            ORDER BY thu_tu LIMIT 1
        """),
        {"l": luot_id},
    ).mappings().first()
    if cur_row is None:
        db.rollback()
        return {"id": luot_id, "trang_thai": "san_sang_nop", "tong_so_cau": TOTAL_QUESTIONS, "hien_tai": None, "lich_su_buoc": lich_su_buoc}

    step = _shape_current_step(db, dict(cur_row))
    db.rollback()
    return {"id": luot_id, "trang_thai": "dang_lam", "tong_so_cau": TOTAL_QUESTIONS, "hien_tai": step, "lich_su_buoc": lich_su_buoc}


def _advance_or_finalize(db: Session, luot_id: int, cur_pos: int) -> bool:
    """Sinh câu kế tiếp theo nhánh thích ứng nếu `cur_pos < 8`; nếu đã xong câu 8 thì đóng phiên và tạo `ket_qua_dau_vao`."""
    if cur_pos < TOTAL_QUESTIONS:
        levels_map = _levels_by_order(db)
        levels_by_id = _levels_by_id(db)
        outcomes = _prior_outcomes(db, luot_id, levels_by_id)
        next_pos = cur_pos + 1
        target_order = compute_slot_target_order(next_pos, outcomes)
        used = _used_question_ids(db, luot_id)
        next_qid, cap_tham_do_id = _pick_question_for_slot(db, next_pos, target_order, levels_map, used)
        seed = random.SystemRandom().randrange(1, 2**31)
        db.execute(
            text("""
                INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, cap_tham_do_id, seed_xao, trang_thai_thao_tac)
                VALUES (:l, :q, :t, :cap, :s, 'chua_thao_tac')
            """),
            {"l": luot_id, "q": next_qid, "t": next_pos, "cap": cap_tham_do_id, "s": seed},
        )
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": next_pos, "id": luot_id})
        return False

    # Kiểm tra chắc chắn cả 8 vị trí đều đã kết thúc thao tác (AT03, AT04, AT44)
    unfinished = int(db.execute(
        text("SELECT COUNT(*) FROM cau_tra_loi WHERE luot_lam_id = :l AND trang_thai_thao_tac = 'chua_thao_tac'"),
        {"l": luot_id},
    ).scalar_one())
    total_rows = int(db.execute(text("SELECT COUNT(*) FROM cau_tra_loi WHERE luot_lam_id = :l"), {"l": luot_id}).scalar_one())
    if unfinished > 0 or total_rows < TOTAL_QUESTIONS:
        raise ConflictError("Vẫn còn câu hỏi chưa hoàn tất thao tác")

    db.execute(
        text("""
            UPDATE luot_lam
            SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = 'nop_tay', vi_tri_hien_tai = :v
            WHERE id = :id
        """),
        {"v": TOTAL_QUESTIONS, "id": luot_id},
    )
    db.execute(
        text("""
            INSERT IGNORE INTO ket_qua_dau_vao (luot_lam_id, trang_thai_phan_tich)
            VALUES (:l, 'chua')
        """),
        {"l": luot_id},
    )
    return True


def submit_step(db: Session, luot_id: int, uid: int, body) -> dict:
    """Lưu câu trả lời hoặc Bỏ qua của vị trí hiện tại, chấm ngay câu khách quan và tiến sang câu tiếp theo."""
    try:
        attempt = _lock_attempt(db, luot_id, uid, for_update=True)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Phiên đánh giá này đã nộp xong")

        cur = db.execute(
            text("""
                SELECT id, cau_hoi_id, thu_tu, seed_xao, phien_ban_luu
                FROM cau_tra_loi
                WHERE luot_lam_id = :l AND trang_thai_thao_tac = 'chua_thao_tac'
                ORDER BY thu_tu LIMIT 1 FOR UPDATE
            """),
            {"l": luot_id},
        ).mappings().first()
        if cur is None:
            raise ConflictError("Không còn câu hỏi chờ trả lời")
        if int(cur["cau_hoi_id"]) != body.cau_hoi_id:
            raise ConflictError("Câu hỏi gửi lên không khớp vị trí hiện tại")

        questions, options = load_questions_by_ids(db, [body.cau_hoi_id])
        q = questions[body.cau_hoi_id]
        option_id, van_ban = None, None
        if not body.bo_qua:
            if q["dang"] in CHOICE_TYPES:
                if body.phuong_an_chon_id is not None:
                    allowed = {o["id"] for o in shuffle_choice_options(q, options, None)}
                    if body.phuong_an_chon_id not in allowed:
                        raise RuleError("Phương án chọn không thuộc câu hỏi này")
                    option_id = body.phuong_an_chon_id
            else:
                van_ban = (body.van_ban or "").strip() or None

        is_skipped = bool(body.bo_qua)
        if not is_skipped and option_id is None and van_ban is None:
            raise RuleError("Vui lòng chọn hoặc nhập câu trả lời trước khi tiếp tục; nếu chưa biết hãy bấm Bỏ qua.")
        trang_thai_tt = "bo_qua" if is_skipped else "da_tra_loi"
        new_pbl = int(cur["phien_ban_luu"]) + 1
        elapsed = min(max(int(body.thoi_gian_lam_giay or 0), 0), 3600) if body.thoi_gian_lam_giay is not None else None
        answer_id = int(cur["id"])
        cur_pos = int(cur["thu_tu"])

        db.execute(
            text("""
                UPDATE cau_tra_loi
                SET phuong_an_chon_id = :o,
                    van_ban = :v,
                    trang_thai_thao_tac = :tt,
                    thoi_gian_lam_giay = :tg,
                    xac_nhan_luc = NOW(),
                    phien_ban_luu = :pbl
                WHERE id = :id
            """),
            {
                "o": None if is_skipped else option_id,
                "v": None if is_skipped else van_ban,
                "tt": trang_thai_tt,
                "tg": elapsed,
                "pbl": new_pbl,
                "id": answer_id,
            },
        )

        # Chấm ngay bằng code cho câu khách quan (câu 1–6 và câu 8); câu 7 bỏ qua cũng chấm 0 ngay
        if q["dang"] in OBJECTIVE_TYPES:
            ans_dict = {"phuong_an_chon_id": option_id, "van_ban": van_ban}
            right = (not is_skipped) and bool(is_correct(q, ans_dict, options))
            db.execute(
                text("""
                    INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem)
                    VALUES (:a, 1, 'code', 'hoan_tat', :pbl, :d)
                """),
                {"a": answer_id, "pbl": new_pbl, "d": 1 if right else 0},
            )
        elif is_skipped:
            db.execute(
                text("""
                    INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet)
                    VALUES (:a, 1, 'code', 'hoan_tat', :pbl, 0, 'Bạn đã bỏ qua câu dịch này.')
                """),
                {"a": answer_id, "pbl": new_pbl},
            )

        finished = _advance_or_finalize(db, luot_id, cur_pos)
        db.commit()
    except Exception:
        db.rollback()
        raise

    if finished:
        return {
            "da_nop": True,
            "luot_id": luot_id,
            "hien_tai": None,
        }
    return {**get_session(db, luot_id, uid), "da_nop": False}


def replace_broken_question(db: Session, luot_id: int, uid: int, ly_do: str = "loi_audio") -> dict:
    """Đổi câu khác cùng vị trí khi tệp âm thanh/hình bị lỗi (AT06, AT33).

    - Còn câu phù hợp chưa dùng: lưu `lich_su_thay_cau` và cập nhật `cau_hoi_id` tại chỗ (giữ tổng 8 câu).
    - Hết câu thay thế: đánh dấu `trang_thai_thao_tac = 'loi_ky_thuat'` và chuyển sang vị trí kế tiếp (AT44).
    """
    try:
        attempt = _lock_attempt(db, luot_id, uid, for_update=True)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Phiên đánh giá đã kết thúc")

        cur = db.execute(
            text("""
                SELECT id, cau_hoi_id, thu_tu, cap_tham_do_id
                FROM cau_tra_loi
                WHERE luot_lam_id = :l AND trang_thai_thao_tac = 'chua_thao_tac'
                ORDER BY thu_tu LIMIT 1 FOR UPDATE
            """),
            {"l": luot_id},
        ).mappings().first()
        if cur is None:
            raise ConflictError("Không có câu đang mở để thay thế")

        pos = int(cur["thu_tu"])
        levels_map = _levels_by_order(db)
        levels_by_id = _levels_by_id(db)
        target_order = levels_by_id.get(int(cur["cap_tham_do_id"]), {}).get("thu_tu", 2)
        used = _used_question_ids(db, luot_id)

        try:
            new_qid, _ = _pick_question_for_slot(db, pos, int(target_order), levels_map, used)
        except RuleError:
            new_qid = None

        if new_qid is not None:
            seed = random.SystemRandom().randrange(1, 2**31)
            db.execute(
                text("""
                    INSERT INTO lich_su_thay_cau (luot_lam_id, thu_tu_vi_tri, cau_hoi_cu_id, cau_hoi_moi_id, ly_do)
                    VALUES (:l, :t, :cu, :moi, :ld)
                """),
                {"l": luot_id, "t": pos, "cu": cur["cau_hoi_id"], "moi": new_qid, "ld": ly_do},
            )
            db.execute(
                text("UPDATE cau_tra_loi SET cau_hoi_id = :q, seed_xao = :s WHERE id = :id"),
                {"q": new_qid, "s": seed, "id": cur["id"]},
            )
            db.commit()
            return {**get_session(db, luot_id, uid), "da_thay_cau": True, "da_nop": False}

        # Không còn câu thay thế -> ghi nhận lỗi kỹ thuật (không tính là sai kiến thức) và qua vị trí kế
        db.execute(
            text("""
                UPDATE cau_tra_loi
                SET phuong_an_chon_id = NULL, van_ban = NULL,
                    trang_thai_thao_tac = 'loi_ky_thuat', xac_nhan_luc = NOW()
                WHERE id = :id
            """),
            {"id": cur["id"]},
        )
        finished = _advance_or_finalize(db, luot_id, pos)
        db.commit()
    except Exception:
        db.rollback()
        raise

    if finished:
        return {"da_thay_cau": False, "da_nop": True, "luot_id": luot_id, "hien_tai": None}
    return {**get_session(db, luot_id, uid), "da_thay_cau": False, "da_nop": False}


def defer_placement(db: Session, uid: int) -> None:
    """Bài đánh giá đầu vào là bước bắt buộc khi bắt đầu (câu chưa biết có nút Bỏ qua ngay trong bài)."""
    raise ConflictError(
        "Vui lòng hoàn thành 8 câu đánh giá trình độ (câu không biết có thể bấm Bỏ qua hoặc gửi trống) để xác định cấp HSK mở khóa."
    )


def save_target_level(db: Session, uid: int, cap_do_id: int | None, phut_moi_ngay: int | None = None) -> dict:
    """Lưu cấp HSK mục tiêu tùy chọn của học viên vào `nguoi_dung.ks_cap_muc_tieu_id`."""
    try:
        if cap_do_id is not None:
            ok = db.execute(
                text("SELECT 1 FROM cap_do WHERE id = :id AND trang_thai = 'da_dang'"),
                {"id": cap_do_id},
            ).first()
            if not ok:
                raise RuleError("Cấp độ mục tiêu không hợp lệ")
        if phut_moi_ngay is not None and phut_moi_ngay not in (10, 15, 30, 60):
            raise RuleError("Thời lượng mỗi ngày chọn trong các mức 10, 15, 30 hoặc 60 phút")

        db.execute(
            text("""
                UPDATE nguoi_dung
                SET ks_cap_muc_tieu_id = :cap,
                    ks_phut_moi_ngay = COALESCE(:phut, ks_phut_moi_ngay),
                    ks_trang_thai = 'da_tra_loi',
                    ks_cap_nhat_luc = NOW()
                WHERE id = :u
            """),
            {"cap": cap_do_id, "phut": phut_moi_ngay, "u": uid},
        )
        db.commit()
        return {"cap_muc_tieu_id": cap_do_id, "phut_moi_ngay": phut_moi_ngay}
    except Exception:
        db.rollback()
        raise
