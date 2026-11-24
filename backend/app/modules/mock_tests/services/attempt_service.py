"""Dịch vụ Thi thử HSK iBT cấp đề ngẫu nhiên theo đúng trình độ hiện tại của Học viên (`AT17`–`AT22`, `AT41`–`AT43`).

- Vai trò:
  1) Xác định tự động trình độ HSK hiện tại của học viên (`path_view.current_proficiency`) — không hiện danh sách HSK 1–4
     để tự chọn và không tiết lộ tên cấp độ ở Phòng chờ hay trong lúc đang làm bài.
  2) Rút ngẫu nhiên 1 bộ đề chuẩn HSK hợp lệ của trình độ hiện tại (ưu tiên đề chưa từng nộp – `AT17`), giữ nguyên phiên
     đang làm dở khi F5 hoặc bấm lại (`AT18`).
  3) Chấm câu khách quan bằng code và tự động chấm câu Viết mở (`viet_mo` / `dich_cau`) bằng AI ngay khi nộp bài
     (đóng giao dịch CSDL trước khi gọi AI, có khóa `FOR UPDATE` chống nộp trùng `AT21`, Giảng viên vẫn phúc khảo lại được).
  4) Chỉ hiển thị tên cấp độ HSK trên Phiếu báo điểm Kết quả & Lịch sử sau khi đã nộp bài.
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import XIANG_JSON_SYSTEM_PROMPT, ai_ready, json_completion
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.common.sql_helpers import in_params
from app.modules.grading import is_correct, load_set_items as load_items, normalize_answer_text
from app.modules.mock_tests.services.content import (
    exam_version,
    shape_passage,
    shape_question,
)
from app.modules.practice.services import path_view

_STANDARD_SPECS = {
    1: {"so_cau": 40, "thoi_luong_phut": 40, "ky_nang": ["nghe", "doc"]},
    2: {"so_cau": 60, "thoi_luong_phut": 55, "ky_nang": ["nghe", "doc"]},
    3: {"so_cau": 80, "thoi_luong_phut": 90, "ky_nang": ["nghe", "doc", "viet"]},
    4: {"so_cau": 100, "thoi_luong_phut": 105, "ky_nang": ["nghe", "doc", "viet"]},
}


def _remaining_seconds_sql() -> str:
    return "TIMESTAMPDIFF(SECOND, NOW(), l.bat_dau_luc + INTERVAL b.thoi_luong_phut MINUTE)"


def _lock_attempt(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text(f"""
            SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, l.bat_dau_luc, l.nop_luc, l.ly_do_nop,
                   l.vi_tri_hien_tai, {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.id = :id AND b.loai = 'de_thi' FOR UPDATE
        """),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


def _grade_single_exam_writing(q: dict, options: dict, student_text: str) -> tuple[float, str, str, str, str]:
    """Chấm tự động câu Viết đoạn / Đặt câu từ hình (`viet_mo`, `dich_cau`) ngay khi nộp đề thi thử."""
    max_score = float(q.get("diem_toi_da") or 10.0)
    must_word = (q.get("tu_bat_buoc") or "").strip()
    img_desc = (q.get("mo_ta_hinh") or "").strip()
    ref_vi = (q.get("dich_nghia") or "").strip()
    accepted = [o["noi_dung"] for o in options.get(q["id"], {}).get("chap_nhan", []) if o.get("noi_dung")]
    rubric = (q.get("tieu_chi_mo_ta") or "Đúng ngữ pháp HSK, sử dụng đúng từ bắt buộc (nếu có) và phù hợp ngữ cảnh hình/đề.").strip()

    if ai_ready():
        prompt = (
            f"Chấm câu Viết trong đề thi HSK ({q['dang']}, thang điểm 0..{max_score:g}):\n"
            f"- Đề bài: {q.get('noi_dung') or '(viết câu theo tranh/từ gợi ý)'}\n"
            f"- Mô tả tranh (nếu có): {img_desc}\n"
            f"- Từ bắt buộc phải dùng (nếu có): {must_word}\n"
            f"- Câu mẫu tham khảo: {' / '.join(accepted) or ref_vi}\n"
            f"- Tiêu chí chấm: {rubric}\n"
            f"- Bài làm của thí sinh: {student_text}\n\n"
            "Hãy chấm công tâm theo chuẩn giám khảo HSK. Nếu thiếu từ bắt buộc hoặc viết sai hoàn toàn ngữ pháp thì trừ điểm tương ứng.\n"
            'Chỉ trả JSON: {"diem": <so>, "nhan_xet": "...", "cau_sua": "...", "ly_do_sua": "..."}'
        )
        raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
        if isinstance(raw, dict) and isinstance(raw.get("diem"), (int, float)):
            sc = max(0.0, min(max_score, round(float(raw["diem"]), 2)))
            return (
                sc,
                str(raw.get("nhan_xet") or "Đã chấm tự động theo tiêu chí HSK.").strip()[:500],
                str(raw.get("cau_sua") or (accepted[0] if accepted else "")).strip()[:500],
                str(raw.get("ly_do_sua") or "").strip()[:500],
                "ai",
            )

    # Bộ chấm dự phòng tất định khi chưa bật khóa AI
    txt = student_text.strip()
    norm_in = normalize_answer_text(txt)
    if any(norm_in == normalize_answer_text(a) for a in ([ref_vi] + accepted) if a):
        return max_score, "Câu viết chính xác ngữ pháp và đúng trọng tâm đề bài.", accepted[0] if accepted else txt, "", "code"
    if must_word and must_word not in txt:
        return (
            round(max_score * 0.2, 2),
            f"Câu viết chưa có từ bắt buộc «{must_word}».",
            accepted[0] if accepted else "",
            f"Đề yêu cầu đặt câu hoàn chỉnh có sử dụng từ «{must_word}».",
            "code",
        )
    cjk_chars = sum(1 for ch in txt if "\u4e00" <= ch <= "\u9fff")
    if q["dang"] == "viet_mo" and cjk_chars >= 4:
        sc = round(max_score * (0.8 if len(txt) >= 6 else 0.65), 2)
        return (
            sc,
            "Câu viết có cấu trúc Hán ngữ hợp lệ và dùng đúng từ khóa yêu cầu.",
            accepted[0] if accepted else txt,
            "Có thể mở rộng thêm bổ ngữ hoặc trạng ngữ để câu sinh động hơn.",
            "code",
        )
    return (
        round(max_score * 0.3, 2),
        "Câu viết còn quá ngắn hoặc chưa đủ thành phần Chủ – Vị.",
        accepted[0] if accepted else "",
        "Cần viết câu tiếng Trung hoàn chỉnh đúng ngữ cảnh đề bài.",
        "code",
    )


def _prepare_writing_grades(db: Session, bo_de_id: int, luot_id: int) -> dict[int, tuple[float, str, str, str, str]]:
    """Thu thập các câu `viet_mo`/`dich_cau` có bài làm, giải phóng kết nối đọc rồi gọi AI chấm trước khi khóa nộp bài."""
    items, questions, options = load_items(db, bo_de_id)
    answers = _answers(db, luot_id)
    tasks: list[tuple[int, dict, str]] = []
    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        if q["dang"] not in ("viet_mo", "dich_cau"):
            continue
        ans = answers.get(q["id"])
        if ans and (ans.get("van_ban") or "").strip():
            tasks.append((int(ans["id"]), q, str(ans["van_ban"]).strip()))

    db.rollback()  # Giải phóng kết nối MySQL trước khi gọi mạng tới AI!
    graded: dict[int, tuple[float, str, str, str, str]] = {}
    for ans_id, q, txt in tasks:
        graded[ans_id] = _grade_single_exam_writing(q, options, txt)
    return graded


def _close_expired_attempts(db: Session, uid: int) -> None:
    """Tự động đóng và chấm hoàn tất mọi lượt Thi thử đã hết giờ của học viên."""
    expired_rows = db.execute(
        text(f"""
            SELECT l.id, l.bo_de_id
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND l.trang_thai = 'dang_lam'
              AND {_remaining_seconds_sql()} <= 0
        """),
        {"u": uid},
    ).mappings().all()
    for r in expired_rows:
        lid = int(r["id"])
        graded_map = _prepare_writing_grades(db, int(r["bo_de_id"]), lid)
        attempt = _lock_attempt(db, lid, uid)
        if attempt["trang_thai"] == "dang_lam" and attempt["con_lai_giay"] <= 0:
            _submit_locked(db, attempt, "het_gio", graded_map)
            db.commit()


def _valid_exams_for_level(db: Session, cap_do_id: int) -> list[dict]:
    """Lọc các bộ đề chuẩn HSK hợp lệ của cấp (`da_dang`, `thoi_luong_phut > 0`, có câu tính điểm và đủ audio Nghe)."""
    rows = db.execute(
        text("""
            SELECT b.id, b.ma_goc_id, b.cap_do_id, b.thoi_luong_phut, b.tep_audio_chung,
                   SUM(CASE WHEN i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_cau,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'nghe' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_nghe,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'doc' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_doc,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'viet' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_viet,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'nghe' AND i.la_cau_vi_du = 0
                             AND b.tep_audio_chung IS NULL
                             AND COALESCE(q.tep_audio, p.tep_audio) IS NULL
                            THEN 1 ELSE 0 END) AS so_nghe_thieu_audio
            FROM bo_de b
            JOIN cap_do cd ON cd.id = b.cap_do_id AND cd.trang_thai = 'da_dang'
            LEFT JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
            LEFT JOIN cau_hoi q ON q.id = i.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            WHERE b.loai = 'de_thi'
              AND b.trang_thai = 'da_dang'
              AND b.cap_do_id = :cap
              AND b.thoi_luong_phut > 0
            GROUP BY b.id, b.ma_goc_id, b.cap_do_id, b.thoi_luong_phut, b.tep_audio_chung
        """),
        {"cap": cap_do_id},
    ).mappings().all()
    valid = []
    for r in rows:
        so_cau = int(r["so_cau"] or 0)
        thieu_audio = int(r["so_nghe_thieu_audio"] or 0)
        if so_cau > 0 and thieu_audio == 0:
            valid.append({
                "id": int(r["id"]),
                "ma_goc_id": int(r["ma_goc_id"]),
                "cap_do_id": int(r["cap_do_id"]),
                "thoi_luong_phut": int(r["thoi_luong_phut"]),
                "so_cau": so_cau,
                "so_nghe": int(r["so_nghe"] or 0),
                "so_doc": int(r["so_doc"] or 0),
                "so_viet": int(r["so_viet"] or 0),
            })
    return valid


def _resolve_current_proficiency_level(db: Session, uid: int, levels: list[dict]) -> dict:
    """Lấy đúng cấp độ HSK hiện tại của học viên (từ Đánh giá đầu vào + tiến độ nâng cấp lộ trình)."""
    if not levels:
        raise RuleError("Hệ thống chưa có cấu hình cấp độ thi")
    prof = path_view.current_proficiency(db, uid, levels)
    if prof:
        matched = next((lv for lv in levels if int(lv["id"]) == int(prof["id"])), None)
        if matched:
            return matched
    return levels[0]


# ---------------- Phòng chờ Thi thử chuẩn HSK iBT & Cấp đề ngẫu nhiên (AT17, AT18) ----------------

def get_exam_lobby(db: Session, uid: int) -> dict:
    """Trả thông tin phòng chờ Thi thử bảo mật: không hiện danh sách HSK 1–4 và không tiết lộ tên cấp trước khi thi."""
    try:
        _close_expired_attempts(db, uid)
        db.commit()
    except Exception:
        db.rollback()
        raise

    levels = [
        dict(r)
        for r in db.execute(
            text("""
                SELECT id, ma, ten, thu_tu, diem_toi_da_thi, diem_dat_thi
                FROM cap_do
                WHERE trang_thai = 'da_dang'
                ORDER BY thu_tu
            """)
        ).mappings().all()
    ]
    cur_lv = _resolve_current_proficiency_level(db, uid, levels)
    cid = int(cur_lv["id"])
    thu_tu = int(cur_lv["thu_tu"])
    next_lv = next((lv for lv in levels if int(lv["thu_tu"]) > thu_tu), None)

    open_row = db.execute(
        text(f"""
            SELECT l.id AS luot_id, b.thoi_luong_phut, {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND l.trang_thai = 'dang_lam'
            ORDER BY l.id DESC LIMIT 1
        """),
        {"u": uid},
    ).mappings().first()

    active_exam = None
    if open_row and int(open_row["con_lai_giay"] or 0) > 0:
        active_exam = {
            "luot_id": int(open_row["luot_id"]),
            "thoi_luong_phut": int(open_row["thoi_luong_phut"]),
            "con_lai_giay": int(open_row["con_lai_giay"]),
        }

    valid_exams = _valid_exams_for_level(db, cid)
    std = _STANDARD_SPECS.get(thu_tu, {"so_cau": 40, "thoi_luong_phut": 40, "ky_nang": ["nghe", "doc"]})
    sample = valid_exams[0] if valid_exams else None
    skills = (
        [k for k in ("nghe", "doc", "viet") if sample and sample[f"so_{k}"] > 0]
        if sample else std["ky_nang"]
    )
    db.rollback()
    return {
        "san_sang_thi": len(valid_exams) > 0 or active_exam is not None,
        "so_cau_chuan": sample["so_cau"] if sample else std["so_cau"],
        "thoi_luong_phut": sample["thoi_luong_phut"] if sample else std["thoi_luong_phut"],
        "ky_nang": skills or std["ky_nang"],
        "diem_toi_da_thi": int(cur_lv["diem_toi_da_thi"]),
        "diem_dat_thi": int(cur_lv["diem_dat_thi"]),
        "ten_trinh_do_hien_tai": cur_lv["ten"],
        "ten_cap_tiep_theo": next_lv["ten"] if next_lv else None,
        "luot_dang_lam": active_exam,
    }


def start_random_exam(db: Session, uid: int) -> dict:
    """Tự động rút 1 đề thi thử ngẫu nhiên hợp lệ theo đúng trình độ hiện tại của học viên (AT17, AT18)."""
    _close_expired_attempts(db, uid)
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})

        # AT18: Nếu đang có phiên thi thử còn thời gian -> trả lại đúng phiên đó (không đổi đề, không đặt lại giờ)
        open_row = db.execute(
            text(f"""
                SELECT l.id, {_remaining_seconds_sql()} AS con_lai_giay
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND l.trang_thai = 'dang_lam'
                ORDER BY l.id DESC LIMIT 1
            """),
            {"u": uid},
        ).mappings().first()
        if open_row and int(open_row["con_lai_giay"]) > 0:
            db.commit()
            return {"luot_id": int(open_row["id"]), "tiep_tuc": True}

        levels = [
            dict(r)
            for r in db.execute(
                text("SELECT id, ma, ten, thu_tu FROM cap_do WHERE trang_thai = 'da_dang' ORDER BY thu_tu")
            ).mappings().all()
        ]
        cur_lv = _resolve_current_proficiency_level(db, uid, levels)
        cap_do_id = int(cur_lv["id"])

        # AT17: Chọn ngẫu nhiên 1 đề hợp lệ của trình độ hiện tại, ưu tiên đề chưa từng nộp (`da_nop`)
        valid_exams = _valid_exams_for_level(db, cap_do_id)
        if not valid_exams:
            raise ConflictError("Hiện chưa có bộ đề thi thử phù hợp cho trình độ của bạn.")

        done_roots = set(
            int(x)
            for x in db.execute(
                text("""
                    SELECT DISTINCT b.ma_goc_id
                    FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                    WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND b.cap_do_id = :cap AND l.trang_thai = 'da_nop'
                """),
                {"u": uid, "cap": cap_do_id},
            ).scalars().all()
        )
        unseen = [e for e in valid_exams if e["ma_goc_id"] not in done_roots]
        chosen = random.SystemRandom().choice(unseen if unseen else valid_exams)

        items, _, _ = load_items(db, chosen["id"])
        scored = [i for i in items if not i["la_cau_vi_du"]]
        if not scored:
            raise ConflictError("Hiện chưa có bộ đề thi thử phù hợp cho trình độ của bạn.")

        result = db.execute(
            text("INSERT INTO luot_lam (nguoi_dung_id, bo_de_id, trang_thai, vi_tri_hien_tai) VALUES (:u, :b, 'dang_lam', 1)"),
            {"u": uid, "b": chosen["id"]},
        )
        luot_id = int(result.lastrowid)
        for item in scored:
            db.execute(
                text("""
                    INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, trang_thai_thao_tac)
                    VALUES (:l, :q, :t, 'chua_thao_tac')
                """),
                {"l": luot_id, "q": item["cau_hoi_id"], "t": item["so_cau"]},
            )
        db.commit()
        return {"luot_id": luot_id, "tiep_tuc": False}
    except Exception:
        db.rollback()
        raise


# ---------------- Làm bài & Nộp bài (AT19, AT20, AT21, AT41) ----------------

def _mask_exam_during_session(exam: dict) -> dict:
    """Trong lúc đang thi: ẩn hoàn toàn mã đề gốc VÀ tên cấp HSK (A2)."""
    masked = dict(exam)
    masked["ten"] = "Kỳ thi thử năng lực Hán ngữ"
    masked["ten_cap_do"] = ""
    masked["ma_de"] = "Đề ngẫu nhiên bảo mật"
    masked.pop("cap_do_id", None)
    masked.pop("thu_tu_cap", None)
    return masked


def _mask_exam_after_submit(exam: dict) -> dict:
    """Sau khi nộp bài: hiển thị cấp độ HSK trên Phiếu điểm nhưng vẫn ẩn mã đề ngân hàng."""
    masked = dict(exam)
    masked["ten"] = f"Bài thi thử {exam['ten_cap_do']}"
    masked["ma_de"] = "Đề ngẫu nhiên"
    return masked


def _answers(db: Session, luot_id: int) -> dict[int, dict]:
    rows = db.execute(
        text("""
            SELECT id, cau_hoi_id, thu_tu, phuong_an_chon_id, van_ban, trang_thai_thao_tac, phien_ban_luu
            FROM cau_tra_loi
            WHERE luot_lam_id = :l
        """),
        {"l": luot_id},
    ).mappings().all()
    return {r["cau_hoi_id"]: dict(r) for r in rows}


def _section_state(items: list[dict], vi_tri_hien_tai: int | None) -> tuple[list[str], str, list[str]]:
    """Xác định thứ tự các phần kỹ năng của đề, phần đang mở hiện tại và danh sách phần đã khóa một chiều (chuẩn HSK iBT)."""
    ordered_skills: list[str] = []
    skill_by_so_cau: dict[int, str] = {}
    for it in items:
        if it["la_cau_vi_du"]:
            continue
        kn = it["ky_nang"]
        if kn not in ordered_skills:
            ordered_skills.append(kn)
        if it.get("so_cau"):
            skill_by_so_cau[int(it["so_cau"])] = kn

    if not ordered_skills:
        return [], "nghe", []
    cur_skill = skill_by_so_cau.get(int(vi_tri_hien_tai or 1), ordered_skills[0])
    cur_idx = ordered_skills.index(cur_skill) if cur_skill in ordered_skills else 0
    locked_past = ordered_skills[:cur_idx]
    return ordered_skills, ordered_skills[cur_idx], locked_past


def get_attempt(db: Session, luot_id: int, uid: int) -> dict:
    attempt = db.execute(
        text(f"""
            SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, l.vi_tri_hien_tai,
                   {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.id = :id AND b.loai = 'de_thi'
        """),
        {"id": luot_id},
    ).mappings().first()
    if attempt is None or int(attempt["nguoi_dung_id"]) != uid:
        raise NotFoundError()

    if attempt["trang_thai"] == "dang_lam" and int(attempt["con_lai_giay"] or 0) <= 0:
        graded_map = _prepare_writing_grades(db, int(attempt["bo_de_id"]), luot_id)
        try:
            locked = _lock_attempt(db, luot_id, uid)
            if locked["trang_thai"] == "dang_lam" and locked["con_lai_giay"] <= 0:
                _submit_locked(db, locked, "het_gio", graded_map)
            db.commit()
        except Exception:
            db.rollback()
            raise
        raw_exam = exam_version(db, int(attempt["bo_de_id"]))
        return {"id": luot_id, "trang_thai": "da_nop", "de": _mask_exam_after_submit(raw_exam)}

    raw_exam = exam_version(db, int(attempt["bo_de_id"]))
    if attempt["trang_thai"] != "dang_lam":
        db.rollback()
        return {"id": luot_id, "trang_thai": attempt["trang_thai"], "de": _mask_exam_after_submit(raw_exam)}

    # Chuẩn đề thi HSK quốc tế: từ HSK 3 trở lên đề thi không in Pinyin trên chữ Hán
    hide_pinyin = int(raw_exam.get("thu_tu_cap") or 1) >= 3
    items, questions, options = load_items(db, raw_exam["id"])
    answers = _answers(db, luot_id)
    passages, shaped = {}, []
    for item in items:
        q = questions[item["cau_hoi_id"]]
        data = shape_question(q, options, reveal=item["la_cau_vi_du"], hide_pinyin=hide_pinyin)
        if q["cau_cha_id"] and q["cau_cha_id"] not in passages:
            passages[q["cau_cha_id"]] = shape_passage(questions[q["cau_cha_id"]], options, reveal=False, hide_pinyin=hide_pinyin)
        answer = answers.get(q["id"])
        shaped.append({
            **{k: item[k] for k in ("thu_tu", "phan", "la_cau_vi_du", "so_cau", "ky_nang")},
            "cau_cha_id": q["cau_cha_id"],
            "cau_hoi": data,
            "tra_loi": {"phuong_an_chon_id": answer["phuong_an_chon_id"], "van_ban": answer["van_ban"]} if answer else None,
        })
    ordered_skills, cur_skill, locked_past = _section_state(items, attempt["vi_tri_hien_tai"])
    max_audio_plays = 1 if int(raw_exam.get("thu_tu_cap") or 1) >= 3 else 2
    db.rollback()
    return {
        "id": luot_id,
        "trang_thai": "dang_lam",
        "con_lai_giay": int(attempt["con_lai_giay"]),
        "vi_tri_hien_tai": attempt["vi_tri_hien_tai"],
        "ky_nang_hien_tai": cur_skill,
        "cac_phan_da_khoa": locked_past,
        "so_luot_nghe_toi_da": max_audio_plays,
        "de": _mask_exam_during_session(raw_exam),
        "cau_hoi": shaped,
        "ngu_lieu": passages,
    }


def save_answer(db: Session, luot_id: int, uid: int, body) -> dict:
    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Bài đã nộp, không sửa được")
        if attempt["con_lai_giay"] <= 0:
            bo_de_id = int(attempt["bo_de_id"])
            db.rollback()
            graded_map = _prepare_writing_grades(db, bo_de_id, luot_id)
            attempt2 = _lock_attempt(db, luot_id, uid)
            if attempt2["trang_thai"] == "dang_lam":
                _submit_locked(db, attempt2, "het_gio", graded_map)
                db.commit()
            raise ConflictError("Đã hết giờ, bài được nộp tự động")

        # Kiểm tra khóa phần thi một chiều chuẩn HSK máy tính (严禁跨区)
        items, _, _ = load_items(db, int(attempt["bo_de_id"]))
        _, cur_skill, locked_past = _section_state(items, attempt["vi_tri_hien_tai"])
        target_item = next((it for it in items if not it["la_cau_vi_du"] and int(it["cau_hoi_id"]) == body.cau_hoi_id), None)
        if target_item is None:
            raise RuleError("Câu hỏi không thuộc bài thi này")
        if target_item["ky_nang"] in locked_past:
            raise RuleError("Phần thi này đã khóa sau khi chuyển phần, không thể quay lại chỉnh sửa.")
        if target_item["ky_nang"] != cur_skill:
            raise RuleError("Vui lòng hoàn thành và chốt phần thi hiện tại trước khi làm phần tiếp theo.")

        answer = db.execute(
            text("SELECT a.id, q.dang, q.cau_cha_id FROM cau_tra_loi a JOIN cau_hoi q ON q.id = a.cau_hoi_id "
                 "WHERE a.luot_lam_id = :l AND a.cau_hoi_id = :q FOR UPDATE"),
            {"l": luot_id, "q": body.cau_hoi_id},
        ).mappings().first()
        if answer is None:
            raise RuleError("Câu hỏi không thuộc bài thi này")
        option_id, van_ban = None, None
        if answer["dang"] in ("chon_mot", "dung_sai", "chon_bo_chung"):
            if body.van_ban is not None:
                raise RuleError("Câu này chọn phương án, không nhập chữ")
            if body.phuong_an_chon_id is not None:
                owner = answer["cau_cha_id"] if answer["dang"] == "chon_bo_chung" else body.cau_hoi_id
                ok = db.execute(
                    text("SELECT 1 FROM phuong_an WHERE id = :o AND cau_hoi_id = :q AND vai_tro = 'lua_chon'"),
                    {"o": body.phuong_an_chon_id, "q": owner},
                ).first()
                if not ok:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            if body.phuong_an_chon_id is not None:
                raise RuleError("Câu này nhập câu trả lời, không chọn phương án")
            van_ban = (body.van_ban or "").strip() or None
        trang_thai_tt = "da_tra_loi" if (option_id is not None or van_ban is not None) else "chua_thao_tac"
        db.execute(
            text("""UPDATE cau_tra_loi
                    SET phuong_an_chon_id = :o, van_ban = :v, trang_thai_thao_tac = :tt,
                        xac_nhan_luc = CASE WHEN :tt = 'da_tra_loi' THEN NOW() ELSE NULL END,
                        phien_ban_luu = phien_ban_luu + 1
                    WHERE id = :id"""),
            {"o": option_id, "v": van_ban, "tt": trang_thai_tt, "id": answer["id"]},
        )
        # Chỉ cập nhật vị trí nếu vị trí đó nằm trong đúng phần đang mở
        valid_cur_nos = {int(it["so_cau"]) for it in items if not it["la_cau_vi_du"] and it["ky_nang"] == cur_skill}
        if body.vi_tri and int(body.vi_tri) in valid_cur_nos:
            db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": int(body.vi_tri), "id": luot_id})
        db.commit()
        return {"con_lai_giay": int(attempt["con_lai_giay"])}
    except Exception:
        db.rollback()
        raise


def advance_section(db: Session, luot_id: int, uid: int) -> dict:
    """Chốt khóa vĩnh viễn phần kỹ năng hiện tại và mở phần kỹ năng kế tiếp (`Nghe → Đọc → Viết`)."""
    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Bài thi đã nộp")
        if attempt["con_lai_giay"] <= 0:
            raise ConflictError("Đã hết giờ làm bài")

        items, _, _ = load_items(db, int(attempt["bo_de_id"]))
        answers = _answers(db, luot_id)
        ordered_skills, cur_skill, _ = _section_state(items, attempt["vi_tri_hien_tai"])
        cur_idx = ordered_skills.index(cur_skill) if cur_skill in ordered_skills else 0
        if cur_idx >= len(ordered_skills) - 1:
            raise RuleError("Bạn đang ở phần cuối cùng của đề thi; hãy bấm Nộp bài khi hoàn tất.")

        missing_in_sec = []
        for it in items:
            if it["la_cau_vi_du"] or it["ky_nang"] != cur_skill:
                continue
            ans = answers.get(it["cau_hoi_id"])
            has_ans = ans is not None and (
                ans["phuong_an_chon_id"] is not None or bool((ans["van_ban"] or "").strip())
            )
            if not has_ans:
                missing_in_sec.append(int(it["so_cau"]))

        if missing_in_sec:
            preview = ", ".join(str(n) for n in missing_in_sec[:12])
            raise RuleError(
                f"Phần hiện tại còn {len(missing_in_sec)} câu chưa trả lời (câu {preview}). "
                "Vì sau khi chuyển phần sẽ khóa không quay lại được, hãy chọn đủ đáp án trước khi sang phần kế tiếp."
            )

        next_skill = ordered_skills[cur_idx + 1]
        first_next_no = next(
            int(it["so_cau"]) for it in items if not it["la_cau_vi_du"] and it["ky_nang"] == next_skill
        )
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": first_next_no, "id": luot_id})
        db.commit()
        return {
            "ky_nang_hien_tai": next_skill,
            "cac_phan_da_khoa": ordered_skills[: cur_idx + 1],
            "vi_tri_hien_tai": first_next_no,
            "con_lai_giay": int(attempt["con_lai_giay"]),
        }
    except Exception:
        db.rollback()
        raise


def _submit_locked(
    db: Session,
    attempt: dict,
    reason: str,
    graded_writing: dict[int, tuple[float, str, str, str, str]] | None = None,
) -> None:
    """Chấm hoàn tất (gồm cả câu Viết do AI vừa chấm) và đóng lượt khi đang giữ khóa dòng `luot_lam` (AT21)."""
    items, questions, options = load_items(db, attempt["bo_de_id"])
    answers = _answers(db, attempt["id"])
    graded_writing = graded_writing or {}

    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        answer = answers.get(q["id"])
        if answer is None:
            continue
        pbl = int(answer["phien_ban_luu"])
        correct = is_correct(q, answer, options)
        if correct is None:  # Viết mở / Dịch câu -> lấy điểm AI chấm tự động ngay khi nộp
            ans_id = int(answer["id"])
            if answer["van_ban"] and ans_id in graded_writing:
                sc, nx, cs, ld, ng = graded_writing[ans_id]
                db.execute(
                    text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet, cau_sua, ly_do_sua)
                            VALUES (:a, 1, :ng, 'hoan_tat', :pbl, :d, :nx, :cs, :ld)"""),
                    {"a": ans_id, "ng": ng, "pbl": pbl, "d": sc, "nx": nx, "cs": cs, "ld": ld},
                )
            else:
                db.execute(
                    text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem)
                            VALUES (:a, 1, 'code', 'hoan_tat', :pbl, 0)"""),
                    {"a": ans_id, "pbl": pbl},
                )
            continue
        db.execute(
            text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem)
                    VALUES (:a, 1, 'code', 'hoan_tat', :pbl, :d)"""),
            {"a": answer["id"], "pbl": pbl, "d": 1 if correct else 0},
        )

    db.execute(
        text("""UPDATE luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                SET l.trang_thai = 'da_nop',
                    l.nop_luc = CASE WHEN :r = 'het_gio'
                                     THEN LEAST(NOW(), l.bat_dau_luc + INTERVAL b.thoi_luong_phut MINUTE)
                                     ELSE NOW() END,
                    l.ly_do_nop = :r
                WHERE l.id = :id AND l.trang_thai = 'dang_lam'"""),
        {"r": reason, "id": attempt["id"]},
    )


def submit_attempt(db: Session, luot_id: int, uid: int, het_gio: bool = False, thu_bai_vi_pham: bool = False) -> dict:
    """Nộp bài Thi thử: chặn nộp tay khi còn câu trống (AT19); cho phép cưỡng chế thu bài khi hết giờ hoặc vi phạm rời màn hình đủ 3 lần (AT20, AT21, AT41)."""
    snap = db.execute(
        text(f"""
            SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, l.ly_do_nop,
                   {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.id = :id AND b.loai = 'de_thi'
        """),
        {"id": luot_id},
    ).mappings().first()
    if snap is None or int(snap["nguoi_dung_id"]) != uid:
        raise NotFoundError()
    if snap["trang_thai"] != "dang_lam":
        db.rollback()
        return {"trang_thai": snap["trang_thai"], "ly_do_nop": snap["ly_do_nop"]}

    is_timeout = int(snap["con_lai_giay"] or 0) <= 0 or (het_gio and int(snap["con_lai_giay"] or 0) <= 5)

    if not is_timeout and not thu_bai_vi_pham:
        items, _, _ = load_items(db, int(snap["bo_de_id"]))
        answers = _answers(db, luot_id)
        missing_numbers = []
        for item in items:
            if item["la_cau_vi_du"]:
                continue
            ans = answers.get(item["cau_hoi_id"])
            has_ans = ans is not None and (
                ans["phuong_an_chon_id"] is not None or bool((ans["van_ban"] or "").strip())
            )
            if not has_ans:
                missing_numbers.append(int(item["so_cau"]))

        if missing_numbers:
            db.rollback()
            preview = ", ".join(str(n) for n in missing_numbers[:15])
            suffix = "…" if len(missing_numbers) > 15 else ""
            raise RuleError(
                f"Còn {len(missing_numbers)} câu tính điểm chưa trả lời (câu {preview}{suffix}). "
                f"Hãy hoàn thành tất cả các câu trước khi nộp bài."
            )

    # Chấm trước câu Viết bằng AI ngoài khóa giao dịch để không giữ kết nối MySQL
    graded_map = _prepare_writing_grades(db, int(snap["bo_de_id"]), luot_id)

    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            db.commit()
            return {"trang_thai": attempt["trang_thai"], "ly_do_nop": attempt["ly_do_nop"]}
        final_reason = "het_gio" if (attempt["con_lai_giay"] <= 0 or (het_gio and attempt["con_lai_giay"] <= 5)) else "nop_tay"
        _submit_locked(db, attempt, final_reason, graded_map)
        db.commit()
        return {"trang_thai": "da_nop", "ly_do_nop": final_reason}
    except Exception:
        db.rollback()
        raise


# ---------------- Kết quả & Lịch sử ----------------

def _current_results(db: Session, answer_ids: list[int]) -> dict[int, dict]:
    if not answer_ids:
        return {}
    marks, params = in_params("a", answer_ids)
    rows = db.execute(
        text(f"""
            SELECT k.cau_tra_loi_id, k.lan, k.nguon, k.trang_thai, k.diem, k.nhan_xet, k.cau_sua, k.ly_do_sua
            FROM ket_qua_cham k
            JOIN (SELECT cau_tra_loi_id, MAX(lan) AS lan FROM ket_qua_cham WHERE cau_tra_loi_id IN ({marks}) GROUP BY cau_tra_loi_id) m
              ON m.cau_tra_loi_id = k.cau_tra_loi_id AND m.lan = k.lan
        """),
        params,
    ).mappings().all()
    current = {r["cau_tra_loi_id"]: dict(r) for r in rows}
    done = db.execute(
        text(f"""SELECT cau_tra_loi_id, diem FROM v_ket_qua_hien_hanh WHERE cau_tra_loi_id IN ({marks})"""), params
    ).mappings().all()
    for r in done:
        current.setdefault(r["cau_tra_loi_id"], {})["diem_hien_hanh"] = float(r["diem"])
    return current


def score_attempt(db: Session, attempt: dict, items, questions, answers) -> dict:
    exam = exam_version(db, attempt["bo_de_id"])
    results = _current_results(db, [a["id"] for a in answers.values()])
    skills: dict[str, dict] = {}
    pending = 0
    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        answer = answers.get(q["id"])
        skill = skills.setdefault(item["ky_nang"], {"ky_nang": item["ky_nang"], "so_cau": 0, "tong_ty_le": 0.0, "dung": 0})
        skill["so_cau"] += 1
        score = results.get(answer["id"], {}).get("diem_hien_hanh") if answer else None
        if score is None:
            pending += 1
            continue
        max_q = float(q["diem_toi_da"] or 10.0)
        pass_q = float(q["nguong_dat"] or (max_q * 0.6))
        if q["dang"] in ("viet_mo", "dich_cau"):
            ratio = min(1.0, score / max(1.0, max_q))
            if score >= pass_q:
                skill["dung"] += 1
        else:
            ratio = score
            if score >= 1:
                skill["dung"] += 1
        skill["tong_ty_le"] += ratio
    skill_list = []
    for s in skills.values():
        s["diem"] = round(100 * s["tong_ty_le"] / s["so_cau"], 2) if s["so_cau"] else 0.0
        skill_list.append(s)
    raw_total = sum(100 * s["tong_ty_le"] / s["so_cau"] for s in skills.values() if s["so_cau"])
    scale = exam["diem_toi_da_thi"] / (100 * len(skills)) if skills else 0
    total = raw_total * scale
    return {
        "ky_nang": skill_list,
        "tong_diem": round(total, 2),
        "diem_toi_da": exam["diem_toi_da_thi"],
        "diem_dat": exam["diem_dat_thi"],
        "dat": pending == 0 and total >= exam["diem_dat_thi"],
        "so_cau_cho_cham": pending,
    }


def get_result(db: Session, luot_id: int, uid: int) -> dict:
    attempt = db.execute(
        text("SELECT id, nguoi_dung_id, bo_de_id, trang_thai, bat_dau_luc, nop_luc, ly_do_nop FROM luot_lam WHERE id = :id"),
        {"id": luot_id},
    ).mappings().first()
    if attempt is None or attempt["nguoi_dung_id"] != uid:
        raise NotFoundError()
    attempt = dict(attempt)
    if attempt["trang_thai"] != "da_nop":
        raise ConflictError("Bài chưa nộp")
    exam = _mask_exam_after_submit(exam_version(db, attempt["bo_de_id"]))
    items, questions, options = load_items(db, exam["id"])
    answers = _answers(db, luot_id)
    results = _current_results(db, [a["id"] for a in answers.values()])
    passages, shaped = {}, []
    for item in items:
        q = questions[item["cau_hoi_id"]]
        if q["cau_cha_id"] and q["cau_cha_id"] not in passages:
            passages[q["cau_cha_id"]] = shape_passage(questions[q["cau_cha_id"]], options, reveal=True)
        answer = answers.get(q["id"])
        result = results.get(answer["id"]) if answer else None
        entry = {
            **{k: item[k] for k in ("thu_tu", "phan", "la_cau_vi_du", "so_cau", "ky_nang")},
            "cau_cha_id": q["cau_cha_id"],
            "cau_hoi": shape_question(q, options, reveal=True),
            "tra_loi": {"phuong_an_chon_id": answer["phuong_an_chon_id"], "van_ban": answer["van_ban"]} if answer else None,
        }
        if answer and not item["la_cau_vi_du"]:
            score = result.get("diem_hien_hanh") if result else None
            pass_q = float(q["nguong_dat"] or (float(q["diem_toi_da"] or 10.0) * 0.6)) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
            entry["ket_qua"] = {
                "diem": score,
                "dung": (score is not None and score >= pass_q) if score is not None else None,
                "bo_trong": answer["phuong_an_chon_id"] is None and not answer["van_ban"],
                "trang_thai_cham": result.get("trang_thai") if result else None,
                "nhan_xet": result.get("nhan_xet") if result else None,
                "cau_sua": result.get("cau_sua") if result else None,
                "ly_do_sua": result.get("ly_do_sua") if result else None,
                "cau_tra_loi_id": answer["id"],
            }
        shaped.append(entry)
    diem_info = score_attempt(db, attempt, items, questions, answers)
    all_lvs = path_view.levels(db)
    exam_ord = int(exam.get("thu_tu_cap") or 1)
    next_lv = next((lv for lv in all_lvs if int(lv["thu_tu"]) > exam_ord), None)
    cur_prof = path_view.current_proficiency(db, uid, all_lvs)
    thang_cap = {
        "dat_chuan": bool(diem_info["dat"]),
        "cap_de_thi": exam["ten_cap_do"],
        "cap_tiep_theo": next_lv["ten"] if next_lv else None,
        "diem_con_thieu": max(0.0, round(float(diem_info["diem_dat"]) - float(diem_info["tong_diem"]), 2)),
        "trinh_do_hien_tai": cur_prof["ten"] if cur_prof else exam["ten_cap_do"],
    }
    return {
        "id": luot_id, "de": exam, "bat_dau_luc": attempt["bat_dau_luc"], "nop_luc": attempt["nop_luc"],
        "ly_do_nop": attempt["ly_do_nop"], "diem": diem_info, "thang_cap": thang_cap,
        "cau_hoi": shaped, "ngu_lieu": passages,
    }


def history(db: Session, uid: int) -> list[dict]:
    try:
        _close_expired_attempts(db, uid)
        db.commit()
    except Exception:
        db.rollback()

    rows = db.execute(
        text(f"""
            SELECT l.id, l.bo_de_id, l.trang_thai, l.bat_dau_luc, l.nop_luc, l.ly_do_nop,
                   b.cap_do_id, cd.ten AS ten_cap_do, {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l
            JOIN bo_de b ON b.id = l.bo_de_id
            JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi'
            ORDER BY l.bat_dau_luc DESC LIMIT 100
        """),
        {"u": uid},
    ).mappings().all()
    out = []
    for r in rows:
        item = dict(r)
        # Lượt đang làm dở ẩn tên cấp HSK; lượt đã nộp mới hiện tên cấp (A2)
        if item["trang_thai"] == "da_nop":
            item["ten"] = f"Bài thi thử {item['ten_cap_do']}"
            items, questions, _ = load_items(db, item["bo_de_id"])
            item["diem"] = score_attempt(db, item, items, questions, _answers(db, item["id"]))
        else:
            item["ten"] = "Kỳ thi thử đang làm"
            item["ten_cap_do"] = ""
            item["cap_do_id"] = None
        item["con_lai_giay"] = max(0, int(item["con_lai_giay"]))
        out.append(item)
    return out
