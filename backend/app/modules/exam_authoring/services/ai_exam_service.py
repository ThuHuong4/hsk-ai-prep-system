"""Giảng viên ghép đề thi thử với AI.

- AI CHỈ CHỌN câu đã được Giảng viên duyệt (đang đăng, bật "Dùng cho Thi thử", đúng cấp) theo cấu trúc phần do
  Giảng viên đặt; AI không tự viết câu mới vào đề. Phần nào ngân hàng thiếu câu thì báo thiếu để soạn bù với AI.
- Giảng viên trao đổi với AI để đổi câu; mọi mã câu AI trả về đều được backend kiểm tra lại (đúng tập ứng viên,
  không trùng, đủ cả cụm câu con của một ngữ liệu).
- Bấm "Tạo đề nháp" mới ghi CSDL (đề ở trạng thái nháp). Giảng viên mở đề kiểm tra rồi bấm Đăng (= duyệt).
- Đóng giao dịch CSDL trước khi gọi AI. AI lỗi: báo lỗi, không tự ghép đề thay.
"""
import json
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import AiNotConfiguredError, AiProviderError, ai_ready, chat_completion, parse_json_reply
from app.modules.exam_authoring.services import listening_audio
from app.modules.exam_authoring.services.ai_media_service import AiMediaError
from app.modules.exam_authoring.services.exam_service import create_exam, delete_draft_exam, set_exam_items
from app.modules.questions.services.question_rules import DANG_LABELS

SKILL_VI = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}
PART_OF = {"nghe": 1, "doc": 2, "viet": 3, "tu_vung": 4}
MAX_CANDIDATES = 250  # mỗi kỹ năng gửi AI tối đa 250 câu ứng viên

SYSTEM_PROMPT = (
    "Bạn là chuyên gia ra đề thi thử HSK. Bạn chỉ được chọn câu trong danh sách ứng viên giảng viên đã duyệt, "
    "không tự viết câu mới. Chọn đề cân đối dạng câu, nhóm kiến thức và chủ đề, tránh các câu gần trùng nhau. "
    "Trả lời bằng tiếng Việt. Chỉ trả JSON hợp lệ."
)


class AiExamError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _short(value, limit: int = 80) -> str:
    value = " ".join(str(value or "").split())
    return value[:limit] + ("…" if len(value) > limit else "")


def _candidates(db: Session, cap_do_id: int) -> list[dict]:
    """Câu dùng được cho đề: đang đăng, bật Thi thử, đúng cấp (câu con lấy cấp/kỹ năng/cờ theo ngữ liệu cha)."""
    rows = db.execute(text("""
        SELECT q.id, q.cau_cha_id, q.dang, q.noi_dung,
               COALESCE(q.ky_nang, p.ky_nang) AS ky_nang,
               COALESCE(q.nhom_kien_thuc_id, p.nhom_kien_thuc_id) AS nhom_id,
               n.ten AS nhom, p.noi_dung AS ngu_lieu
        FROM cau_hoi q
        LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
        LEFT JOIN nhom_kien_thuc n ON n.id = COALESCE(q.nhom_kien_thuc_id, p.nhom_kien_thuc_id)
        WHERE q.dang <> 'ngu_lieu' AND q.trang_thai = 'da_dang'
          AND COALESCE(p.trang_thai, 'da_dang') = 'da_dang'
          AND COALESCE(q.cap_do_id, p.cap_do_id) = :c
          AND COALESCE(p.dung_thi_thu, q.dung_thi_thu) = 1
        ORDER BY q.id
    """), {"c": cap_do_id}).mappings().all()
    return [dict(r) for r in rows]


def _clusters(candidates: list[dict]) -> dict[int, list[int]]:
    """Câu con cùng một ngữ liệu phải vào đề cùng nhau: ngữ liệu id -> danh sách câu con."""
    groups: dict[int, list[int]] = {}
    for c in candidates:
        if c["cau_cha_id"]:
            groups.setdefault(c["cau_cha_id"], []).append(c["id"])
    return groups


def _ask(messages: list[dict]) -> dict:
    if not ai_ready():
        raise AiExamError("Chưa cấu hình AI (OPENAI_API_KEY, OPENAI_MODEL trong .env)", 503)
    try:
        reply = chat_completion(SYSTEM_PROMPT, messages)
    except AiNotConfiguredError as error:
        raise AiExamError("Chưa cấu hình AI", 503) from error
    except AiProviderError as error:
        raise AiExamError("Dịch vụ AI đang lỗi hoặc quá thời gian chờ, vui lòng thử lại", 502) from error
    try:
        data = parse_json_reply(reply)
    except ValueError as error:
        raise AiExamError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502) from error
    if not isinstance(data, dict):
        raise AiExamError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    return data


def compose_exam(db: Session, body) -> dict:
    """AI chọn câu cho đề theo cấu trúc phần; có thể trao đổi để chỉnh lựa chọn hiện tại."""
    level = db.execute(text("SELECT ten FROM cap_do WHERE id = :id"), {"id": body.cap_do_id}).scalar_one_or_none()
    if level is None:
        raise AiExamError("Cấp độ không tồn tại", 422)
    candidates = _candidates(db, body.cap_do_id)
    db.rollback()  # đóng giao dịch đọc trước khi gọi AI

    plan = {p.ky_nang: p.so_cau for p in body.cau_truc if p.so_cau > 0}
    if not plan:
        raise AiExamError("Hãy đặt số câu cho ít nhất một phần", 422)
    by_id = {c["id"]: c for c in candidates}
    clusters = _clusters(candidates)
    available = {skill: sum(1 for c in candidates if c["ky_nang"] == skill) for skill in plan}

    # Danh sách ứng viên gửi AI (giữ cả câu đang chọn để AI biết mà đổi)
    current = [i for i in body.hien_tai if i in by_id]
    sent = []
    for skill in plan:
        pool = [c for c in candidates if c["ky_nang"] == skill]
        if len(pool) > MAX_CANDIDATES:
            keep = [c for c in pool if c["id"] in current]
            rest = [c for c in pool if c["id"] not in current]
            pool = keep + random.sample(rest, MAX_CANDIDATES - len(keep))
        sent += pool
    lines = [
        f"{c['id']}|{SKILL_VI.get(c['ky_nang'], c['ky_nang'])}|{DANG_LABELS.get(c['dang'], c['dang'])}|"
        f"{c['nhom'] or '-'}|{('NL' + str(c['cau_cha_id'])) if c['cau_cha_id'] else '-'}|{_short(c['noi_dung'] or c['ngu_lieu'])}"
        for c in sent
    ]
    structure = "; ".join(f"Phần {PART_OF[s]} {SKILL_VI[s]}: {n} câu (ngân hàng có {available[s]})" for s, n in plan.items())
    context = (
        f"Ghép đề thi thử {level}. Cấu trúc: {structure}.\n"
        f"{'Yêu cầu thêm của giảng viên: ' + body.yeu_cau if body.yeu_cau else ''}\n"
        "Ứng viên (mã|kỹ năng|dạng|nhóm kiến thức|ngữ liệu chung|nội dung rút gọn). "
        "Câu cùng mã ngữ liệu NLx phải chọn cả cụm.\n" + "\n".join(lines) + "\n"
        f"Đang chọn: {current or 'chưa có'}.\n"
        'Trả JSON: {"tra_loi": "giải thích ngắn cách chọn hoặc trả lời giảng viên", '
        '"chon": {"nghe": [mã câu...], "doc": [...], "viet": [...]}}'
    )
    messages = [{"role": "user", "content": context}]
    for turn in body.lich_su[-10:]:
        messages.append({"role": "assistant" if turn.vai_tro == "ai" else "user", "content": turn.noi_dung})
    messages.append({"role": "user", "content": body.tin_nhan or "Hãy chọn câu cho đề theo cấu trúc trên."})
    data = _ask(messages)

    picked: dict[str, list[int]] = {}
    used: set[int] = set()
    raw = data.get("chon") if isinstance(data.get("chon"), dict) else {}
    for skill, limit in plan.items():
        ids = []
        for value in raw.get(skill) or []:
            if not isinstance(value, int) or value in used or value not in by_id or by_id[value]["ky_nang"] != skill:
                continue  # bỏ mã AI bịa, sai kỹ năng hoặc trùng
            group = clusters.get(by_id[value]["cau_cha_id"], [value]) if by_id[value]["cau_cha_id"] else [value]
            if len(ids) + len(group) > limit and ids:
                continue
            for member in group:  # thêm đủ cả cụm câu con của ngữ liệu
                if member not in used:
                    ids.append(member)
                    used.add(member)
        picked[skill] = ids

    items, missing = [], []
    for skill, limit in plan.items():
        for cid in picked[skill]:
            c = by_id[cid]
            items.append({
                "cau_hoi_id": cid, "phan": PART_OF[skill], "ky_nang": skill, "dang": c["dang"],
                "nhom": c["nhom"], "cau_cha_id": c["cau_cha_id"], "noi_dung": _short(c["noi_dung"] or c["ngu_lieu"], 160),
            })
        short = limit - len(picked[skill])
        if short > 0:
            missing.append({"ky_nang": skill, "so_thieu": short, "co_san": available[skill]})
    reply = " ".join(str(data.get("tra_loi") or "").split())[:3000] or "AI không có phản hồi."
    return {"tra_loi": reply, "cau_hoi": items, "thieu": missing}


def create_exam_from_ai(db: Session, body, lecturer_id: int) -> int:
    """Tạo đề NHÁP từ danh sách câu Giảng viên đã xem; tự động ghép 1 băng Nghe liên tiếp nếu chưa có âm thanh chung."""
    info = body.thong_tin
    if not info.nguon:
        info = info.model_copy(update={"nguon": "Ghép với AI từ ngân hàng câu hỏi đã duyệt"})
    new_id = create_exam(db, info, lecturer_id)
    try:
        set_exam_items(db, new_id, body.cau_hoi)
    except Exception:
        delete_draft_exam(db, new_id)  # không để lại đề rỗng khi danh sách câu không hợp lệ
        raise
    if not info.tep_audio_chung:
        try:
            listening_audio.build_for_exam_db(db, new_id)
        except AiMediaError:
            pass
    return new_id
