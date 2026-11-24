"""Trợ lý AI của Giảng viên: khung hỏi đáp mở ở mọi trang (giống Hỏi Xiang của học viên).

- Trả lời câu hỏi chuyên môn (ngữ pháp, vì sao một câu sai, cách ra đề...), cùng Giảng viên lên kế hoạch đề.
- Được biết số câu ĐANG ĐĂNG trong ngân hàng và số đề đang đăng theo cấp để tư vấn có căn cứ; không bịa số.
- Chỉ ĐỀ XUẤT hành động (mở Soạn câu với AI / Ghép đề với AI đã điền sẵn); không tự ghi CSDL.
- Cuộc trò chuyện không lưu ở máy chủ. Đóng giao dịch CSDL trước khi gọi AI.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.questions.schemas.question_payload import AI_DRAFT_TYPES
from app.modules.questions.services.ai_draft_service import SKILL_VI, AiDraftError, _ask_json, _bank_summary, _text
from app.modules.questions.services.question_rules import DANG_LABELS

ASSISTANT_PROMPT = (
    "Bạn là trợ lý AI của giảng viên dạy và ra đề luyện thi HSK 1–4 trên hệ thống Xianglingo. "
    "Bạn suy nghĩ kỹ rồi trả lời ngắn gọn, rõ ràng bằng tiếng Việt: giải thích ngữ pháp, phân tích vì sao một đáp án "
    "đúng/sai, góp ý câu hỏi, cùng giảng viên lên kế hoạch đề thi (cấu trúc phần, phân bổ dạng câu, chủ đề, nhóm kiến thức). "
    "Khi nói về ngân hàng câu hỏi chỉ dùng số liệu hệ thống cung cấp, không bịa số. "
    "Bạn không tự đăng hay sửa dữ liệu; nếu phù hợp, đề xuất hành động để giảng viên tự bấm. Chỉ trả JSON hợp lệ."
)


def _exam_counts(db: Session) -> list[dict]:
    rows = db.execute(text("""
        SELECT cap_do_id, COUNT(*) AS so_de FROM bo_de
        WHERE loai = 'de_thi' AND trang_thai = 'da_dang' GROUP BY cap_do_id
    """)).mappings().all()
    return [dict(r) for r in rows]


def ask_assistant(db: Session, body) -> dict:
    levels, by_type, by_group = _bank_summary(db, None, None)
    exams = _exam_counts(db)
    db.rollback()
    names = {int(lv["id"]): lv["ten"] for lv in levels}
    counts = "; ".join(
        f"{names.get(int(r['cap_do_id']), '?')} · {SKILL_VI.get(r['ky_nang'], r['ky_nang'])} · "
        f"{DANG_LABELS.get(r['dang'], r['dang'])}: {int(r['so_cau'])}"
        for r in by_type if r["cap_do_id"] and r["ky_nang"]
    ) or "chưa có câu nào"
    groups = "; ".join(f"{g['ten']}: {int(g['so_cau'])}" for g in by_group) or "chưa có danh mục nhóm"
    exam_text = "; ".join(f"{names.get(int(e['cap_do_id']), '?')}: {int(e['so_de'])} đề" for e in exams) or "chưa có đề nào đang đăng"
    level_list = ", ".join(f"{lv['id']}={lv['ten']}" for lv in levels)
    context = (
        "Số liệu hệ thống (chỉ câu và đề đang đăng):\n"
        f"- Cấp: {level_list}\n- Câu theo cấp · kỹ năng · dạng (không liệt kê = 0): {counts}\n"
        f"- Câu theo nhóm kiến thức: {groups}\n- Đề thi thử đang đăng: {exam_text}\n"
        f"- Giảng viên đang ở trang: {body.trang or 'không rõ'}\n"
        f"- Dạng AI soạn được: {', '.join(f'{t}={DANG_LABELS[t]}' for t in AI_DRAFT_TYPES)}; "
        f"kỹ năng: {', '.join(f'{k}={v}' for k, v in SKILL_VI.items())}\n"
        'Trả JSON: {"tra_loi": "câu trả lời (xuống dòng bằng \\n)", "hanh_dong": [ '
        '{"loai": "soan_cau", "cap_do_id": 1, "ky_nang": "nghe", "dang": "dung_sai", "chu_de": "...", "so_luong": 5, "nhan": "nhãn nút ngắn"}, '
        '{"loai": "ghep_de", "cap_do_id": 1, "nhan": "nhãn nút ngắn"} ]} — hanh_dong có thể rỗng, tối đa 3.'
    )
    messages = [{"role": "user", "content": context}]
    for turn in body.lich_su[-12:]:
        messages.append({"role": "assistant" if turn.vai_tro == "ai" else "user", "content": turn.noi_dung})
    messages.append({"role": "user", "content": body.tin_nhan})

    data = _ask_json(ASSISTANT_PROMPT, messages)
    if not isinstance(data, dict):
        raise AiDraftError("AI trả về dữ liệu không đúng định dạng, vui lòng thử lại", 502)
    actions = []
    for a in data.get("hanh_dong") or []:
        if not isinstance(a, dict) or not isinstance(a.get("cap_do_id"), int) or a["cap_do_id"] not in names:
            continue
        label = _text(a.get("nhan"), 80)
        if a.get("loai") == "ghep_de":
            actions.append({"loai": "ghep_de", "cap_do_id": a["cap_do_id"], "nhan": label or "Mở Ghép đề với AI"})
        elif a.get("loai") == "soan_cau" and a.get("ky_nang") in SKILL_VI and a.get("dang") in AI_DRAFT_TYPES:
            count = a.get("so_luong") if isinstance(a.get("so_luong"), int) else 5
            actions.append({
                "loai": "soan_cau", "cap_do_id": a["cap_do_id"], "ky_nang": a["ky_nang"], "dang": a["dang"],
                "chu_de": _text(a.get("chu_de"), 200) or "", "so_luong": max(1, min(20, count)),
                "nhan": label or "Mở Soạn câu với AI",
            })
    reply = _text(data.get("tra_loi"), 6000) or "AI không có phản hồi."
    return {"tra_loi": reply, "hanh_dong": actions[:3]}
