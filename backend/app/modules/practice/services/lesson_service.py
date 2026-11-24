"""Lượt làm bài Ôn luyện (mục 4.1, 4.3, 4.4, 4.6 & bổ sung gợi ý phân tầng / ghi 3 chiều dữ liệu học).

- Vai trò: Xử lý mở bài học/kiểm tra cuối thửa, mở gợi ý 2 tầng, kiểm tra từng câu, trừ năng lượng, ghi Sổ tay và cộng KN.
- Luồng dữ liệu: `student_practice.py` -> `lesson_service.py` -> `grading` (chấm đúng/sai) -> ghi `luot_lam`, `cau_tra_loi`, `ket_qua_cham`, `so_tay`, `nhat_ky_thuong`.
- Xử lý ngoại lệ: Chặn ô khóa, chặn hết năng lượng ở lượt tiêu hao, chặn gửi câu sai thứ tự, chống cộng lặp KN / trừ lặp khi bấm đúp.
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import XIANG_JSON_SYSTEM_PROMPT, ai_ready, json_completion
from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.grading import (
    CHOICE_TYPES,
    correct_option_id,
    is_correct as _is_correct,
    load_set_items as load_items,
    normalize_answer_text,
    shuffle_choice_options as _shuffled,
)
from app.modules.practice.services import path_view

CONSUMING = ("hoc_moi", "lam_lai")
KN = {"bai": ("kn_bai", 10), "cuoi_thua": ("kn_cuoi_thua", 20)}

_FALLBACK_HINT_1 = {
    "nghe": "Hãy nghe lại từ khóa chỉ thời gian, địa điểm hoặc động từ chính trong câu.",
    "doc": "Chú ý chủ ngữ, động từ chính và từ hỏi trong câu trước khi đối chiếu đáp án.",
    "tu_vung": "Đọc kỹ âm tiết pinyin và ngữ cảnh để phân biệt các từ gần nghĩa.",
    "viet": "Xác định cấu trúc Chủ ngữ + Trạng ngữ thời gian/địa điểm + Động từ + Tân ngữ.",
}
_FALLBACK_HINT_2 = {
    "sap_xep": "Tìm chủ ngữ đứng đầu câu, đặt trạng ngữ chỉ thời gian/nơi chốn trước động từ chính.",
    "dien_chu": "Kiểm tra loại từ còn thiếu ở chỗ trống (động từ, lượng từ hay trợ từ ngữ khí).",
}


def _lesson_scope(db: Session, ma_goc_id: int) -> dict:
    row = db.execute(
        text("""SELECT b.id, b.ma_goc_id, b.loai, b.vi_tri, b.ten, b.thua_id, t.ten AS ten_thua, t.cap_do_id, t.ky_nang, c.ten AS ten_cap_do
                FROM bo_de b
                JOIN bo_de t ON t.ma_goc_id = b.thua_id AND t.trang_thai = 'da_dang'
                JOIN cap_do c ON c.id = t.cap_do_id
                WHERE b.ma_goc_id = :g AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'"""),
        {"g": ma_goc_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def _slot_state(db: Session, uid: int, lesson: dict) -> dict:
    level = next((l for l in path_view.levels(db) if l["id"] == lesson["cap_do_id"]), None)
    if level is None or not path_view.level_open(level, lesson["ky_nang"], path_view.opened_levels(db, uid, lesson["ky_nang"])):
        raise ConflictError("Cấp này của kỹ năng chưa mở")
    for land in path_view.build_map(db, uid, lesson["cap_do_id"], lesson["ky_nang"]):
        for slot in land["o"]:
            if slot.get("ma_goc_id") == lesson["ma_goc_id"]:
                return slot
    raise NotFoundError()


def start_lesson(db: Session, ma_goc_id: int, uid: int) -> int:
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        energy, max_energy = path_view.sync_user_energy(db, uid, auto_commit=False)
        lesson = _lesson_scope(db, ma_goc_id)
        slot = _slot_state(db, uid, lesson)
        if slot["trang_thai"] == "khoa":
            raise ConflictError("Ô này chưa mở. Hãy hoàn thành ô trước.")
        if slot.get("luot_dang_lam"):
            db.commit()
            return int(slot["luot_dang_lam"])
        purpose = {"da_xong": "on_lai", "da_vuot": "on_lai", "chua_dat": "lam_lai"}.get(slot["trang_thai"], "hoc_moi")
        if purpose in CONSUMING and energy <= 0:
            raise ConflictError(
                f"Hết năng lượng (0/{max_energy}). Hãy vào Sổ tay câu sai làm đúng từ 80% để hồi ngay +1 năng lượng hoặc nhận Nhiệm vụ ngày!"
            )
        items, questions, _ = load_items(db, lesson["id"])
        if not items:
            raise RuleError("Bài chưa có câu hỏi")
        result = db.execute(
            text("""INSERT INTO luot_lam (nguoi_dung_id, bo_de_id, muc_dich, trang_thai, vi_tri_hien_tai)
                    VALUES (:u, :b, :m, 'dang_lam', 1)"""),
            {"u": uid, "b": lesson["id"], "m": purpose},
        )
        luot_id = int(result.lastrowid)
        order = [i["cau_hoi_id"] for i in items]
        random.SystemRandom().shuffle(order)
        for pos, qid in enumerate(order, start=1):
            db.execute(
                text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, seed_xao) VALUES (:l, :q, :t, :s)"),
                {"l": luot_id, "q": qid, "t": pos, "s": random.SystemRandom().randrange(1, 2**31)},
            )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _lock(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text("""SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.muc_dich, l.trang_thai, l.vi_tri_hien_tai, l.bat_dau_luc,
                       b.ma_goc_id, b.loai
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.id = :id AND b.loai IN ('bai', 'cuoi_thua') FOR UPDATE"""),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


def _answers(db: Session, luot_id: int) -> list[dict]:
    rows = db.execute(
        text("""SELECT a.id, a.cau_hoi_id, a.thu_tu, a.seed_xao, a.trang_thai_thao_tac, a.muc_goi_y,
                       a.phuong_an_chon_id, a.van_ban, a.xac_nhan_luc, a.xem_loi_giai_luc,
                       a.phien_ban_luu, a.nang_luong_tru, v.diem, v.nhan_xet, v.cau_sua, v.ly_do_sua
                FROM cau_tra_loi a LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l ORDER BY a.thu_tu"""),
        {"l": luot_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _hint_texts(q: dict, skill: str) -> tuple[str, str]:
    h1 = (q.get("goi_y") or "").strip() or _FALLBACK_HINT_1.get(skill, "Đọc kỹ yêu cầu câu hỏi và đối chiếu từng từ khóa.")
    h2 = (q.get("goi_y_2") or "").strip() or _FALLBACK_HINT_2.get(q["dang"], "Loại trừ các phương án sai ngữ cảnh hoặc sai loại từ trước khi chọn.")
    return h1, h2


def _pass_mark(q: dict) -> float:
    return float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0


def _grade_open_writing(q: dict, options: dict, student_text: str) -> tuple[float, str, str, str, str]:
    """Chấm câu Viết / Dịch trong Ôn luyện theo mô hình hướng dẫn của Cambridge Write & Improve."""
    max_score = float(q.get("diem_toi_da") or 10.0)
    threshold = _pass_mark(q)
    ref_ans = (q.get("dich_nghia") or "").strip()
    accepted = [o["noi_dung"] for o in options[q["id"]]["chap_nhan"] if o.get("noi_dung")]
    must_word = (q.get("tu_bat_buoc") or "").strip()
    rubric = (q.get("tieu_chi_mo_ta") or "Đúng ý nghĩa, ngữ pháp HSK và dùng từ tự nhiên.").strip()

    if ai_ready():
        prompt = (
            f"Đề bài ({q['dang']}): {q.get('noi_dung') or ''}\n"
            f"Từ bắt buộc (nếu có): {must_word}\n"
            f"Đáp án/nghĩa tham chiếu: {ref_ans or ' / '.join(accepted)}\n"
            f"Tiêu chí (0..{max_score:g}, đạt từ {threshold:g}): {rubric}\n"
            f"Bài làm của học viên: {student_text}\n\n"
            "Chấm theo phong cách Cambridge Write & Improve: đánh giá khách quan, nêu rõ chỗ cần cải thiện mà giữ tinh thần khích lệ.\n"
            'Chỉ trả JSON: {"diem": <so>, "nhan_xet": "...", "cau_sua": "...", "ly_do_sua": "..."}'
        )
        raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
        if isinstance(raw, dict) and isinstance(raw.get("diem"), (int, float)):
            sc = max(0.0, min(max_score, round(float(raw["diem"]), 2)))
            return (
                sc,
                str(raw.get("nhan_xet") or "").strip()[:500],
                str(raw.get("cau_sua") or "").strip()[:500],
                str(raw.get("ly_do_sua") or "").strip()[:500],
                "ai",
            )

    norm_in = normalize_answer_text(student_text)
    refs = [r for r in ([ref_ans] + accepted) if r]
    if any(norm_in == normalize_answer_text(r) for r in refs):
        return max_score, "Câu viết/dịch rõ ràng, chính xác cấu trúc và ý nghĩa.", refs[0], "", "code"
    if must_word and must_word not in student_text:
        return 2.0, f"Bài viết chưa sử dụng từ bắt buộc «{must_word}».", refs[0] if refs else "", f"Hãy đặt câu có chứa từ «{must_word}» đúng vị trí ngữ pháp.", "code"
    words_ref = {w for r in refs for w in normalize_answer_text(r).split() if len(w) >= 2}
    matched = sum(1 for w in words_ref if w in norm_in) if words_ref else 0
    ratio = matched / max(1, len(words_ref)) if words_ref else 0.5
    sc = round(max_score * min(1.0, ratio * 1.15), 1)
    nx = "Đã truyền tải được ý chính, có thể trau chuốt thêm cách diễn đạt." if sc >= threshold else "Câu trả lời cần điều chỉnh lại từ vựng hoặc cấu trúc để sát nghĩa hơn."
    return sc, nx, refs[0] if refs else "", "Kiểm tra lại chủ ngữ, trạng ngữ và động từ chính trong câu.", "code"


def _feedback(q: dict, options: dict, answer: dict, energy_cut: int, word: dict | None = None) -> dict:
    is_skipped = answer.get("trang_thai_thao_tac") == "bo_qua" or (answer["phuong_an_chon_id"] is None and not answer["van_ban"])
    dung = (not is_skipped) and answer["diem"] is not None and float(answer["diem"]) >= _pass_mark(q)
    # Chuẩn Cambridge: khi học viên bấm Bỏ qua, tuyệt đối KHÔNG tự động lộ đáp án hay lời giải
    if is_skipped:
        return {
            "dung": False,
            "bo_qua": True,
            "dap_an_id": None,
            "dap_an_chap_nhan": [],
            "giai_thich": None,
            "dich_nghia": None,
            "loi_nghe": None,
            "goi_mo": None,
            "diem": 0,
            "diem_toi_da": float(q.get("diem_toi_da") or 1.0),
            "nhan_xet": None,
            "cau_sua": None,
            "ly_do_sua": None,
            "nang_luong_tru": energy_cut,
            "tu_vung": None,
        }

    h1, _ = _hint_texts(q, q.get("ky_nang") or "doc")
    return {
        "dung": dung,
        "bo_qua": False,
        "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
        "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
        "giai_thich": q["giai_thich"],
        "dich_nghia": q["dich_nghia"],
        "loi_nghe": q["loi_nghe"],
        "goi_mo": answer.get("ly_do_sua") or h1,
        "diem": float(answer["diem"]) if answer.get("diem") is not None else 0.0,
        "diem_toi_da": float(q.get("diem_toi_da") or 1.0),
        "nhan_xet": answer.get("nhan_xet"),
        "cau_sua": answer.get("cau_sua"),
        "ly_do_sua": answer.get("ly_do_sua"),
        "nang_luong_tru": energy_cut,
        "tu_vung": word,
    }


def _word(db: Session, tu_vung_id: int | None) -> dict | None:
    if not tu_vung_id:
        return None
    row = db.execute(
        text("""SELECT id, chu_han, pinyin, nghia, vd_cau, vd_pinyin, vd_nghia, vd_audio FROM tu_vung
                WHERE id = :id AND trang_thai = 'xuat_ban'"""),
        {"id": tu_vung_id},
    ).mappings().first()
    return dict(row) if row else None


def _word_for_question(db: Session, q: dict, options: dict) -> dict | None:
    """Tìm từ mục đầy đủ (chữ Hán, pinyin, nghĩa, câu ví dụ) cho câu hỏi sau khi học viên đã kiểm tra đáp án."""
    direct = _word(db, q.get("tu_vung_id"))
    if direct:
        return direct
    if q.get("ky_nang") != "tu_vung":
        return None
    candidates: list[str] = []
    stem = (q.get("noi_dung") or "").strip()
    if stem and len(stem) <= 8 and "（" not in stem and "(" not in stem and "_" not in stem:
        candidates.append(stem)
    if q["dang"] in CHOICE_TYPES:
        right_id = correct_option_id(q, options)
        owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
        right_opt = next((o for o in options[owner]["lua_chon"] if o["id"] == right_id), None)
        if right_opt and right_opt.get("noi_dung"):
            han = right_opt["noi_dung"].split("[", 1)[0].strip()
            if han and len(han) <= 8:
                candidates.append(han)
    for cand in candidates:
        row = db.execute(
            text("""SELECT id, chu_han, pinyin, nghia, vd_cau, vd_pinyin, vd_nghia, vd_audio FROM tu_vung
                    WHERE chu_han = :h AND trang_thai = 'xuat_ban'
                    ORDER BY (cap_do_id = :c) DESC, id ASC LIMIT 1"""),
            {"h": cand, "c": q.get("cap_do_id") or 0},
        ).mappings().first()
        if row:
            return dict(row)
    return None


def _summary(db: Session, attempt: dict, lesson_row: dict, answers: list[dict], questions: dict) -> dict:
    total = len(answers)
    right = sum(1 for a in answers if a["diem"] is not None and float(a["diem"]) >= _pass_mark(questions[a["cau_hoi_id"]]))
    passed = total > 0 and right == total
    kn = 0
    nl_thuong = 0
    reason, _ = KN[lesson_row["loai"]]
    if passed:
        got = db.execute(
            text("""SELECT so_luong FROM nhat_ky_thuong
                    WHERE nguoi_dung_id = :u AND luot_lam_id = :l AND ly_do = :r LIMIT 1"""),
            {"u": attempt["nguoi_dung_id"], "l": attempt["id"], "r": reason},
        ).scalar_one_or_none()
        kn = int(got or 0)
        if lesson_row["loai"] == "cuoi_thua":
            got_nl = db.execute(
                text("""SELECT so_luong FROM nhat_ky_thuong
                        WHERE nguoi_dung_id = :u AND luot_lam_id = :l AND ly_do = 'thuong_cuoi_thua' LIMIT 1"""),
                {"u": attempt["nguoi_dung_id"], "l": attempt["id"]},
            ).scalar_one_or_none()
            nl_thuong = int(got_nl or 0)
    wrong = [
        {"thu_tu": a["thu_tu"], "noi_dung": questions[a["cau_hoi_id"]]["noi_dung"]}
        for a in answers
        if not (a["diem"] is not None and float(a["diem"]) >= _pass_mark(questions[a["cau_hoi_id"]]))
        and a.get("trang_thai_thao_tac") != "bo_qua"
    ]
    return {
        "so_dung": right,
        "tong": total,
        "dat": passed,
        "kn_nhan": kn,
        "nang_luong_thuong": nl_thuong,
        "ly_do_kn": reason if kn else None,
        "cau_can_on": wrong,
    }


def get_attempt(db: Session, luot_id: int, uid: int) -> dict:
    attempt = _lock(db, luot_id, uid)
    db.commit()
    lesson_row = db.execute(
        text("SELECT id, ma_goc_id, loai, vi_tri, ten, thua_id FROM bo_de WHERE id = :id"),
        {"id": attempt["bo_de_id"]},
    ).mappings().one()
    land = db.execute(
        text("""SELECT t.ten, t.cap_do_id, t.ky_nang, c.ten AS ten_cap_do FROM bo_de t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.ma_goc_id = :g ORDER BY (t.trang_thai = 'da_dang') DESC, t.phien_ban DESC LIMIT 1"""),
        {"g": lesson_row["thua_id"]},
    ).mappings().one()
    _, questions, options = load_items(db, attempt["bo_de_id"])
    answers = _answers(db, luot_id)
    allow_hints = lesson_row["loai"] == "bai"  # Kiểm tra cuối thửa tắt gợi ý & Hỏi Xiang khi đang làm (AT23)
    items = []
    for a in answers:
        q = questions[a["cau_hoi_id"]]
        parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
        confirmed = a["xac_nhan_luc"] is not None
        muc_goi_y = int(a.get("muc_goi_y") or 0)
        h1, h2 = _hint_texts(q, land["ky_nang"])
        opened_hints = ([h1] if muc_goi_y >= 1 else []) + ([h2] if muc_goi_y >= 2 else [])
        is_retry_challenge = (
            attempt["muc_dich"] == "lam_lai"
            and not confirmed
            and q["dang"] == "chon_mot"
            and not q["tep_hinh"]
            and not q["tep_audio"]
        )
        word_info = (
            _word_for_question(db, q, options)
            if (confirmed or (is_retry_challenge and land["ky_nang"] == "tu_vung"))
            else None
        )
        stem_pinyin = None if is_retry_challenge else q["pinyin"]
        retry_context = (
            word_info["vd_cau"]
            if is_retry_challenge and word_info and word_info.get("vd_cau") and (q["noi_dung"] or "").strip() == word_info["chu_han"]
            else None
        )
        opts_out = _shuffled(q, options, a["seed_xao"])
        if is_retry_challenge:
            opts_out = [
                {
                    **o,
                    "noi_dung": o["noi_dung"].split("[", 1)[0].strip() if "[" in (o.get("noi_dung") or "") else o["noi_dung"],
                }
                for o in opts_out
            ]
        items.append({
            "thu_tu": a["thu_tu"],
            "muc_goi_y": muc_goi_y,
            "cho_phep_goi_y": allow_hints and not confirmed,
            "goi_y_da_mo": opened_hints if allow_hints else [],
            "cau_hoi": {
                "id": q["id"],
                "dang": q["dang"],
                "noi_dung": q["noi_dung"],
                "pinyin": stem_pinyin,
                "thu_thach_lam_lai": is_retry_challenge,
                "ngu_canh_lam_lai": retry_context,
                "tep_hinh": q["tep_hinh"],
                "tep_audio": q["tep_audio"],
                "mo_ta_hinh": q["mo_ta_hinh"],
                "goi_y": opened_hints[-1] if opened_hints else None,  # Chỉ hiện gợi ý sau khi học viên chủ động bấm mở
                "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None,
                "tu_bat_buoc": q["tu_bat_buoc"],
            },
            "ngu_lieu": parent and {
                "noi_dung": parent["noi_dung"],
                "pinyin": None if is_retry_challenge else parent["pinyin"],
                "tep_hinh": parent["tep_hinh"],
                "tep_audio": parent["tep_audio"],
            },
            "phuong_an": opts_out,
            "tra_loi": {"phuong_an_chon_id": a["phuong_an_chon_id"], "van_ban": a["van_ban"]} if confirmed else None,
            "ket_qua": _feedback(q, options, a, int(a["nang_luong_tru"]), word_info) if confirmed else None,
        })
    return {
        "id": luot_id,
        "trang_thai": attempt["trang_thai"],
        "muc_dich": attempt["muc_dich"],
        "tieu_hao": attempt["muc_dich"] in CONSUMING,
        "bai": {
            "ma_goc_id": lesson_row["ma_goc_id"],
            "ten": lesson_row["ten"],
            "loai": lesson_row["loai"],
            "vi_tri": lesson_row["vi_tri"],
            "thua": land["ten"],
            "ky_nang": land["ky_nang"],
            "cap_do_id": land["cap_do_id"],
            "ten_cap_do": land["ten_cap_do"],
        },
        "cau_hoi": items,
        "the_tu": [],
        "ket_qua": _summary(db, attempt, lesson_row, answers, questions) if attempt["trang_thai"] == "da_nop" else None,
        **path_view.energy_and_kn(db, uid),
    }


def open_hint(db: Session, luot_id: int, uid: int, cau_hoi_id: int) -> dict:
    """Mở tuần tự Gợi ý mức 1 rồi mức 2 cho câu đang làm của bài Ôn luyện thường (không trừ điểm, lưu vào muc_goi_y)."""
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Lượt làm bài đã kết thúc")
        if attempt["loai"] != "bai":
            raise ConflictError("Bài kiểm tra cuối thửa không hỗ trợ mở gợi ý")
        answers = _answers(db, luot_id)
        answer = next((a for a in answers if a["cau_hoi_id"] == cau_hoi_id), None)
        if answer is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        if answer["xac_nhan_luc"] is not None:
            raise ConflictError("Câu này đã kiểm tra xong")
        _, questions, _ = load_items(db, attempt["bo_de_id"])
        q = questions[cau_hoi_id]
        skill = q.get("ky_nang") or "doc"
        h1, h2 = _hint_texts(q, skill)
        cur = int(answer.get("muc_goi_y") or 0)
        nxt = min(2, cur + 1)
        if nxt != cur:
            db.execute(text("UPDATE cau_tra_loi SET muc_goi_y = :m WHERE id = :id"), {"m": nxt, "id": answer["id"]})
        db.commit()
        opened = ([h1] if nxt >= 1 else []) + ([h2] if nxt >= 2 else [])
        return {"muc_goi_y": nxt, "goi_y_da_mo": opened}
    except Exception:
        db.rollback()
        raise


def check_answer(db: Session, luot_id: int, uid: int, body) -> dict:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Lượt này đã kết thúc")
        answers = _answers(db, luot_id)
        answer = next((a for a in answers if a["cau_hoi_id"] == body.cau_hoi_id), None)
        if answer is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        _, questions, options = load_items(db, attempt["bo_de_id"])
        q = questions[answer["cau_hoi_id"]]
        if answer["xac_nhan_luc"] is not None:  # Gửi lặp: trả lại kết quả cũ, không trừ thêm
            w_dup = _word_for_question(db, q, options)
            db.commit()
            return {"ket_qua": _feedback(q, options, answer, int(answer["nang_luong_tru"]), w_dup), "ket_thuc": False,
                    **path_view.energy_and_kn(db, uid)}
        first_open = next(a for a in answers if a["xac_nhan_luc"] is None)
        if first_open["id"] != answer["id"]:
            raise ConflictError("Hãy trả lời các câu theo thứ tự")

        option_id, van_ban = None, None
        if q["dang"] in CHOICE_TYPES:
            if body.phuong_an_chon_id is not None:
                if body.phuong_an_chon_id not in {o["id"] for o in _shuffled(q, options, None)}:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            van_ban = (body.van_ban or "").strip() or None
        is_skipped = option_id is None and van_ban is None
        trang_thai_tt = "bo_qua" if is_skipped else "da_tra_loi"

        # Nếu là câu Dịch / Viết mở và có nhập bài làm -> đóng giao dịch đọc trước khi gọi AI chấm kiểu Write & Improve
        diem_cham, nx_cham, cs_cham, ld_cham, nguon_cham = 0.0, None, None, None, "code"
        if not is_skipped and q["dang"] in ("viet_mo", "dich_cau"):
            db.rollback()
            diem_cham, nx_cham, cs_cham, ld_cham, nguon_cham = _grade_open_writing(q, options, van_ban)
            attempt = _lock(db, luot_id, uid)
            if attempt["trang_thai"] != "dang_lam":
                raise ConflictError("Lượt này đã kết thúc")
            answers = _answers(db, luot_id)
            answer = next((a for a in answers if a["cau_hoi_id"] == body.cau_hoi_id), None)
            if answer["xac_nhan_luc"] is not None:
                w_dup = _word_for_question(db, q, options)
                db.commit()
                return {"ket_qua": _feedback(q, options, answer, int(answer["nang_luong_tru"]), w_dup), "ket_thuc": False,
                        **path_view.energy_and_kn(db, uid)}
            correct = diem_cham >= _pass_mark(q)
        else:
            answer.update({"phuong_an_chon_id": option_id, "van_ban": van_ban, "trang_thai_thao_tac": trang_thai_tt})
            correct = (not is_skipped) and bool(_is_correct(q, answer, options))
            diem_cham = 1.0 if correct else 0.0

        cut = 0
        if not correct:
            if attempt["muc_dich"] in CONSUMING:
                db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
                energy, _ = path_view.sync_user_energy(db, uid, auto_commit=False)
                cut = 1 if energy > 0 else 0
                if cut:
                    db.execute(text("UPDATE nguoi_dung SET nang_luong = nang_luong - 1 WHERE id = :u"), {"u": uid})
            if not is_skipped:  # Chỉ câu trả lời sai mới vào Sổ tay; câu Bỏ qua không tính là sai kiến thức
                db.execute(
                    text("""INSERT INTO so_tay (nguoi_dung_id, cau_hoi_goc_id, trang_thai, han_on, cap_nhat_luc)
                            VALUES (:u, :g, 'can_on', CURDATE(), NOW())
                            ON DUPLICATE KEY UPDATE trang_thai = 'can_on', han_on = CURDATE(), cap_nhat_luc = NOW()"""),
                    {"u": uid, "g": q["ma_goc_id"]},
                )
        new_pbl = int(answer.get("phien_ban_luu") or 0) + 1
        # Chuẩn AT45 & Cambridge Write & Improve: không tự ghi xem_loi_giai_luc khi kiểm tra câu;
        # chỉ ghi xem_loi_giai_luc = NOW() khi học viên chủ động bấm mở xem đáp án/lời giải đối chiếu.
        db.execute(
            text("""UPDATE cau_tra_loi
                    SET phuong_an_chon_id = :o, van_ban = :v, trang_thai_thao_tac = :tt,
                        xac_nhan_luc = NOW(),
                        phien_ban_luu = :pbl, nang_luong_tru = :c
                    WHERE id = :id"""),
            {
                "o": option_id, "v": van_ban, "tt": trang_thai_tt,
                "pbl": new_pbl, "c": cut, "id": answer["id"],
            },
        )
        db.execute(
            text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet, cau_sua, ly_do_sua)
                    VALUES (:a, 1, :ng, 'hoan_tat', :pbl, :d, :nx, :cs, :ld)"""),
            {
                "a": answer["id"], "ng": nguon_cham, "pbl": new_pbl,
                "d": diem_cham, "nx": nx_cham, "cs": cs_cham, "ld": ld_cham,
            },
        )
        answer.update({
            "phuong_an_chon_id": option_id,
            "van_ban": van_ban,
            "trang_thai_thao_tac": trang_thai_tt,
            "diem": diem_cham,
            "nhan_xet": nx_cham,
            "cau_sua": cs_cham,
            "ly_do_sua": ld_cham,
            "xac_nhan_luc": True,
        })
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": answer["thu_tu"] + 1, "id": luot_id})

        finished = all(a["xac_nhan_luc"] is not None for a in answers)
        if finished:
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = 'nop_tay' WHERE id = :id"), {"id": luot_id})
            passed = all(a["diem"] is not None and float(a["diem"]) >= _pass_mark(questions[a["cau_hoi_id"]]) for a in answers)
            if passed:
                reason, amount = KN[attempt["loai"]]
                db.execute(
                    text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, luot_lam_id, ly_do, so_luong, bo_de_goc_id)
                            VALUES (:u, :l, :r, :n, :g)"""),
                    {"u": uid, "l": luot_id, "r": reason, "n": amount, "g": attempt["ma_goc_id"]},
                )
                if attempt["loai"] == "cuoi_thua" and attempt["muc_dich"] in CONSUMING:
                    db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
                    cur_e, max_e = path_view.sync_user_energy(db, uid, auto_commit=False)
                    if cur_e < max_e:
                        ins_e = db.execute(
                            text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, luot_lam_id, ly_do, so_luong)
                                    VALUES (:u, :l, 'thuong_cuoi_thua', 1)"""),
                            {"u": uid, "l": luot_id},
                        )
                        if ins_e.rowcount:
                            db.execute(text("UPDATE nguoi_dung SET nang_luong = nang_luong + 1 WHERE id = :u"), {"u": uid})
        word = _word_for_question(db, q, options) if not is_skipped else None
        db.commit()
        return {"ket_qua": _feedback(q, options, answer, cut, word), "ket_thuc": finished, **path_view.energy_and_kn(db, uid)}
    except Exception:
        db.rollback()
        raise


def mark_solution_viewed(db: Session, luot_id: int, uid: int, cau_hoi_id: int) -> dict:
    """Ghi nhận `xem_loi_giai_luc = NOW()` khi học viên bấm xem đáp án/lời giải đối chiếu sau khi đã kiểm tra câu (AT45 — không ghi đè muc_goi_y)."""
    try:
        _lock(db, luot_id, uid)
        row = db.execute(
            text("""SELECT id, xac_nhan_luc, trang_thai_thao_tac
                    FROM cau_tra_loi WHERE luot_lam_id = :l AND cau_hoi_id = :q"""),
            {"l": luot_id, "q": cau_hoi_id},
        ).mappings().first()
        if row is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        if row["xac_nhan_luc"] is None or row["trang_thai_thao_tac"] == "bo_qua":
            raise ConflictError("Chỉ mở lời giải sau khi đã trả lời và kiểm tra câu hỏi")
        db.execute(
            text("UPDATE cau_tra_loi SET xem_loi_giai_luc = COALESCE(xem_loi_giai_luc, NOW()) WHERE id = :id"),
            {"id": int(row["id"])},
        )
        db.commit()
        return {"da_ghi_nhan": True}
    except Exception:
        db.rollback()
        raise


def abandon(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] == "dang_lam":
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_bo' WHERE id = :id"), {"id": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        raise
