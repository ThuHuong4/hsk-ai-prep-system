"""Chấm câu Dịch (câu 7), phân tích năng lực đầu vào bằng AI và dựng màn hình kết quả 4 phần.

- Vai trò:
  1) Chấm câu 7 (`dich_cau`) theo tiêu chí chấm; tái sử dụng điểm đã chấm nếu `phien_ban_luu` không đổi (AT36).
  2) Gọi AI tổng hợp nhận định điểm mạnh/điểm yếu kèm câu bằng chứng (1..8), không giữ giao dịch CSDL mở lúc chờ AI.
  3) Hậu kiểm chặt đầu ra AI: loại bỏ câu bằng chứng ngoài 1..8 hoặc gán nhầm câu 'loi_ky_thuat' làm lỗi kiến thức (AT38, AT52).
  4) Chọn bài ôn cụ thể đang mở lưu vào `goi_y_lo_trinh` và trả về kết quả tách bạch 4 phần (AT09, AT35, AT37).
- Bảng CSDL tác động: `ket_qua_cham`, `ket_qua_dau_vao`, `nhan_dinh_dau_vao`, `nhan_dinh_bang_chung`, `goi_y_lo_trinh`.
"""
import threading
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import XIANG_JSON_SYSTEM_PROMPT, ai_ready, json_completion
from app.modules.common.service_errors import ConflictError, NotFoundError
from app.modules.grading import CHOICE_TYPES, correct_option_id, load_questions_by_ids, normalize_answer_text
from app.modules.placement.services.adaptive_rules import propose_starting_level_order
from app.modules.practice.services import level_test_service, path_view

ANALYSIS_TIMEOUT_SECONDS = 60
SKILL_VI = {"tu_vung": "Từ vựng", "doc": "Đọc hiểu", "nghe": "Nghe hiểu", "viet": "Viết & Dịch câu"}

_analyzing_locks: set[int] = set()
_lock = threading.Lock()


def _acquire_analysis(luot_id: int) -> bool:
    with _lock:
        if luot_id in _analyzing_locks:
            return False
        _analyzing_locks.add(luot_id)
        return True


def _release_analysis(luot_id: int) -> None:
    with _lock:
        _analyzing_locks.discard(luot_id)


def _fold_vi(value: str | None) -> str:
    val = unicodedata.normalize("NFKD", (value or "").lower().replace("đ", "d"))
    val = "".join(c for c in val if not unicodedata.combining(c))
    return " ".join(val.split())


def _heuristic_translation_grade(q: dict, options: dict, student_text: str) -> tuple[float, str, str, str, dict]:
    """Chấm dự phòng câu Dịch theo từ khóa nghĩa cốt lõi kèm 3 tiêu chí kiểu WriteMate khi chưa cấu hình khóa AI."""
    max_score = float(q["diem_toi_da"] or 10.0)
    ref_vi = (q.get("dich_nghia") or "").strip()
    accepted = [o["noi_dung"] for o in options[q["id"]]["chap_nhan"] if o.get("noi_dung")]
    given_norm = normalize_answer_text(student_text)
    given_fold = _fold_vi(student_text)

    if any(given_norm == normalize_answer_text(a) for a in ([ref_vi] + accepted) if a):
        return (
            max_score,
            "Bản dịch truyền tải chính xác, tự nhiên và đầy đủ toàn bộ ý của câu tiếng Trung gốc.",
            ref_vi or student_text,
            "Giữ tốt cấu trúc chủ - vị và ngữ cảnh giao tiếp.",
            {"y_nghia": 10, "tu_vung": 10, "dien_dat": 10, "nhan_loi": "Chuyển ngữ chuẩn xác"},
        )

    tokens = [w for w in _fold_vi(ref_vi).split() if len(w) >= 2]
    matched = sum(1 for w in set(tokens) if w in given_fold) if tokens else 0
    ratio = matched / max(1, len(set(tokens))) if tokens else 0.0
    score = round(max_score * min(1.0, ratio * 1.15), 1)
    passed = score >= float(q["nguong_dat"] or 6.0)
    y_score = min(10, max(1, round(ratio * 10)))
    tv_score = min(10, max(1, round(ratio * 10.5)))
    dd_score = min(10, max(2, round((score / max(1.0, max_score)) * 10)))
    comment = (
        "Bạn nắm được ý chính của câu gốc, chỉ cần trau chuốt thêm vài từ chi tiết để câu dịch tự nhiên hơn."
        if passed
        else "Bản dịch mới chạm được một phần ý hoặc còn thiếu thành phần quan trọng (chủ ngữ, thời gian hoặc động từ chính)."
    )
    reason = f"Đối chiếu với nghĩa chuẩn: “{ref_vi}”." if ref_vi else "Cần dịch đủ chủ ngữ, thời gian và động từ chính."
    tag = "Đạt ý chính câu dịch" if passed else ("Dịch thiếu ý cốt lõi" if ratio >= 0.25 else "Lệch nghĩa câu gốc")
    return score, comment, ref_vi or student_text, reason, {
        "y_nghia": y_score,
        "tu_vung": tv_score,
        "dien_dat": dd_score,
        "nhan_loi": tag,
    }


def _grade_translation_question(q: dict, options: dict, student_text: str) -> tuple[float, str, str, str, str, dict]:
    """Trả `(diem, nhan_xet, cau_sua, ly_do_sua, nguon, rubric_meta)` cho câu 7 (`dich_cau`)."""
    max_score = float(q["diem_toi_da"] or 10.0)
    ref_vi = (q.get("dich_nghia") or "").strip()
    rubric = (q.get("tieu_chi_mo_ta") or "Chấm theo mức độ truyền đạt đúng ý nghĩa câu tiếng Trung sang tiếng Việt.").strip()

    if ai_ready():
        prompt = (
            f"Câu tiếng Trung: {q['noi_dung']}\n"
            f"Pinyin: {q.get('pinyin') or ''}\n"
            f"Nghĩa tham chiếu: {ref_vi}\n"
            f"Tiêu chí chấm (thang 0..{max_score:g}, ngưỡng đạt {float(q['nguong_dat'] or 6):g}): {rubric}\n"
            f"Bản dịch của học viên: {student_text}\n\n"
            "Hãy đóng vai giám khảo HSK chuyên nghiệp (phong cách WriteMate AI): chấm sát nghĩa thực tế, "
            "đánh giá 3 tiêu chí thành phần thang 0..10 (y_nghia, tu_vung, dien_dat) và gắn nhãn chẩn đoán ngắn (nhan_loi, tối đa 5 từ).\n"
            'Chỉ trả JSON: {"diem": <so>, "y_nghia": <0..10>, "tu_vung": <0..10>, "dien_dat": <0..10>, '
            '"nhan_loi": "...", "nhan_xet": "...", "cau_sua": "...", "ly_do_sua": "..."}'
        )
        data = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
        if isinstance(data, dict) and isinstance(data.get("diem"), (int, float)):
            score = max(0.0, min(max_score, round(float(data["diem"]), 2)))
            norm10 = round((score / max(1.0, max_score)) * 10)
            y_sc = max(0, min(10, int(round(float(data.get("y_nghia", norm10))))))
            tv_sc = max(0, min(10, int(round(float(data.get("tu_vung", norm10))))))
            dd_sc = max(0, min(10, int(round(float(data.get("dien_dat", norm10))))))
            nhan_loi = str(data.get("nhan_loi") or ("Chuyển ngữ đạt chuẩn" if score >= float(q["nguong_dat"] or 6) else "Cần chỉnh diễn đạt dịch")).strip()[:80]
            nhan_xet = str(data.get("nhan_xet") or "Đã chấm theo tiêu chí ý nghĩa.").strip()[:500]
            cau_sua = str(data.get("cau_sua") or ref_vi or student_text).strip()[:500]
            ly_do = str(data.get("ly_do_sua") or "").strip()[:500]
            return score, nhan_xet, cau_sua, ly_do, "ai", {
                "y_nghia": y_sc,
                "tu_vung": tv_sc,
                "dien_dat": dd_sc,
                "nhan_loi": nhan_loi,
            }

    score, nhan_xet, cau_sua, ly_do, meta = _heuristic_translation_grade(q, options, student_text)
    return score, nhan_xet, cau_sua, ly_do, "code", meta


def _load_attempt_bundle(db: Session, luot_id: int, uid: int) -> tuple[dict, dict, list[dict], dict, dict, dict]:
    attempt = db.execute(
        text("""
            SELECT id, nguoi_dung_id, trang_thai, bat_dau_luc, nop_luc
            FROM luot_lam
            WHERE id = :id AND loai_boc_cau = 'danh_gia_dau_vao'
        """),
        {"id": luot_id},
    ).mappings().first()
    if attempt is None or int(attempt["nguoi_dung_id"]) != uid:
        raise NotFoundError()
    if attempt["trang_thai"] != "da_nop":
        raise ConflictError("Bài đánh giá chưa nộp xong")

    kqdv = db.execute(
        text("SELECT * FROM ket_qua_dau_vao WHERE luot_lam_id = :l"),
        {"l": luot_id},
    ).mappings().first()
    if kqdv is None:
        db.execute(text("INSERT IGNORE INTO ket_qua_dau_vao (luot_lam_id, trang_thai_phan_tich) VALUES (:l, 'chua')"), {"l": luot_id})
        db.commit()
        kqdv = db.execute(text("SELECT * FROM ket_qua_dau_vao WHERE luot_lam_id = :l"), {"l": luot_id}).mappings().one()

    ans_rows = [
        dict(r)
        for r in db.execute(
            text("""
                SELECT a.id, a.cau_hoi_id, a.thu_tu, a.cap_tham_do_id, a.trang_thai_thao_tac,
                       a.phuong_an_chon_id, a.van_ban, a.thoi_gian_lam_giay, a.phien_ban_luu,
                       v.diem, v.phien_ban_luu AS cham_phien_ban_luu, v.nhan_xet, v.cau_sua, v.ly_do_sua
                FROM cau_tra_loi a
                LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l
                ORDER BY a.thu_tu
            """),
            {"l": luot_id},
        ).mappings().all()
    ]
    questions, options = load_questions_by_ids(db, [int(a["cau_hoi_id"]) for a in ans_rows])
    # Bổ sung nhom_kien_thuc_id và tên nhóm kiến thức cho các câu hỏi
    q_meta = {
        int(r["id"]): dict(r)
        for r in db.execute(
            text("""
                SELECT q.id, q.nhom_kien_thuc_id, n.ten AS ten_nhom
                FROM cau_hoi q
                LEFT JOIN nhom_kien_thuc n ON n.id = q.nhom_kien_thuc_id
                WHERE q.id IN (SELECT cau_hoi_id FROM cau_tra_loi WHERE luot_lam_id = :l)
            """),
            {"l": luot_id},
        ).mappings().all()
    }
    for qid, meta in q_meta.items():
        if qid in questions:
            questions[qid].update(meta)

    levels = {
        int(r["id"]): dict(r)
        for r in db.execute(text("SELECT id, ma, ten, thu_tu FROM cap_do ORDER BY thu_tu")).mappings().all()
    }
    return dict(attempt), dict(kqdv), ans_rows, questions, options, levels


def _build_deterministic_insights(ans_rows: list[dict], questions: dict, levels: dict, start_lv: dict) -> list[dict]:
    """Sinh bộ nhận định sư phạm chuẩn xác kèm câu bằng chứng thật từ 8 câu làm bài (dự phòng hoặc bổ trợ AI)."""
    by_skill: dict[str, list[dict]] = {"tu_vung": [], "doc": [], "nghe": [], "viet": []}
    for a in ans_rows:
        q = questions[int(a["cau_hoi_id"])]
        pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
        dung = a["diem"] is not None and float(a["diem"]) >= pass_mark
        by_skill.setdefault(q["ky_nang"], []).append({
            "thu_tu": int(a["thu_tu"]),
            "trang_thai_thao_tac": a["trang_thai_thao_tac"],
            "dung": dung,
            "nhom_id": q.get("nhom_kien_thuc_id"),
            "ten_nhom": q.get("ten_nhom"),
            "cap_ten": levels.get(int(q["cap_do_id"]), {}).get("ten", "HSK"),
        })

    insights: list[dict] = []
    for skill in ("tu_vung", "doc", "nghe", "viet"):
        items = by_skill.get(skill, [])
        valid = [x for x in items if x["trang_thai_thao_tac"] != "loi_ky_thuat"]
        if not valid:
            continue
        right = [x for x in valid if x["trang_thai_thao_tac"] == "da_tra_loi" and x["dung"]]
        wrong_or_skip = [x for x in valid if x not in right]
        skill_name = SKILL_VI[skill]
        if len(right) == len(valid):
            caps = ", ".join(sorted({x["cap_ten"] for x in right}))
            insights.append({
                "ky_nang": skill,
                "nhom_kien_thuc_id": right[-1]["nhom_id"],
                "loai": "diem_manh",
                "noi_dung": f"Ở kỹ năng {skill_name}, bạn xử lý vững các câu thăm dò ({caps}).",
                "bang_chung": [x["thu_tu"] for x in right],
            })
        elif right and wrong_or_skip:
            weak = wrong_or_skip[0]
            topic = f" (nhóm {weak['ten_nhom']})" if weak["ten_nhom"] else ""
            insights.append({
                "ky_nang": skill,
                "nhom_kien_thuc_id": weak["nhom_id"],
                "loai": "nhan_xet",
                "noi_dung": f"{skill_name}: bạn nắm được phần cơ bản nhưng còn lúng túng ở mức {weak['cap_ten']}{topic}.",
                "bang_chung": [x["thu_tu"] for x in valid],
            })
        else:
            weak = wrong_or_skip[0]
            topic = f" đặc biệt ở chủ điểm {weak['ten_nhom']}" if weak["ten_nhom"] else ""
            insights.append({
                "ky_nang": skill,
                "nhom_kien_thuc_id": weak["nhom_id"],
                "loai": "diem_yeu",
                "noi_dung": f"{skill_name} là phần cần ưu tiên củng cố trước{topic}.",
                "bang_chung": [x["thu_tu"] for x in wrong_or_skip],
            })

    insights.append({
        "ky_nang": None,
        "nhom_kien_thuc_id": None,
        "loai": "nhan_xet",
        "noi_dung": f"Từ 8 câu thực tế, Xiang đề xuất bạn bắt đầu lộ trình ở {start_lv['ten']} để vừa sức và lấp chắc các điểm còn thiếu.",
        "bang_chung": [int(a["thu_tu"]) for a in ans_rows if a["trang_thai_thao_tac"] != "loi_ky_thuat"][:3],
    })
    return insights


def _answer_display_pair(a: dict, q: dict, options: dict) -> tuple[str | None, str | None]:
    chosen_text = a["van_ban"]
    right_text = q["dich_nghia"] if q["dang"] == "dich_cau" else " / ".join(o["noi_dung"] for o in options[q["id"]]["chap_nhan"])
    if q["dang"] in CHOICE_TYPES:
        opts = options[q["id"]]["lua_chon"]
        chosen_opt = next((o for o in opts if o["id"] == a["phuong_an_chon_id"]), None)
        right_id = correct_option_id(q, options)
        right_opt = next((o for o in opts if o["id"] == right_id), None)
        chosen_text = (chosen_opt["noi_dung"] or "(hình)") if chosen_opt else None
        right_text = (right_opt["noi_dung"] or "(hình)") if right_opt else None
    return chosen_text, right_text


def _build_diagnostic_rubric(
    q: dict,
    lv_name: str,
    trang_thai: str,
    dung: bool | None,
    diem: float | None,
    max_score: float,
    rubric_meta: dict | None = None,
    ai_tag: str | None = None,
    ai_tip: str | None = None,
) -> dict:
    """Dựng hồ sơ chẩn đoán đa tiêu chí kiểu WriteMate AI (nhãn lỗi, điểm độ hiểu 0..100, 3 thanh tiêu chí và mẹo ghi nhớ)."""
    dang = q["dang"]
    kn = q["ky_nang"]
    pinyin_hint = f"Phiên âm: {q['pinyin']}." if q.get("pinyin") else ""
    meaning_hint = f"Nghĩa chuẩn: “{q['dich_nghia']}”." if q.get("dich_nghia") else ""

    if trang_thai == "loi_ky_thuat":
        return {
            "muc_danh_gia": "loi_ky_thuat",
            "nhan_chan_doan": "Loại trừ sự cố kỹ thuật",
            "diem_do_hieu": None,
            "tieu_chi": [],
            "meo_ghi_nho": "Câu gặp lỗi âm thanh/hình ảnh không tính vào điểm yếu của bạn.",
        }

    if dang in ("viet_mo", "dich_cau"):
        if trang_thai == "bo_qua":
            return {
                "muc_danh_gia": "chua_biet",
                "nhan_chan_doan": "Chưa biết từ vựng / mẫu câu",
                "diem_do_hieu": 0,
                "tieu_chi": [
                    {"ten": "Độ chính xác ý nghĩa", "diem": 0, "toi_da": 10},
                    {"ten": "Từ vựng & Ngữ cảnh", "diem": 0, "toi_da": 10},
                    {"ten": "Diễn đạt tự nhiên", "diem": 0, "toi_da": 10},
                ],
                "meo_ghi_nho": ai_tip or f"{pinyin_hint} {meaning_hint}".strip() or "Ghi nhớ cụm động từ và chủ ngữ chính của câu.",
            }
        sc = float(diem or 0.0)
        pct = max(0, min(100, round(100 * sc / max(1.0, max_score))))
        m = rubric_meta or {}
        base10 = max(1, round(pct / 10)) if sc > 0 else 0
        return {
            "muc_danh_gia": "vung" if dung else "can_cung_co",
            "nhan_chan_doan": ai_tag or m.get("nhan_loi") or ("Chuyển ngữ chuẩn xác" if dung else "Cần trau chuốt bản dịch"),
            "diem_do_hieu": pct,
            "tieu_chi": [
                {"ten": "Độ chính xác ý nghĩa", "diem": int(m.get("y_nghia", base10)), "toi_da": 10},
                {"ten": "Từ vựng & Ngữ cảnh", "diem": int(m.get("tu_vung", base10)), "toi_da": 10},
                {"ten": "Diễn đạt tự nhiên", "diem": int(m.get("dien_dat", max(base10, 2 if sc > 0 else 0))), "toi_da": 10},
            ],
            "meo_ghi_nho": ai_tip or (q.get("giai_thich") or f"Khi dịch câu {lv_name}, hãy xác định cụm thời gian/địa điểm trước động từ chính.").strip(),
        }

    # Các câu khách quan & sắp xếp từ (1..6, 8)
    criteria_names = {
        "tu_vung": ("Nhận diện mặt chữ Hán", "Độ chuẩn nghĩa từ vựng", f"Phản xạ từ vựng {lv_name}"),
        "doc": ("Nắm bắt từ khóa câu", "Liên kết ngữ cảnh đọc", f"Đọc hiểu cấu trúc {lv_name}"),
        "nghe": ("Nhận diện âm & thanh điệu", "Bắt từ khóa thông tin", f"Phản xạ nghe {lv_name}"),
        "viet": ("Trật tự Chủ – Vị – Tân", "Vị trí trạng ngữ / trợ từ", f"Cấu trúc câu {lv_name}"),
    }.get(kn, ("Nhận diện trọng tâm", "Áp dụng ngữ cảnh", f"Mức độ vững {lv_name}"))

    if trang_thai == "bo_qua":
        scores = (0, 0, 0)
        default_tag = {
            "tu_vung": "Chưa biết từ vựng này",
            "doc": "Chưa đọc hiểu được câu",
            "nghe": "Chưa bắt được âm nghe",
            "viet": "Chưa nắm quy tắc ghép câu",
        }.get(kn, "Chưa biết kiến thức này")
        pct = 0
        verdict = "chua_biet"
    elif dung:
        scores = (10, 10, 10)
        default_tag = {
            "tu_vung": "Nắm chắc từ vựng cốt lõi",
            "doc": "Đọc hiểu ngữ cảnh chính xác",
            "nghe": "Nghe bắt ý chuẩn xác",
            "viet": "Nắm vững trật tự ngữ pháp",
        }.get(kn, "Nắm vững kiến thức")
        pct = 100
        verdict = "vung"
    else:
        scores = (4, 3, 2) if dang == "sap_xep" else (4, 2, 3)
        default_tag = {
            "tu_vung": "Nhầm nghĩa từ vựng",
            "doc": "Lệch thông tin trọng tâm",
            "nghe": "Nhầm từ khóa khi nghe",
            "viet": "Sai trật tự ngữ pháp câu",
        }.get(kn, "Nhầm lẫn điểm kiến thức")
        pct = 30
        verdict = "can_cung_co"

    default_tip = (
        q.get("giai_thich")
        or (f"Quy tắc câu Hán ngữ: Chủ ngữ + Thời gian/Địa điểm + Động từ ({meaning_hint})" if dang == "sap_xep" else f"{pinyin_hint} {meaning_hint}".strip())
        or f"Ôn kỹ chủ điểm {q.get('ten_nhom') or SKILL_VI.get(kn, kn)} ở cấp {lv_name}."
    )

    return {
        "muc_danh_gia": verdict,
        "nhan_chan_doan": ai_tag or default_tag,
        "diem_do_hieu": pct,
        "tieu_chi": [
            {"ten": criteria_names[0], "diem": scores[0], "toi_da": 10},
            {"ten": criteria_names[1], "diem": scores[1], "toi_da": 10},
            {"ten": criteria_names[2], "diem": scores[2], "toi_da": 10},
        ],
        "meo_ghi_nho": (ai_tip or default_tip).strip()[:320],
    }


def analyze_single_submitted_step(db: Session, answer_id: int) -> dict:
    """Chấm (nếu là câu dịch) và gọi AI phân tích sâu điểm yếu / độ hiểu kiểu WriteMate cho ĐÚNG CÂU VỪA LÀM ngay lập tức.
    Luôn đóng giao dịch đọc CSDL (`db.rollback()`) trước khi gọi OpenAI để không giữ kết nối MySQL khi AI suy luận.
    """
    row = db.execute(
        text("""
            SELECT a.id, a.luot_lam_id, a.cau_hoi_id, a.thu_tu, a.trang_thai_thao_tac,
                   a.phuong_an_chon_id, a.van_ban, a.phien_ban_luu,
                   v.diem, v.nhan_xet, v.cau_sua, v.ly_do_sua
            FROM cau_tra_loi a
            LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
            WHERE a.id = :id
        """),
        {"id": answer_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    a = dict(row)
    qid = int(a["cau_hoi_id"])
    questions, options = load_questions_by_ids(db, [qid])
    q = questions[qid]
    meta = db.execute(
        text("""
            SELECT q.nhom_kien_thuc_id, n.ten AS ten_nhom, cd.ten AS ten_cap
            FROM cau_hoi q
            LEFT JOIN nhom_kien_thuc n ON n.id = q.nhom_kien_thuc_id
            LEFT JOIN cap_do cd ON cd.id = q.cap_do_id
            WHERE q.id = :q
        """),
        {"q": qid},
    ).mappings().one()
    q.update(dict(meta))
    db.rollback()  # Giải phóng kết nối đọc trước khi gọi AI phân tích chuyên sâu câu này!

    pos = int(a["thu_tu"])
    lv_name = q.get("ten_cap") or "HSK"
    skill_label = SKILL_VI.get(q["ky_nang"], q["ky_nang"])
    topic_name = q.get("ten_nhom")
    topic_clause = f" thuộc chủ điểm «{topic_name}»" if topic_name else ""
    chosen_text, right_text = _answer_display_pair(a, q, options)
    max_score = float(q["diem_toi_da"] or (10.0 if q["dang"] in ("viet_mo", "dich_cau") else 1.0))
    pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0

    # 1. Nếu là câu Dịch (câu 7) có nhập văn bản -> chấm theo rubric 3 tiêu chí kiểu WriteMate ngay tại bước này
    if q["dang"] in ("viet_mo", "dich_cau") and a["trang_thai_thao_tac"] == "da_tra_loi" and a["van_ban"]:
        score, nx, cs, ld, nguon, r_meta = _grade_translation_grade_safe(q, options, a["van_ban"])
        next_lan = int(db.execute(
            text("SELECT COALESCE(MAX(lan), 0) + 1 FROM ket_qua_cham WHERE cau_tra_loi_id = :id"),
            {"id": answer_id},
        ).scalar_one())
        db.execute(
            text("""
                INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet, cau_sua, ly_do_sua)
                VALUES (:id, :lan, :ng, 'hoan_tat', :pbl, :d, :nx, :cs, :ld)
            """),
            {"id": answer_id, "lan": next_lan, "ng": nguon, "pbl": int(a["phien_ban_luu"]), "d": score, "nx": nx, "cs": cs, "ld": ld},
        )
        db.commit()
        dung = score >= pass_mark
        diag = _build_diagnostic_rubric(q, lv_name, a["trang_thai_thao_tac"], dung, score, max_score, rubric_meta=r_meta, ai_tip=ld or None)
        return {
            "thu_tu": pos,
            "ky_nang": q["ky_nang"],
            "dang": q["dang"],
            "ten_ky_nang": skill_label,
            "cap": lv_name,
            "nhom_kien_thuc": topic_name,
            "trang_thai_thao_tac": a["trang_thai_thao_tac"],
            "dung": dung,
            "la_diem_yeu": not dung,
            "diem": score,
            "diem_toi_da": max_score,
            "tra_loi": chosen_text,
            "dap_an_dung": right_text,
            "pinyin": q.get("pinyin"),
            "dich_nghia": q.get("dich_nghia"),
            "loi_nghe": q.get("loi_nghe"),
            "phan_tich_ai": nx,
            "cau_sua": cs,
            "ly_do_sua": ld,
            **diag,
        }

    # 2. Câu Bỏ qua hoặc câu Khách quan / Sắp xếp câu (1..6, 8)
    diem = float(a["diem"] or 0.0)
    dung = a["trang_thai_thao_tac"] == "da_tra_loi" and diem >= pass_mark
    ai_tag = None
    ai_tip = None

    if a["trang_thai_thao_tac"] == "bo_qua":
        fallback_note = (
            f"Bạn chủ động bấm Bỏ qua vì chưa gặp điểm kiến thức{topic_clause} ({lv_name}). "
            f"Đáp án chuẩn là «{right_text or ''}»"
            + (f" — nghĩa là: “{q['dich_nghia']}”." if q.get("dich_nghia") else ".")
            + " Xiang đã đánh dấu chính xác lỗ hổng này để ưu tiên bài ôn từ gốc cho bạn."
        )
        ai_note = None
        if ai_ready():
            prompt = (
                f"Học viên đang làm khảo sát đánh giá năng lực HSK thực tế (Câu {pos}/8, kỹ năng {skill_label}, cấp {lv_name}{topic_clause}).\n"
                f"Đề bài: {q.get('noi_dung') or q.get('loi_nghe') or ''}\n"
                f"Pinyin: {q.get('pinyin') or ''}\n"
                f"Nghĩa tiếng Việt: {q.get('dich_nghia') or ''}\n"
                f"Đáp án chuẩn: {right_text or ''}\n"
                "Thao tác của học viên: BẤM BỎ QUA (ràng buộc bắt buộc: học viên CHƯA BIẾT từ vựng/cấu trúc này).\n"
                "Hãy trả kết quả chẩn đoán chuyên nghiệp kiểu WriteMate AI (tiếng Việt, xưng 'Xiang' - 'bạn'):\n"
                "- nhan_loi: nhãn chẩn đoán súc tích 3–5 từ (vd: 'Chưa biết từ vựng cốt lõi')\n"
                "- phan_tich: 2 câu ngắn giải thích rõ từ/cấu trúc chưa biết và nghĩa của đáp án chuẩn\n"
                "- meo_ghi_nho: 1 câu quy tắc / mẹo nhớ nhanh kèm Pinyin hoặc cấu trúc.\n"
                'Chỉ trả JSON: {"nhan_loi": "...", "phan_tich": "...", "meo_ghi_nho": "..."}'
            )
            raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
            if isinstance(raw, dict) and str(raw.get("phan_tich") or "").strip():
                ai_note = str(raw["phan_tich"]).strip()[:600]
                ai_tag = str(raw.get("nhan_loi") or "").strip()[:80] or None
                ai_tip = str(raw.get("meo_ghi_nho") or "").strip()[:320] or None
        final_note = ai_note or fallback_note
    elif dung:
        meaning_part = f" (“{q['dich_nghia']}”)" if q.get("dich_nghia") and q["dang"] != "sap_xep" else ""
        fallback_note = (
            f"Bạn xử lý chính xác «{chosen_text or right_text}»{meaning_part}, "
            f"chứng tỏ nền tảng {skill_label.lower()}{topic_clause} ở cấp {lv_name} của bạn đã vững."
        )
        ai_note = None
        if ai_ready():
            prompt = (
                f"Học viên vừa trả lời ĐÚNG Câu {pos}/8 khảo sát đánh giá HSK thực tế ({skill_label}, {lv_name}{topic_clause}).\n"
                f"Đề bài: {q.get('noi_dung') or q.get('loi_nghe') or ''}\n"
                f"Pinyin: {q.get('pinyin') or ''}\n"
                f"Nghĩa: {q.get('dich_nghia') or ''}\n"
                f"Đáp án học viên chọn/ghép: {chosen_text or ''}\n"
                "Hãy nhận xét chuyên nghiệp kiểu WriteMate AI (tiếng Việt, xưng 'Xiang' - 'bạn'):\n"
                "- nhan_loi: nhãn năng lực đạt được 3–5 từ (vd: 'Nắm vững cấu trúc câu')\n"
                "- phan_tich: 1–2 câu khẳng định điểm từ vựng/ngữ pháp học viên đã làm chủ\n"
                "- meo_ghi_nho: 1 câu mở rộng ngắn gọn cách dùng trong giao tiếp HSK.\n"
                'Chỉ trả JSON: {"nhan_loi": "...", "phan_tich": "...", "meo_ghi_nho": "..."}'
            )
            raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
            if isinstance(raw, dict) and str(raw.get("phan_tich") or "").strip():
                ai_note = str(raw["phan_tich"]).strip()[:600]
                ai_tag = str(raw.get("nhan_loi") or "").strip()[:80] or None
                ai_tip = str(raw.get("meo_ghi_nho") or "").strip()[:320] or None
        final_note = ai_note or fallback_note
    else:
        fallback_note = (
            f"Phương án/câu trả lời «{chosen_text or '—'}» chưa khớp với ngữ cảnh của đề bài. "
            f"Xiang nhận thấy bạn đang nhầm lẫn ở điểm kiến thức{topic_clause} ({lv_name}); "
            f"nhóm kiến thức này đã được ghi nhận để ưu tiên bài ôn củng cố cho bạn."
        )
        ai_note = None
        if ai_ready():
            prompt = (
                f"Học viên vừa trả lời CHƯA ĐÚNG Câu {pos}/8 khảo sát đánh giá HSK ({skill_label}, {lv_name}{topic_clause}).\n"
                f"Đề bài: {q.get('noi_dung') or q.get('loi_nghe') or ''}\n"
                f"Pinyin: {q.get('pinyin') or ''}\n"
                f"Nghĩa tham chiếu nội bộ (KHÔNG tiết lộ thẳng ra câu trả lời): {q.get('dich_nghia') or ''}\n"
                f"Học viên trả lời: {chosen_text or ''}\n"
                f"Đáp án đúng nội bộ (TUYỆT ĐỐI KHÔNG nêu trực tiếp đáp án này): {right_text or ''}\n"
                "Hãy phân tích theo đúng triết lý Cambridge Write & Improve (tiếng Việt, xưng 'Xiang' - 'bạn', KHÔNG giải hộ / KHÔNG tiết lộ đáp án đúng):\n"
                "- nhan_loi: nhãn điểm yếu 3–5 từ (vd: 'Nhầm từ vựng chỉ màu sắc', 'Chưa nắm liên từ đối lập')\n"
                "- phan_tich: 2 câu giải thích vì sao lựa chọn của học viên chưa phù hợp ngữ cảnh và chỉ ra khía cạnh từ vựng/ngữ pháp học viên đang hiểu nhầm (không nói đáp án đúng là gì)\n"
                "- meo_ghi_nho: 1 câu định hướng chủ điểm cần ôn tập để khắc phục lỗ hổng này.\n"
                'Chỉ trả JSON: {"nhan_loi": "...", "phan_tich": "...", "meo_ghi_nho": "..."}'
            )
            raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
            if isinstance(raw, dict) and str(raw.get("phan_tich") or "").strip():
                ai_note = str(raw["phan_tich"]).strip()[:600]
                ai_tag = str(raw.get("nhan_loi") or "").strip()[:80] or None
                ai_tip = str(raw.get("meo_ghi_nho") or "").strip()[:320] or None
        final_note = ai_note or fallback_note

    kqc_id = db.execute(
        text("SELECT id FROM ket_qua_cham WHERE cau_tra_loi_id = :id ORDER BY lan DESC LIMIT 1"),
        {"id": answer_id},
    ).scalar_one_or_none()
    if kqc_id:
        db.execute(text("UPDATE ket_qua_cham SET nhan_xet = :nx WHERE id = :kid"), {"nx": final_note, "kid": int(kqc_id)})
        db.commit()

    diag = _build_diagnostic_rubric(q, lv_name, a["trang_thai_thao_tac"], dung, diem, max_score, ai_tag=ai_tag, ai_tip=ai_tip)
    return {
        "thu_tu": pos,
        "ky_nang": q["ky_nang"],
        "dang": q["dang"],
        "ten_ky_nang": skill_label,
        "cap": lv_name,
        "nhom_kien_thuc": topic_name,
        "trang_thai_thao_tac": a["trang_thai_thao_tac"],
        "dung": dung,
        "la_diem_yeu": (a["trang_thai_thao_tac"] == "bo_qua") or (not dung),
        "diem": diem,
        "diem_toi_da": max_score,
        "tra_loi": chosen_text,
        "dap_an_dung": right_text,
        "pinyin": q.get("pinyin"),
        "dich_nghia": q.get("dich_nghia"),
        "loi_nghe": q.get("loi_nghe"),
        "phan_tich_ai": final_note,
        "cau_sua": None,
        "ly_do_sua": None,
        **diag,
    }


def _build_per_question_comprehension(
    ans_rows: list[dict],
    questions: dict,
    options: dict,
    levels: dict,
) -> dict[int, str]:
    """Sinh phân tích độ hiểu cho từng câu 1..8:
    - Ràng buộc cứng: câu `bo_qua` (hoặc gửi trống) luôn được kết luận là 'Chưa biết', không phán đoán sai.
    - Câu có trả lời (`da_tra_loi`): nếu AI khả dụng sẽ phân tích sâu độ hiểu (đúng ở đâu / hiểu nhầm ở đâu),
      nếu AI tắt thì dùng bộ phân tích sư phạm tất định đối chiếu đáp án chọn và đáp án chuẩn.
    """
    deterministic: dict[int, str] = {}
    answered_for_ai: list[dict] = []

    for a in ans_rows:
        pos = int(a["thu_tu"])
        q = questions[int(a["cau_hoi_id"])]
        lv_name = levels.get(int(q["cap_do_id"]), {}).get("ten", "HSK")
        skill_label = SKILL_VI.get(q["ky_nang"], q["ky_nang"])
        topic = f" thuộc chủ điểm «{q['ten_nhom']}»" if q.get("ten_nhom") else ""
        chosen_text, right_text = _answer_display_pair(a, q, options)
        pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
        dung = a["diem"] is not None and float(a["diem"]) >= pass_mark

        if a["trang_thai_thao_tac"] == "loi_ky_thuat":
            deterministic[pos] = "Sự cố kỹ thuật âm thanh/hiển thị: câu này được loại trừ, không tính là chưa biết hay làm sai."
            continue

        if a["trang_thai_thao_tac"] == "bo_qua":
            # Ràng buộc cứng: Bỏ qua / để trống gửi luôn coi là Chưa biết
            deterministic[pos] = (
                f"Không biết (Đã bỏ qua): Bạn chưa nắm được từ vựng hoặc cấu trúc {skill_label.lower()} cấp {lv_name}{topic}. "
                f"Đáp án chuẩn của câu này là «{right_text or ''}»."
            )
            continue

        # Đã có câu trả lời thực tế -> phân tích độ hiểu
        if q["dang"] in ("viet_mo", "dich_cau") and a.get("nhan_xet"):
            deterministic[pos] = str(a["nhan_xet"])
        elif dung:
            meaning_hint = f" ({q['dich_nghia']})" if q.get("dich_nghia") and q["dang"] != "sap_xep" else ""
            deterministic[pos] = (
                f"Hiểu vững kiến thức {lv_name}: Bạn xác định chính xác «{chosen_text or right_text}»{meaning_hint}, "
                f"cho thấy nền tảng {skill_label.lower()}{topic} ở mức này đã chắc chắn."
            )
        else:
            explain = q.get("giai_thich") or (f"Nghĩa chuẩn: {q['dich_nghia']}." if q.get("dich_nghia") else "")
            deterministic[pos] = (
                f"Hiểu chưa trọn ({lv_name}): Bạn đưa ra đáp án «{chosen_text or '—'}», trong khi đáp án đúng là «{right_text or '—'}». "
                f"Điều này cho thấy bạn còn nhầm lẫn ở điểm kiến thức{topic}. {explain}".strip()
            )

        if q["dang"] not in ("viet_mo", "dich_cau"):
            answered_for_ai.append({
                "pos": pos,
                "skill": skill_label,
                "level": lv_name,
                "topic": q.get("ten_nhom") or "",
                "stem": q.get("noi_dung") or q.get("loi_nghe") or "",
                "meaning": q.get("dich_nghia") or "",
                "chosen": chosen_text or "",
                "right": right_text or "",
                "correct": dung,
            })

    if ai_ready() and answered_for_ai:
        prompt_lines = [
            "Hãy phân tích ngắn gọn ĐỘ HIỂU (1–2 câu tiếng Việt, xưng 'Xiang' - 'bạn') cho từng câu mà học viên CÓ ĐƯA ĐÁP ÁN dưới đây:",
            "- Nếu Đúng: nêu rõ học viên hiểu chắc từ vựng/ngữ pháp/ý nghe-đọc nào.",
            "- Nếu Sai: đối chiếu đáp án học viên chọn với đáp án đúng để chỉ rõ điểm hiểu nhầm và cách hiểu đúng.",
            "Danh sách câu đã trả lời:",
        ]
        for item in answered_for_ai:
            st = "Đúng" if item["correct"] else "Sai"
            prompt_lines.append(
                f"- Câu {item['pos']} ({item['skill']} {item['level']}, nhóm '{item['topic']}'): Đề='{item['stem']}' ({item['meaning']}) | "
                f"Học viên trả lời='{item['chosen']}' | Đáp án đúng='{item['right']}' | Kết quả={st}"
            )
        prompt_lines.append('Chỉ trả JSON mảng: [{"thu_tu": 1, "phan_tich": "..."}]')
        raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, "\n".join(prompt_lines))
        if isinstance(raw, list):
            valid_answered_pos = {x["pos"] for x in answered_for_ai}
            for row in raw:
                if isinstance(row, dict) and isinstance(row.get("thu_tu"), int) and row["thu_tu"] in valid_answered_pos:
                    txt = str(row.get("phan_tich") or "").strip()
                    if txt:
                        deterministic[row["thu_tu"]] = txt[:500]

    return deterministic


def _ask_ai_insights(ans_rows: list[dict], questions: dict, levels: dict, start_lv: dict) -> list[dict] | None:
    """Gọi AI phân tích tổng hợp và hậu kiểm nghiêm ngặt danh sách câu bằng chứng (AT38, AT52)."""
    if not ai_ready():
        return None
    tech_error_slots = {int(a["thu_tu"]) for a in ans_rows if a["trang_thai_thao_tac"] == "loi_ky_thuat"}
    valid_slots = {int(a["thu_tu"]) for a in ans_rows} - tech_error_slots
    if not valid_slots:
        return None

    lines = [
        f"Học viên vừa hoàn thành bài đánh giá đầu vào 8 câu HSK. Cấp bắt đầu đề xuất (do hệ thống tính): {start_lv['ten']}.",
        "RÀNG BUỘC BẮT BUỘC: Câu có trạng thái 'Không biết (Bỏ qua)' nghĩa là học viên hoàn toàn chưa biết kiến thức câu đó; câu có trả lời thì đánh giá mức độ hiểu.",
        "Tóm tắt 8 câu:",
    ]
    nhom_by_slot: dict[int, int | None] = {}
    for a in ans_rows:
        pos = int(a["thu_tu"])
        q = questions[int(a["cau_hoi_id"])]
        nhom_by_slot[pos] = q.get("nhom_kien_thuc_id")
        lv_name = levels.get(int(q["cap_do_id"]), {}).get("ten", "HSK")
        pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
        dung = a["diem"] is not None and float(a["diem"]) >= pass_mark
        state_str = (
            "Lỗi kỹ thuật (không tính lỗi kiến thức)"
            if a["trang_thai_thao_tac"] == "loi_ky_thuat"
            else "Không biết (Bỏ qua / để trống)"
            if a["trang_thai_thao_tac"] == "bo_qua"
            else ("Trả lời Đúng (hiểu bài)" if dung else "Trả lời Sai (hiểu nhầm)")
        )
        topic = f", nhóm '{q['ten_nhom']}'" if q.get("ten_nhom") else ""
        lines.append(f"- Câu {pos}: kỹ năng {q['ky_nang']}, {lv_name}{topic}, kết quả: {state_str}.")

    lines.append(
        "Hãy viết 3 đến 5 nhận định ngắn gọn bằng tiếng Việt dễ hiểu cho học viên (xưng 'Xiang' - 'bạn'). "
        "KHÔNG kết luận câu Lỗi kỹ thuật là yếu kiến thức. "
        'Chỉ trả JSON mảng: [{"ky_nang": "tu_vung|doc|nghe|viet|null", "loai": "diem_manh|diem_yeu|nhan_xet", '
        '"noi_dung": "...", "bang_chung": [1, 2]}]'
    )
    raw = json_completion(XIANG_JSON_SYSTEM_PROMPT, "\n".join(lines))
    if not isinstance(raw, list):
        return None

    cleaned: list[dict] = []
    for item in raw[:6]:
        if not isinstance(item, dict):
            continue
        kn = item.get("ky_nang")
        if kn not in ("tu_vung", "doc", "nghe", "viet", None):
            kn = None
        loai = item.get("loai")
        if loai not in ("diem_manh", "diem_yeu", "nhan_xet"):
            continue
        noi_dung = str(item.get("noi_dung") or "").strip()
        if not noi_dung:
            continue
        ev_raw = item.get("bang_chung") if isinstance(item.get("bang_chung"), list) else []
        ev = sorted({int(x) for x in ev_raw if isinstance(x, int) and int(x) in valid_slots})
        if not ev:
            continue
        first_nhom = next((nhom_by_slot.get(s) for s in ev if nhom_by_slot.get(s)), None)
        cleaned.append({
            "ky_nang": kn,
            "nhom_kien_thuc_id": first_nhom,
            "loai": loai,
            "noi_dung": noi_dung[:600],
            "bang_chung": ev,
        })
    return cleaned or None


def _pick_recommended_lessons(
    db: Session,
    uid: int,
    start_lv: dict,
    weak_skills: list[str],
    weak_nhom_ids: list[int],
) -> list[dict]:
    """Chọn tối đa 3 bài Ôn luyện cụ thể đang mở và đã đăng để lưu vào `goi_y_lo_trinh`."""
    lv_all = path_view.levels(db)
    order_skills = weak_skills + [s for s in ("tu_vung", "nghe", "doc", "viet") if s not in weak_skills]
    picks: list[dict] = []

    for skill in order_skills:
        if len(picks) >= 3:
            break
        opened = path_view.opened_levels(db, uid, skill, lv_all)
        # Ưu tiên cấp đề xuất nếu đã mở, nếu chưa mở thì lấy cấp mở cao nhất <= cấp đề xuất để học ngay được
        open_candidates = [
            lv for lv in lv_all
            if lv["thu_tu"] <= start_lv["thu_tu"] and path_view.level_open(lv, skill, opened)
        ]
        if not open_candidates:
            open_candidates = [lv for lv in lv_all if path_view.level_open(lv, skill, opened)]
        if not open_candidates:
            continue
        chosen_lv = open_candidates[-1]
        lands = path_view.build_map(db, uid, chosen_lv["id"], skill)
        open_slots = [
            {**slot, "ten_thua": land["ten"]}
            for land in lands
            for slot in land["o"]
            if slot.get("ma_goc_id") and slot["loai"] == "bai" and slot["trang_thai"] in ("dang_lam", "chua_dat", "chua_hoc")
        ]
        if not open_slots:
            continue
        chosen_slot = open_slots[0]
        bo_de_id = db.execute(
            text("SELECT id FROM bo_de WHERE ma_goc_id = :g AND trang_thai = 'da_dang' ORDER BY phien_ban DESC LIMIT 1"),
            {"g": chosen_slot["ma_goc_id"]},
        ).scalar_one_or_none()
        if not bo_de_id:
            continue
        reason = (
            f"Ưu tiên củng cố {SKILL_VI[skill]} tại {chosen_lv['ten']} ({chosen_slot['ten_thua']} · {chosen_slot['ten']})."
            if skill in weak_skills
            else f"Bài mở đầu phù hợp cho kỹ năng {SKILL_VI[skill]} tại {chosen_lv['ten']}."
        )
        picks.append({
            "ky_nang": skill,
            "nhom_kien_thuc_id": weak_nhom_ids[0] if weak_nhom_ids and skill in weak_skills else None,
            "bo_de_id": int(bo_de_id),
            "ly_do": reason,
        })
    return picks


def analyze_placement(db: Session, luot_id: int, uid: int) -> dict:
    """Thực thi chấm câu 7 (nếu chưa có kết quả khớp `phien_ban_luu`) và phân tích năng lực đầu vào."""
    attempt, kqdv, ans_rows, questions, options, levels = _load_attempt_bundle(db, luot_id, uid)
    if kqdv["trang_thai_phan_tich"] == "xong":
        db.rollback()
        return get_placement_result(db, luot_id, uid)

    if not _acquire_analysis(luot_id):
        db.rollback()
        return get_placement_result(db, luot_id, uid)

    try:
        db.execute(
            text("""
                UPDATE ket_qua_dau_vao
                SET trang_thai_phan_tich = 'dang', bat_dau_phan_tich_luc = NOW()
                WHERE luot_lam_id = :l
            """),
            {"l": luot_id},
        )
        db.commit()  # Kết thúc giao dịch ghi trạng thái trước khi gọi mạng tới AI!

        # Bước 1: Chấm câu 7 (`dich_cau`) nếu chưa có điểm hoàn tất khớp `phien_ban_luu` (AT36)
        for a in ans_rows:
            q = questions[int(a["cau_hoi_id"])]
            if q["dang"] not in ("viet_mo", "dich_cau"):
                continue
            if a["trang_thai_thao_tac"] != "da_tra_loi" or not a["van_ban"]:
                continue
            if a["diem"] is not None and a["cham_phien_ban_luu"] == a["phien_ban_luu"]:
                continue  # Dùng lại điểm đã chấm cho cùng phiên bản câu trả lời!

            score, nhan_xet, cau_sua, ly_do, nguon, _ = _grade_translation_grade_safe(q, options, a["van_ban"])
            next_lan = int(db.execute(
                text("SELECT COALESCE(MAX(lan), 0) + 1 FROM ket_qua_cham WHERE cau_tra_loi_id = :id"),
                {"id": a["id"]},
            ).scalar_one())
            db.execute(
                text("""
                    INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem, nhan_xet, cau_sua, ly_do_sua)
                    VALUES (:id, :lan, :ng, 'hoan_tat', :pbl, :d, :nx, :cs, :ld)
                """),
                {
                    "id": a["id"], "lan": next_lan, "ng": nguon,
                    "pbl": int(a["phien_ban_luu"]), "d": score,
                    "nx": nhan_xet, "cs": cau_sua, "ld": ly_do,
                },
            )
            db.commit()
            a["diem"] = score
            a["nhan_xet"] = nhan_xet
            a["cau_sua"] = cau_sua
            a["ly_do_sua"] = ly_do

        # Bước 2: Tính cấp bắt đầu đề xuất + ghi chú giới hạn dữ liệu (nếu có bỏ qua / lỗi kỹ thuật / cấp dự phòng)
        outcomes_for_level = []
        limit_notes: list[str] = []
        skipped_cnt = 0
        tech_cnt = 0
        for a in ans_rows:
            q = questions[int(a["cau_hoi_id"])]
            pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
            dung = a["diem"] is not None and float(a["diem"]) >= pass_mark
            actual_lv = levels.get(int(q["cap_do_id"]), {"thu_tu": 1, "ten": "HSK 1"})
            target_lv = levels.get(int(a["cap_tham_do_id"])) if a["cap_tham_do_id"] else actual_lv
            if target_lv and target_lv["id"] != actual_lv["id"]:
                limit_notes.append(f"Câu {a['thu_tu']} dùng câu dự phòng {actual_lv['ten']} thay cho {target_lv['ten']}.")
            if a["trang_thai_thao_tac"] == "bo_qua":
                skipped_cnt += 1
            elif a["trang_thai_thao_tac"] == "loi_ky_thuat":
                tech_cnt += 1
            outcomes_for_level.append({
                "trang_thai_thao_tac": a["trang_thai_thao_tac"],
                "dung": dung,
                "cap_thuc_te_thu_tu": actual_lv["thu_tu"],
            })

        if tech_cnt:
            limit_notes.insert(0, f"Có {tech_cnt} câu gặp sự cố kỹ thuật âm thanh/hình ảnh (đã loại trừ khỏi đánh giá lỗi kiến thức).")
        if skipped_cnt >= 3:
            limit_notes.insert(0, f"Bạn đã bỏ qua {skipped_cnt}/8 câu nên độ chính xác của đánh giá ban đầu có giới hạn.")

        levels_by_order = {lv["thu_tu"]: lv for lv in levels.values()}
        proposed_order = propose_starting_level_order(outcomes_for_level)
        start_lv = levels_by_order.get(proposed_order) or next(iter(levels.values()))

        db.rollback()  # Đảm bảo không giữ giao dịch trước khi gọi AI phân tích tổng hợp
        missing_per_q = [
            a for a in ans_rows
            if not (a.get("nhan_xet") or "").strip() or a.get("nhan_xet") == "Bạn đã bỏ qua câu dịch này."
        ]
        per_question_notes = (
            _build_per_question_comprehension(missing_per_q, questions, options, levels) if missing_per_q else {}
        )
        insights = _ask_ai_insights(ans_rows, questions, levels, start_lv) or _build_deterministic_insights(
            ans_rows, questions, levels, start_lv
        )

        # Bước 3: Bổ sung phân tích từng câu (nếu còn thiếu), lưu cấp xếp lớp 1..L và nhận định trong một giao dịch
        for a in missing_per_q:
            pos = int(a["thu_tu"])
            note_txt = per_question_notes.get(pos)
            if not note_txt:
                continue
            q = questions[int(a["cau_hoi_id"])]
            if q["dang"] in ("viet_mo", "dich_cau") and a["trang_thai_thao_tac"] == "da_tra_loi":
                continue
            has_kqc = db.execute(
                text("SELECT id FROM ket_qua_cham WHERE cau_tra_loi_id = :id ORDER BY lan DESC LIMIT 1"),
                {"id": a["id"]},
            ).scalar_one_or_none()
            if has_kqc:
                db.execute(
                    text("UPDATE ket_qua_cham SET nhan_xet = :nx WHERE id = :kid"),
                    {"nx": note_txt, "kid": int(has_kqc)},
                )

        ghi_chu = " ".join(limit_notes)[:1000] if limit_notes else None
        db.execute(
            text("""
                UPDATE ket_qua_dau_vao
                SET trang_thai_phan_tich = 'xong',
                    hoan_tat_phan_tich_luc = NOW(),
                    cap_de_xuat_id = :cap,
                    ghi_chu_gioi_han = :gc
                WHERE luot_lam_id = :l
            """),
            {"cap": start_lv["id"], "gc": ghi_chu, "l": luot_id},
        )

        weak_skills = [ins["ky_nang"] for ins in insights if ins["loai"] == "diem_yeu" and ins["ky_nang"]]
        weak_nhoms = [ins["nhom_kien_thuc_id"] for ins in insights if ins["loai"] == "diem_yeu" and ins["nhom_kien_thuc_id"]]
        rec_lessons = _pick_recommended_lessons(db, uid, start_lv, weak_skills, weak_nhoms)

        db.execute(text("DELETE FROM nhan_dinh_bang_chung WHERE luot_lam_id = :l"), {"l": luot_id})
        db.execute(text("DELETE FROM nhan_dinh_dau_vao WHERE luot_lam_id = :l"), {"l": luot_id})
        db.execute(text("DELETE FROM goi_y_lo_trinh WHERE luot_lam_id = :l"), {"l": luot_id})

        for idx, ins in enumerate(insights, start=1):
            db.execute(
                text("""
                    INSERT INTO nhan_dinh_dau_vao (luot_lam_id, thu_tu, ky_nang, nhom_kien_thuc_id, loai, noi_dung)
                    VALUES (:l, :t, :kn, :nhom, :loai, :nd)
                """),
                {
                    "l": luot_id,
                    "t": idx,
                    "kn": ins["ky_nang"],
                    "nhom": ins["nhom_kien_thuc_id"],
                    "loai": ins["loai"],
                    "nd": ins["noi_dung"],
                },
            )
            for slot_no in ins["bang_chung"]:
                db.execute(
                    text("""
                        INSERT IGNORE INTO nhan_dinh_bang_chung (luot_lam_id, thu_tu_nhan_dinh, thu_tu_cau)
                        VALUES (:l, :tn, :tc)
                    """),
                    {"l": luot_id, "tn": idx, "tc": slot_no},
                )

        for idx, rec in enumerate(rec_lessons, start=1):
            db.execute(
                text("""
                    INSERT INTO goi_y_lo_trinh (luot_lam_id, thu_tu, ky_nang, nhom_kien_thuc_id, ly_do, bo_de_id)
                    VALUES (:l, :t, :kn, :nhom, :ld, :bd)
                """),
                {
                    "l": luot_id,
                    "t": idx,
                    "kn": rec["ky_nang"],
                    "nhom": rec["nhom_kien_thuc_id"],
                    "ld": rec["ly_do"],
                    "bd": rec["bo_de_id"],
                },
            )

        db.execute(text("UPDATE luot_lam SET goi_y_luc = NOW() WHERE id = :l"), {"l": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        db.execute(
            text("UPDATE ket_qua_dau_vao SET trang_thai_phan_tich = 'loi' WHERE luot_lam_id = :l"),
            {"l": luot_id},
        )
        db.commit()
        raise
    finally:
        _release_analysis(luot_id)

    return get_placement_result(db, luot_id, uid)


def _grade_translation_grade_safe(q: dict, options: dict, student_text: str) -> tuple[float, str, str, str, str, dict]:
    try:
        return _grade_translation_question(q, options, student_text)
    except Exception:
        score, nx, cs, ld, meta = _heuristic_translation_grade(q, options, student_text)
        return score, nx, cs, ld, "code", meta


def get_placement_result(db: Session, luot_id: int, uid: int) -> dict:
    """Đọc màn hình kết quả Đánh giá đầu vào tách bạch rõ 4 phần + chỉ số tiêu chí kiểu WriteMate (AT09, AT35, AT37)."""
    attempt, kqdv, ans_rows, questions, options, levels = _load_attempt_bundle(db, luot_id, uid)

    # Tự động chuyển trạng thái 'dang' quá 60 giây thành 'loi' để hiện nút Thử lại (AT35)
    status = kqdv["trang_thai_phan_tich"]
    if status == "dang" and kqdv["bat_dau_phan_tich_luc"] is not None:
        expired = db.execute(
            text("SELECT TIMESTAMPDIFF(SECOND, :t, NOW()) > :lim"),
            {"t": kqdv["bat_dau_phan_tich_luc"], "lim": ANALYSIS_TIMEOUT_SECONDS},
        ).scalar_one()
        if expired and luot_id not in _analyzing_locks:
            db.execute(text("UPDATE ket_qua_dau_vao SET trang_thai_phan_tich = 'loi' WHERE luot_lam_id = :l"), {"l": luot_id})
            db.commit()
            status = "loi"

    # Phần chi tiết 8 câu kèm bộ chỉ số chẩn đoán WriteMate để hiển thị đồng nhất trên Báo cáo
    evidence_items = []
    skill_stats = {sk: {"ky_nang": sk, "ten_ky_nang": SKILL_VI[sk], "dung": 0, "tong": 0, "bo_qua": 0} for sk in ("tu_vung", "doc", "nghe", "viet")}

    for a in ans_rows:
        q = questions[int(a["cau_hoi_id"])]
        lv_name = levels.get(int(q["cap_do_id"]), {}).get("ten", "HSK")
        max_sc = float(q["diem_toi_da"]) if q["diem_toi_da"] is not None else (10.0 if q["dang"] in ("viet_mo", "dich_cau") else 1.0)
        pass_mark = float(q["nguong_dat"] or 6.0) if q["dang"] in ("viet_mo", "dich_cau") else 1.0
        diem_val = float(a["diem"]) if a["diem"] is not None else None
        dung = diem_val is not None and diem_val >= pass_mark
        chosen_text, right_text = _answer_display_pair(a, q, options)
        diag = _build_diagnostic_rubric(
            q,
            lv_name,
            a["trang_thai_thao_tac"],
            None if a["trang_thai_thao_tac"] == "loi_ky_thuat" else dung,
            diem_val,
            max_sc,
            ai_tip=a.get("ly_do_sua") or None,
        )
        if a["trang_thai_thao_tac"] != "loi_ky_thuat" and q["ky_nang"] in skill_stats:
            st_sk = skill_stats[q["ky_nang"]]
            st_sk["tong"] += 1
            if a["trang_thai_thao_tac"] == "bo_qua":
                st_sk["bo_qua"] += 1
            elif dung:
                st_sk["dung"] += 1

        evidence_items.append({
            "thu_tu": int(a["thu_tu"]),
            "ky_nang": q["ky_nang"],
            "ten_ky_nang": SKILL_VI.get(q["ky_nang"], q["ky_nang"]),
            "dang": q["dang"],
            "cap": lv_name,
            "nhom_kien_thuc": q.get("ten_nhom"),
            "noi_dung": q["noi_dung"],
            "pinyin": q["pinyin"],
            "loi_nghe": q["loi_nghe"],
            "dich_nghia": q["dich_nghia"],
            "trang_thai_thao_tac": a["trang_thai_thao_tac"],
            "tra_loi": chosen_text,
            "dap_an_dung": right_text,
            "dung": None if a["trang_thai_thao_tac"] == "loi_ky_thuat" else dung,
            "diem": diem_val,
            "diem_toi_da": max_sc,
            "thoi_gian_lam_giay": a["thoi_gian_lam_giay"],
            "nhan_xet": a["nhan_xet"],
            "phan_tich_ai": a["nhan_xet"],
            "cau_sua": a["cau_sua"],
            "ly_do_sua": a["ly_do_sua"],
            "giai_thich": q["giai_thich"],
            **diag,
        })

    ky_nang_thong_ke = [
        {
            **v,
            "phan_tram": round(100 * v["dung"] / v["tong"]) if v["tong"] > 0 else 0,
        }
        for v in skill_stats.values()
    ]

    # Phần 1: Nhận định năng lực kèm liên kết câu bằng chứng
    nd_rows = db.execute(
        text("""
            SELECT nd.thu_tu, nd.ky_nang, nd.nhom_kien_thuc_id, n.ten AS ten_nhom, nd.loai, nd.noi_dung
            FROM nhan_dinh_dau_vao nd
            LEFT JOIN nhom_kien_thuc n ON n.id = nd.nhom_kien_thuc_id
            WHERE nd.luot_lam_id = :l
            ORDER BY nd.thu_tu
        """),
        {"l": luot_id},
    ).mappings().all()
    bc_rows = db.execute(
        text("SELECT thu_tu_nhan_dinh, thu_tu_cau FROM nhan_dinh_bang_chung WHERE luot_lam_id = :l ORDER BY thu_tu_cau"),
        {"l": luot_id},
    ).all()
    bc_map: dict[int, list[int]] = {}
    for tn, tc in bc_rows:
        bc_map.setdefault(int(tn), []).append(int(tc))

    nhan_dinh = [
        {
            "thu_tu": int(r["thu_tu"]),
            "ky_nang": r["ky_nang"],
            "ten_nhom": r["ten_nhom"],
            "loai": r["loai"],
            "noi_dung": r["noi_dung"],
            "bang_chung": bc_map.get(int(r["thu_tu"]), []),
        }
        for r in nd_rows
    ]

    # Phần 2: Cấp bắt đầu đề xuất + nút kiểm tra mở cấp nếu cấp đó ở kỹ năng tương ứng đang khóa
    cap_de_xuat = levels.get(int(kqdv["cap_de_xuat_id"])) if kqdv["cap_de_xuat_id"] else None
    lv_list = path_view.levels(db)
    unlock_actions = []
    if cap_de_xuat:
        for skill in ("tu_vung", "nghe", "doc", "viet"):
            sk_lvs = path_view.skill_levels(db, skill)
            if not any(l["id"] == cap_de_xuat["id"] for l in sk_lvs):
                continue
            opened = path_view.opened_levels(db, uid, skill, sk_lvs)
            if not path_view.level_open(cap_de_xuat, skill, opened):
                info = level_test_service.start_info(db, uid, skill, cap_de_xuat, sk_lvs)
                unlock_actions.append({
                    "ky_nang": skill,
                    "ten_ky_nang": SKILL_VI[skill],
                    "cap_do_id": cap_de_xuat["id"],
                    "ten_cap": cap_de_xuat["ten"],
                    "duoc_lam_bat_dau_cap": info["duoc_lam"],
                    "ly_do_chua_mo_kiem_tra": info["ly_do"],
                })

    # Phần 3: Bài ôn cụ thể được đề xuất từ `goi_y_lo_trinh`
    rec_rows = db.execute(
        text("""
            SELECT g.thu_tu, g.ky_nang, g.ly_do, b.ma_goc_id, b.ten AS ten_bai,
                   t.ten AS ten_thua, cd.ten AS ten_cap
            FROM goi_y_lo_trinh g
            JOIN bo_de b ON b.id = g.bo_de_id
            LEFT JOIN bo_de t ON t.ma_goc_id = b.thua_id AND t.trang_thai = 'da_dang'
            LEFT JOIN cap_do cd ON cd.id = t.cap_do_id
            WHERE g.luot_lam_id = :l
            ORDER BY g.thu_tu
        """),
        {"l": luot_id},
    ).mappings().all()
    bai_de_xuat = [dict(r) for r in rec_rows]

    # Phần 4: Danh sách cấp hiện đã mở theo từng kỹ năng + mục tiêu HSK của học viên
    cap_da_mo = []
    for skill in ("tu_vung", "nghe", "doc", "viet"):
        sk_lvs = path_view.skill_levels(db, skill)
        opened = path_view.opened_levels(db, uid, skill, sk_lvs)
        open_names = [l["ten"] for l in sk_lvs if path_view.level_open(l, skill, opened)]
        cap_da_mo.append({"ky_nang": skill, "ten_ky_nang": SKILL_VI[skill], "cac_cap_da_mo": open_names})

    user_goal = db.execute(
        text("SELECT ks_cap_muc_tieu_id, ks_phut_moi_ngay FROM nguoi_dung WHERE id = :u"),
        {"u": uid},
    ).mappings().one()
    db.rollback()

    right_count = sum(1 for c in evidence_items if c["dung"] is True)
    valid_count = sum(1 for c in evidence_items if c["trang_thai_thao_tac"] != "loi_ky_thuat")

    return {
        "luot_id": luot_id,
        "nop_luc": attempt["nop_luc"],
        "trang_thai_phan_tich": status,
        "ghi_chu_gioi_han": kqdv["ghi_chu_gioi_han"],
        "tong_quan_diem": {"so_cau_dung": right_count, "so_cau_hop_le": valid_count, "tong_so_cau": len(evidence_items)},
        "phan_1_nhan_dinh": nhan_dinh,
        "phan_2_cap_de_xuat": {
            "cap_do": cap_de_xuat,
            "tuyen_bo": (
                f"Hệ thống đã xếp bạn vào trình độ {cap_de_xuat['ten']} từ 8 câu thực tế: mở khóa lộ trình từ HSK 1 đến {cap_de_xuat['ten']} ở cả 4 kỹ năng "
                f"và khóa các cấp cao hơn để bạn học chắc nền tảng (hoàn thành lộ trình hoặc thi Vượt cấp để mở cấp kế tiếp)."
                if cap_de_xuat
                else "Kết quả đánh giá trình độ đầu vào của bạn."
            ),
            "kiem_tra_mo_cap": unlock_actions,
        },
        "phan_3_bai_nen_hoc": bai_de_xuat,
        "phan_4_cap_da_mo": cap_da_mo,
        "muc_tieu_hien_tai": {
            "cap_muc_tieu_id": user_goal["ks_cap_muc_tieu_id"],
            "phut_moi_ngay": user_goal["ks_phut_moi_ngay"],
            "danh_sach_cap": lv_list,
        },
        "ky_nang_thong_ke": ky_nang_thong_ke,
        "chi_tiet_8_cau": evidence_items,
    }
