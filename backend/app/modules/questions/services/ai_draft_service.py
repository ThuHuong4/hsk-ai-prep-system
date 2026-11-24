"""Giảng viên dùng AI soạn câu hỏi (Mục 11 nghiệp vụ bổ sung).

Luồng: Giảng viên nhập yêu cầu -> AI soạn lô bản nháp + tự gắn nhóm kiến thức + tự soát lỗi
-> Giảng viên trao đổi với AI để chỉnh từng câu (AI chỉ ĐỀ XUẤT bản sửa) -> Giảng viên bấm Duyệt mới lưu & đăng.
- Soạn, soát lỗi, trao đổi: KHÔNG ghi CSDL. Chỉ bước Duyệt mới ghi (lưu + đăng, ghi người duyệt, thời điểm duyệt).
- Đóng giao dịch CSDL trước khi gọi AI (không giữ kết nối MySQL lúc chờ mạng).
- AI lỗi: báo lỗi, không tạo câu giả. Soát lỗi thất bại: đánh dấu "chưa soát" để Giảng viên tự kiểm tra.
- Câu Nghe: AI chỉ viết lời thoại; phải tải tệp âm thanh thật mới duyệt được.
"""
import json
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiNotConfiguredError,
    AiProviderError,
    ai_ready,
    chat_completion,
    is_real_openai_endpoint,
    parse_json_reply,
)
from app.modules.questions.schemas.question_payload import AI_DRAFT_TYPES, AiChatIn, AiDraftIn, AiSuggestIn, QuestionIn
from app.modules.questions.services.errors import ConflictError
from app.modules.questions.services.question_rules import DANG_LABELS, QuestionRuleError, validate_question
from app.modules.questions.services.quality_service import find_similar
from app.modules.questions.services.question_status import publish_question
from app.modules.questions.services.save_question import create_question

SKILL_VI = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}
BATCH = 5  # mỗi lần gọi AI soạn tối đa 5 câu (tránh quá thời gian chờ 30 giây)

SYSTEM_PROMPT = (
    "Bạn là chuyên gia soạn đề luyện thi HSK cho người Việt. Bạn chỉ soạn BẢN NHÁP để giảng viên kiểm tra. "
    "Nội dung tiếng Trung là chữ Hán giản thể, đúng ngữ pháp, dùng từ vựng trong phạm vi cấp HSK được yêu cầu. "
    "Giải thích và gợi ý viết bằng tiếng Việt. Không ghi đây là đề thi chính thức. Chỉ trả JSON hợp lệ."
)
REVIEW_PROMPT = (
    "Bạn là giám khảo phản biện đề HSK. Soát từng câu và chỉ nêu lỗi THẬT SỰ có, bằng tiếng Việt, ngắn gọn. "
    "Chỉ trả JSON hợp lệ."
)

_SHAPES = {
    "chon_mot": '"noi_dung": "đề bài", "phuong_an": ["A", "B", "C"], "dap_an_dung": 1  (số thứ tự phương án đúng, từ 1; 3-4 phương án)',
    "dung_sai": '"noi_dung": "câu nhận định cần xét đúng/sai", "dap_an_dung": true',
    "sap_xep": '"noi_dung": "yêu cầu sắp xếp", "manh": ["mảnh 1", "mảnh 2", "mảnh 3"] (đã xáo trộn), "cau_dung": ["câu đúng", "cách sắp xếp đúng khác nếu có"]',
    "dien_chu": '"noi_dung": "câu có chỗ trống ___", "dap_an": ["đáp án chấp nhận"]',
    "viet_mo": '"noi_dung": "đề bài viết", "tu_bat_buoc": "từ phải dùng (<= 6 chữ, có thể rỗng)", "tieu_chi": "tiêu chí chấm", "cau_mau": "câu mẫu tham khảo"',
    "dich_cau": '"noi_dung": "câu tiếng Trung cần dịch sang tiếng Việt", "ban_dich_mau": ["bản dịch tiếng Việt chấp nhận"], "tieu_chi": "tiêu chí chấm theo ý chính"',
}
_COMMON = (
    '"pinyin": "pinyin của phần tiếng Trung", "dich_nghia": "nghĩa tiếng Việt", '
    '"mo_ta_hinh": "mô tả ngắn bức tranh minh họa tình huống bằng tiếng Việt (để trống nếu câu chỉ dùng chữ)", '
    '"giai_thich": "giải thích đáp án", "goi_y": "gợi ý mức 1: nhắc điều cần chú ý, KHÔNG lộ đáp án", '
    '"goi_y_2": "gợi ý mức 2: thêm một bước phân tích, KHÔNG nêu đáp án", "nhom_ma": "mã nhóm kiến thức phù hợp nhất hoặc rỗng"'
)
# Trường nội dung AI được phép sửa khi trao đổi (phân loại, cờ dùng, nguồn giữ nguyên)
_CONTENT_FIELDS = ("noi_dung", "pinyin", "dich_nghia", "giai_thich", "goi_y", "goi_y_2", "loi_nghe",
                   "mo_ta_hinh", "tu_bat_buoc", "tieu_chi_mo_ta")
_LIMITS = {"goi_y": 2000, "goi_y_2": 2000, "mo_ta_hinh": 1000, "tu_bat_buoc": 20}


class AiDraftError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------- tiện ích chung

def _text(value, limit: int = 5000) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    value = str(value).strip()
    return value[:limit] or None


def _str_list(value, limit: int = 1000, max_items: int = 10) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    items = [_text(v, limit) for v in value]
    return [v for v in items if v][:max_items]


def _ask_json(system: str, messages: list[dict]) -> object:
    """Gọi AI và bóc JSON; lỗi thì ném AiDraftError (không tạo dữ liệu giả)."""
    if not ai_ready():
        raise AiDraftError("Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong backend/.env)", 503)
    try:
        reply = chat_completion(system, messages)
    except AiNotConfiguredError as error:
        raise AiDraftError(str(error) or "Chưa cấu hình AI", 503) from error
    except AiProviderError as error:
        raise AiDraftError(str(error) or "Dịch vụ AI đang lỗi hoặc quá thời gian chờ, vui lòng thử lại", 502) from error
    try:
        return parse_json_reply(reply)
    except ValueError as error:
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502) from error


def _level_name(db: Session, cap_do_id: int) -> str:
    name = db.execute(text("SELECT ten FROM cap_do WHERE id = :id"), {"id": cap_do_id}).scalar_one_or_none()
    if name is None:
        raise AiDraftError("Cấp độ không tồn tại", 422)
    return str(name)


def _groups(db: Session) -> list[dict]:
    rows = db.execute(text("SELECT id, ma, ten FROM nhom_kien_thuc WHERE trang_thai = 'hoat_dong' ORDER BY ten")).mappings().all()
    return [dict(r) for r in rows]


def _groups_hint(groups: list[dict]) -> str:
    if not groups:
        return ""
    return "\n- Nhóm kiến thức được phép (nhom_ma: tên): " + "; ".join(f"{g['ma']}: {g['ten']}" for g in groups)


def _group_id(groups: list[dict], ma) -> int | None:
    ma = _text(ma, 50)
    return next((g["id"] for g in groups if g["ma"] == ma), None) if ma else None


def _rule_error(payload: dict) -> str | None:
    """Kiểm tra đủ thành phần theo dạng câu; trả lỗi (tiếng Việt) hoặc None nếu hợp lệ."""
    try:
        validate_question(QuestionIn.model_validate(payload))
    except QuestionRuleError as error:
        return error.message
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(p) for p in first.get("loc", ()))
        return f"Dữ liệu chưa hợp lệ ở {where}: {first.get('msg', '')}"
    return None


def _notes(payload: dict) -> list[str]:
    if payload["ky_nang"] == "nghe" and not payload.get("tep_audio"):
        return ["Câu Nghe: bấm “Tạo giọng đọc AI” (miễn phí) hoặc tải tệp âm thanh lên, nghe kiểm tra trước khi duyệt."]
    return []


def _card(payload: dict, issues: list[str] | None) -> dict:
    """Một thẻ câu cho màn hình duyệt: loi = thiếu thành phần; van_de_ai = AI soát (None = chưa soát được);
    trung_lap = câu đã có trong ngân hàng gần giống (điền sau bởi _attach_duplicates)."""
    return {"cau_hoi": payload, "loi": _rule_error(payload), "van_de_ai": issues, "luu_y": _notes(payload), "trung_lap": []}


def _attach_duplicates(db: Session, cards: list[dict]) -> list[dict]:
    """Gắn danh sách câu gần trùng trong ngân hàng (bằng chứng không sao chép / không soạn lặp)."""
    if cards:
        for card, similar in zip(cards, find_similar(db, [c["cau_hoi"] for c in cards])):
            card["trung_lap"] = similar
    return cards


# ---------------------------------------------------------------- dựng payload

def _build_payload(req: AiDraftIn, raw: dict, groups: list[dict]) -> dict:
    """Dựng payload đúng chuẩn QuestionIn từ một câu AI trả về."""
    payload = {
        "dang": req.dang, "cap_do_id": req.cap_do_id, "ky_nang": req.ky_nang,
        "dung_on_luyen": True, "dung_thi_thu": req.dung_thi_thu, "dung_dau_vao": False,
        "tu_vung_id": None, "nguon_noi_dung": "soan_voi_ai",
        "nhom_kien_thuc_id": _group_id(groups, raw.get("nhom_ma")),
        "noi_dung": _text(raw.get("noi_dung")), "pinyin": _text(raw.get("pinyin")),
        "dich_nghia": _text(raw.get("dich_nghia")), "giai_thich": _text(raw.get("giai_thich")),
        "goi_y": _text(raw.get("goi_y"), 2000), "goi_y_2": _text(raw.get("goi_y_2"), 2000),
        "loi_nghe": _text(raw.get("loi_nghe")) if req.ky_nang == "nghe" else None,
        "tep_audio": None, "tep_hinh": None, "mo_ta_hinh": _text(raw.get("mo_ta_hinh"), 1000),
        "tu_bat_buoc": None, "tieu_chi_mo_ta": None, "diem_toi_da": None, "nguong_dat": None,
        "dap_an_thu_tu": None, "phuong_an": [], "dap_an_chap_nhan": [], "cau_con": [],
    }
    if req.dang == "chon_mot":
        options = _str_list(raw.get("phuong_an"), max_items=6)
        correct = raw.get("dap_an_dung")
        correct = correct if isinstance(correct, int) and not isinstance(correct, bool) else 0
        payload["phuong_an"] = [{"noi_dung": o, "tep_hinh": None, "la_dap_an_dung": i == correct}
                                for i, o in enumerate(options, start=1)]
    elif req.dang == "dung_sai":
        right = raw.get("dap_an_dung") if isinstance(raw.get("dap_an_dung"), bool) else None
        payload["phuong_an"] = _true_false(right)
    elif req.dang == "sap_xep":
        payload["phuong_an"] = [{"noi_dung": o, "tep_hinh": None, "la_dap_an_dung": False}
                                for o in _str_list(raw.get("manh"), max_items=12)]
        payload["dap_an_chap_nhan"] = _str_list(raw.get("cau_dung"))
    elif req.dang == "dien_chu":
        payload["dap_an_chap_nhan"] = _str_list(raw.get("dap_an"))
    elif req.dang == "viet_mo":
        payload.update({"tu_bat_buoc": _text(raw.get("tu_bat_buoc"), 20), "tieu_chi_mo_ta": _text(raw.get("tieu_chi")),
                        "diem_toi_da": 10, "nguong_dat": 6})
        sample = _text(raw.get("cau_mau"))
        if sample:
            payload["giai_thich"] = "\n".join(p for p in (payload["giai_thich"], f"Câu mẫu: {sample}") if p)
    elif req.dang == "dich_cau":
        payload.update({"tieu_chi_mo_ta": _text(raw.get("tieu_chi")), "diem_toi_da": 10, "nguong_dat": 6,
                        "dap_an_chap_nhan": _str_list(raw.get("ban_dich_mau"))})
    _fix_hints(payload)
    return payload


def _true_false(right: bool | None) -> list[dict]:
    return [{"noi_dung": "Đúng", "tep_hinh": None, "la_dap_an_dung": right is True},
            {"noi_dung": "Sai", "tep_hinh": None, "la_dap_an_dung": right is False}]


def _fix_hints(payload: dict) -> None:
    if payload.get("goi_y_2") and not payload.get("goi_y"):
        payload["goi_y"], payload["goi_y_2"] = payload["goi_y_2"], None


def _merge_revision(original: dict, revised: dict, groups: list[dict]) -> dict:
    """Ghép bản AI đề xuất vào câu gốc: chỉ nhận trường nội dung/đáp án, giữ nguyên phân loại và nguồn."""
    merged = dict(original)
    for field in _CONTENT_FIELDS:
        if field in revised:
            merged[field] = _text(revised.get(field), _LIMITS.get(field, 5000))
    if original["ky_nang"] != "nghe":
        merged["loi_nghe"] = original.get("loi_nghe")
    dang = original["dang"]
    if dang in ("chon_mot", "sap_xep") and isinstance(revised.get("phuong_an"), list):
        options = []
        for o in revised["phuong_an"][:12]:
            content = _text(o.get("noi_dung") if isinstance(o, dict) else o, 1000)
            if content:
                correct = bool(o.get("la_dap_an_dung")) if isinstance(o, dict) and dang == "chon_mot" else False
                options.append({"noi_dung": content, "tep_hinh": None, "la_dap_an_dung": correct})
        merged["phuong_an"] = options
    elif dang == "dung_sai" and isinstance(revised.get("phuong_an"), list) and len(revised["phuong_an"]) == 2:
        first = revised["phuong_an"][0]
        merged["phuong_an"] = _true_false(bool(first.get("la_dap_an_dung")) if isinstance(first, dict) else None)
    if dang in ("sap_xep", "dien_chu", "dich_cau") and "dap_an_chap_nhan" in revised:
        merged["dap_an_chap_nhan"] = _str_list(revised.get("dap_an_chap_nhan"))
    if dang != "viet_mo":
        merged["tu_bat_buoc"] = None
    if dang not in ("viet_mo", "dich_cau"):
        merged["tieu_chi_mo_ta"] = None
    if "nhom_ma" in revised:
        merged["nhom_kien_thuc_id"] = _group_id(groups, revised.get("nhom_ma"))
    merged["nguon_noi_dung"] = "soan_voi_ai"
    _fix_hints(merged)
    return merged


# ---------------------------------------------------------------- soát lỗi

def _review_view(payload: dict, level: str) -> dict:
    keys = ("dang", "ky_nang", "noi_dung", "loi_nghe", "pinyin", "dich_nghia", "phuong_an", "dap_an_chap_nhan",
            "tu_bat_buoc", "tieu_chi_mo_ta", "giai_thich", "goi_y", "goi_y_2")
    view = {k: payload.get(k) for k in keys if payload.get(k) not in (None, [], "")}
    view["cap"] = level
    return view


def _review(payloads: list[dict], level: str) -> list[list[str] | None]:
    """AI soát lỗi; trả danh sách vấn đề theo từng câu ([] = sạch, None = chưa soát được)."""
    if not payloads:
        return []
    prompt = (
        "Soát các câu sau theo 5 tiêu chí: (1) đáp án đúng có thật sự duy nhất và đúng không, "
        "(2) có phương án gây tranh cãi hoặc hai phương án cùng đúng không, (3) từ vựng/ngữ pháp có vượt cấp không, "
        "(4) gợi ý có làm lộ đáp án không, (5) chữ Hán, pinyin, nghĩa tiếng Việt có sai không.\n"
        f"Câu (JSON): {json.dumps([_review_view(p, level) for p in payloads], ensure_ascii=False)}\n"
        'Trả JSON: {"ket_qua": [{"stt": 1, "van_de": ["mô tả lỗi"]}]} — câu không có lỗi để "van_de": [].'
    )
    try:
        data = _ask_json(REVIEW_PROMPT, [{"role": "user", "content": prompt}])
    except AiDraftError:
        return [None] * len(payloads)
    rows = data.get("ket_qua") if isinstance(data, dict) else None
    result: list[list[str] | None] = [None] * len(payloads)
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("stt"), int) and 1 <= row["stt"] <= len(payloads):
                result[row["stt"] - 1] = _str_list(row.get("van_de"), 500, 8)
    return result


# ---------------------------------------------------------------- 1. soạn lô

def _generate_batch(req: AiDraftIn, level: str, groups: list[dict], count: int, part: int, parts: int) -> list[dict]:
    listening = (
        '\n- Đây là câu Nghe: thêm trường "loi_nghe" là lời thoại/đoạn nghe tiếng Trung (hội thoại thì mỗi lượt một dòng '
        'bắt đầu bằng "男：" hoặc "女：", câu hỏi cuối ghi "问：" để hệ thống đọc đa giọng Nam/Nữ/Hỏi như đề HSK thật); '
        '"noi_dung" là câu hỏi hoặc nhận định in trên đề.'
        if req.ky_nang == "nghe" else ""
    )
    extra = f"\n- Yêu cầu thêm của giảng viên: {req.yeu_cau}" if req.yeu_cau else ""
    topic = req.chu_de or "tự chọn các chủ đề quen thuộc, đa dạng, đúng phạm vi cấp này"
    split = f"\n- Đây là phần {part}/{parts}: chọn tình huống khác các phần khác để không trùng câu." if parts > 1 else ""
    prompt = (
        f"Soạn {count} câu hỏi {level}, kỹ năng {SKILL_VI[req.ky_nang]}, dạng \"{DANG_LABELS[req.dang]}\", "
        f"chủ đề: {topic}.{extra}{listening}{split}{_groups_hint(groups)}\n"
        "- Mỗi câu khác nhau, độ khó vừa với cấp đã nêu.\n"
        f'Trả về JSON: {{"cau_hoi": [{{ {_SHAPES[req.dang]}, {_COMMON} }}]}}'
    )
    data = _ask_json(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
    items = data.get("cau_hoi") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    payloads = [_build_payload(req, raw, groups) for raw in items[:count] if isinstance(raw, dict)]
    issues = _review(payloads, level)
    return [_card(p, i) for p, i in zip(payloads, issues)]


def generate_drafts(db: Session, req: AiDraftIn) -> dict:
    level = _level_name(db, req.cap_do_id)
    groups = _groups(db)
    db.rollback()  # kết thúc giao dịch đọc trước khi gọi mạng tới AI
    if not ai_ready():
        raise AiDraftError("Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong .env)", 503)
    sizes = [BATCH] * (req.so_luong // BATCH) + ([req.so_luong % BATCH] if req.so_luong % BATCH else [])
    workers = len(sizes) if is_real_openai_endpoint() else min(2, len(sizes))
    with ThreadPoolExecutor(max_workers=workers or 1) as pool:
        futures = [pool.submit(_generate_batch, req, level, groups, n, i + 1, len(sizes)) for i, n in enumerate(sizes)]
        cards, failed = [], None
        for future in futures:
            try:
                cards.extend(future.result())
            except AiDraftError as error:
                failed = error
    seen, unique = set(), []
    for card in cards:  # bỏ câu trùng nội dung giữa các phần
        key = (card["cau_hoi"].get("noi_dung") or "").strip()
        if key and key in seen:
            continue
        seen.add(key)
        unique.append(card)
    if not unique:
        raise failed or AiDraftError("AI không trả về câu hỏi nào, vui lòng thử lại", 502)
    _attach_duplicates(db, unique)
    note = "Một phần yêu cầu AI bị lỗi nên số câu ít hơn số đã chọn." if failed or len(unique) < req.so_luong else None
    return {"ban_nhap": unique, "ghi_chu": note}


# ---------------------------------------------------------------- 0. hỏi AI nên soạn gì

def _bank_summary(db: Session, cap_do_id: int | None, ky_nang: str | None) -> tuple[list[dict], list[dict], list[dict]]:
    """Số câu ĐANG ĐĂNG theo cấp × kỹ năng × dạng và theo nhóm kiến thức (câu con tính theo câu cha)."""
    where, params = ["q.trang_thai = 'da_dang'", "q.dang <> 'ngu_lieu'"], {}
    if cap_do_id:
        where.append("COALESCE(q.cap_do_id, p.cap_do_id) = :c")
        params["c"] = cap_do_id
    if ky_nang:
        where.append("COALESCE(q.ky_nang, p.ky_nang) = :k")
        params["k"] = ky_nang
    base = f"FROM cau_hoi q LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id WHERE {' AND '.join(where)}"
    by_type = db.execute(text(f"""
        SELECT COALESCE(q.cap_do_id, p.cap_do_id) AS cap_do_id, COALESCE(q.ky_nang, p.ky_nang) AS ky_nang,
               q.dang, COUNT(*) AS so_cau {base}
        GROUP BY 1, 2, 3"""), params).mappings().all()
    by_group = db.execute(text(f"""
        SELECT n.ma, n.ten, COUNT(q.id) AS so_cau
        FROM nhom_kien_thuc n
        LEFT JOIN (SELECT q.id, q.nhom_kien_thuc_id {base}) q ON q.nhom_kien_thuc_id = n.id
        WHERE n.trang_thai = 'hoat_dong' GROUP BY n.id, n.ma, n.ten"""), params).mappings().all()
    levels = db.execute(text("SELECT id, ten FROM cap_do ORDER BY thu_tu")).mappings().all()
    return [dict(r) for r in levels], [dict(r) for r in by_type], [dict(r) for r in by_group]


def suggest_plan(db: Session, body: AiSuggestIn) -> dict:
    levels, by_type, by_group = _bank_summary(db, body.cap_do_id, body.ky_nang)
    db.rollback()
    level_name = {int(lv["id"]): lv["ten"] for lv in levels}
    counts = [
        f"{level_name.get(int(r['cap_do_id']), '?')} · {SKILL_VI.get(r['ky_nang'], r['ky_nang'])} · "
        f"{DANG_LABELS.get(r['dang'], r['dang'])}: {int(r['so_cau'])} câu"
        for r in by_type if r["cap_do_id"] and r["ky_nang"]
    ]
    groups = [f"{g['ten']} ({g['ma']}): {int(g['so_cau'])} câu" for g in by_group]
    scope = ", ".join(x for x in (
        level_name.get(body.cap_do_id) if body.cap_do_id else None,
        SKILL_VI.get(body.ky_nang) if body.ky_nang else None,
    ) if x) or "tất cả cấp và kỹ năng"
    level_list = ", ".join(f"{lv['id']}={lv['ten']}" for lv in levels)
    context = (
        f"Ngân hàng câu hỏi Xianglingo (câu đang đăng, phạm vi: {scope}).\n"
        f"- Cấp hiện có: {level_list}\n"
        f"- Số câu theo cấp · kỹ năng · dạng (dạng không có trong danh sách = 0 câu): "
        f"{'; '.join(counts) or 'chưa có câu nào'}\n"
        f"- Số câu theo nhóm kiến thức: {'; '.join(groups) or 'chưa có danh mục nhóm'}\n"
        f"- Dạng AI được soạn: {', '.join(f'{t}={DANG_LABELS[t]}' for t in AI_DRAFT_TYPES)}; kỹ năng: "
        f"{', '.join(f'{k}={v}' for k, v in SKILL_VI.items())}\n"
        "Bạn tư vấn giảng viên nên soạn gì tiếp theo: ưu tiên chỗ ngân hàng còn ít câu, nhóm kiến thức chưa có câu, "
        "cân đối kỹ năng. Chỉ dựa vào số liệu trên, không bịa số. Trả lời câu hỏi của giảng viên nếu có. "
        'Trả JSON: {"tra_loi": "trả lời ngắn, có nêu số liệu làm căn cứ", "goi_y": [{"cap_do_id": 1, "ky_nang": "nghe", '
        '"dang": "dung_sai", "chu_de": "...", "so_luong": 5, "yeu_cau": "...", "ly_do": "căn cứ ngắn"}]} (tối đa 4 gợi ý)'
    )
    messages = [{"role": "user", "content": context}]
    for turn in body.lich_su[-10:]:
        messages.append({"role": "assistant" if turn.vai_tro == "ai" else "user", "content": turn.noi_dung})
    messages.append({"role": "user", "content": body.tin_nhan or "Hãy gợi ý tôi nên soạn những câu nào tiếp theo."})

    data = _ask_json(SYSTEM_PROMPT, messages)
    if not isinstance(data, dict):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    plans = []
    for g in data.get("goi_y") or []:
        if not isinstance(g, dict):
            continue
        cap, skill, dang = g.get("cap_do_id"), g.get("ky_nang"), g.get("dang")
        if not (isinstance(cap, int) and cap in level_name and skill in SKILL_VI and dang in AI_DRAFT_TYPES):
            continue  # bỏ gợi ý sai cấp/kỹ năng/dạng
        count = g.get("so_luong") if isinstance(g.get("so_luong"), int) else 5
        plans.append({
            "cap_do_id": cap, "ky_nang": skill, "dang": dang,
            "chu_de": _text(g.get("chu_de"), 200) or "", "so_luong": max(1, min(20, count)),
            "yeu_cau": _text(g.get("yeu_cau"), 1000) or "", "ly_do": _text(g.get("ly_do"), 500),
        })
    return {"tra_loi": _text(data.get("tra_loi"), 3000) or "AI không có phản hồi.", "goi_y": plans[:4]}


# ---------------------------------------------------------------- 2. trao đổi với AI về một câu

def chat_about_draft(db: Session, body: AiChatIn) -> dict:
    original = body.cau_hoi.model_dump(mode="json")
    level = _level_name(db, body.cau_hoi.cap_do_id)
    groups = _groups(db)
    db.rollback()
    view = _review_view(original, level)
    view["nhom_ma"] = next((g["ma"] for g in groups if g["id"] == original.get("nhom_kien_thuc_id")), None)
    instruction = (
        f"Câu hỏi hiện tại (JSON): {json.dumps(view, ensure_ascii=False)}{_groups_hint(groups)}\n"
        "Giảng viên trao đổi với bạn về câu này. Nếu giảng viên chỉ hỏi, hãy trả lời và để cau_hoi_sua = null. "
        "Nếu giảng viên yêu cầu sửa, trả bản sửa ĐẦY ĐỦ trong cau_hoi_sua với các trường: noi_dung, pinyin, dich_nghia, "
        "giai_thich, goi_y, goi_y_2, loi_nghe (nếu là câu Nghe), phuong_an [{noi_dung, la_dap_an_dung}], "
        "dap_an_chap_nhan [..], tu_bat_buoc, tieu_chi_mo_ta, nhom_ma. Không đổi dạng câu, cấp, kỹ năng. "
        'Trả JSON: {"tra_loi": "câu trả lời ngắn cho giảng viên", "cau_hoi_sua": {...} hoặc null}'
    )
    messages = [{"role": "user", "content": instruction}]
    for turn in body.lich_su[-10:]:
        messages.append({"role": "assistant" if turn.vai_tro == "ai" else "user", "content": turn.noi_dung})
    messages.append({"role": "user", "content": body.tin_nhan})

    data = _ask_json(SYSTEM_PROMPT, messages)
    if not isinstance(data, dict):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    reply = _text(data.get("tra_loi"), 3000) or "AI không có phản hồi."
    revised = data.get("cau_hoi_sua")
    proposal = None
    if isinstance(revised, dict):
        merged = _merge_revision(original, revised, groups)
        proposal = _attach_duplicates(db, [_card(merged, _review([merged], level)[0])])[0]
    return {"tra_loi": reply, "de_xuat": proposal}


# ---------------------------------------------------------------- 3. soát lại sau khi Giảng viên sửa

def review_drafts(db: Session, items: list[QuestionIn]) -> dict:
    payloads = [q.model_dump(mode="json") for q in items]
    names = {int(r[0]): str(r[1]) for r in db.execute(text("SELECT id, ten FROM cap_do")).all()}
    db.rollback()
    if not ai_ready():
        raise AiDraftError("Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong .env)", 503)
    # Gom theo cấp, mỗi lần soát tối đa 5 câu, chạy song song
    jobs: list[tuple[str, list[int]]] = []
    by_level: dict[str, list[int]] = {}
    for index, payload in enumerate(payloads):
        by_level.setdefault(names.get(int(payload["cap_do_id"]), "HSK"), []).append(index)
    for level, indexes in by_level.items():
        jobs += [(level, indexes[i:i + BATCH]) for i in range(0, len(indexes), BATCH)]
    issues: list[list[str] | None] = [None] * len(payloads)
    with ThreadPoolExecutor(max_workers=len(jobs) or 1) as pool:
        futures = {pool.submit(_review, [payloads[i] for i in idx], level): idx for level, idx in jobs}
        for future, idx in futures.items():
            for i, found in zip(idx, future.result()):
                issues[i] = found
    return {"ban_nhap": _attach_duplicates(db, [_card(p, i) for p, i in zip(payloads, issues)])}


# ---------------------------------------------------------------- 4. Giảng viên duyệt (lưu + đăng)

def approve_drafts(db: Session, items: list[QuestionIn], lecturer_id: int) -> dict:
    """Mỗi câu lưu và đăng trong giao dịch riêng: câu lỗi không chặn câu khác."""
    results = []
    for index, q in enumerate(items, start=1):
        q = q.model_copy(update={"nguon_noi_dung": "soan_voi_ai"})
        try:
            new_id = create_question(db, q, lecturer_id)
        except QuestionRuleError as error:
            results.append({"stt": index, "id": None, "loi": error.message})
            continue
        try:
            publish_question(db, new_id, lecturer_id)
            if q.tep_audio:
                db.execute(text("UPDATE cau_hoi SET da_kiem_tra_audio = 1 WHERE id = :id AND tep_audio IS NOT NULL"), {"id": new_id})
                db.commit()
            results.append({"stt": index, "id": new_id, "loi": None})
        except (QuestionRuleError, ConflictError) as error:
            results.append({"stt": index, "id": new_id, "loi": f"Đã lưu nháp nhưng chưa đăng: {error.message}"})
    return {"ket_qua": results}
