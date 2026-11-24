"""Các lớp kiểm định tự động cho đề AI soạn (chạy trước khi Giảng viên xem lại).

1. Giải lại đề: một lượt AI KHÔNG thấy đáp án làm bài, so với đáp án đã soạn.
2. Từ vượt cấp: code đối chiếu chữ Hán với bảng từ vựng đã xuất bản (không dùng AI).
3. Nhìn ảnh: model nhìn ảnh xem có khớp mô tả, có chữ trong ảnh không.
4. Nghe lại: model nghe chép lại âm thanh, so với lời nghe gốc.
Lớp nào chưa cấu hình hoặc lỗi thì trả None (= chưa kiểm), không coi là đạt.
"""
import json
import re
from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiNotConfiguredError,
    AiProviderError,
    look_at_image,
    parse_json_reply,
    stt_ready,
    transcribe,
    vision_ready,
)
from app.modules.exam_authoring.services.ai_part_service import PAIR, SHARED, _review_view
from app.modules.grading.objective_grader import normalize_answer_text
from app.modules.questions.services.ai_draft_service import AiDraftError, _ask_json
from app.storage.static_media import UPLOADS_DIR

_HAN = re.compile(r"[㐀-鿿]+")
_SPEAKER = re.compile(r"(?m)^\s*(男|女|问|問)\s*[：:]\s*")
SOLVER_PROMPT = (
    "Bạn là thí sinh HSK rất giỏi. Làm bài thật cẩn thận, chỉ dựa vào nội dung được cho "
    "(câu Nghe: loi_nghe là lời được đọc lên). Chỉ trả JSON hợp lệ."
)
_ANSWER_KEYS = ("dap_an", "thu_tu_dung", "dap_an_chap_nhan", "giai_thich", "cau_mau", "dich_nghia", "tieu_chi",
                "pinyin_nghe", "nhom_ma")


# ---------------------------------------------------------------- 1. giải lại đề

def _blind(m: dict) -> dict:
    view = _review_view(m)
    for key in _ANSWER_KEYS:
        view.pop(key, None)
    for child in view.get("cau") or []:
        for key in _ANSWER_KEYS:
            child.pop(key, None)
    return view


def _same(m: dict, given) -> bool | None:
    """So đáp án AI giải với đáp án đã soạn; None nếu kiểu này không so được."""
    kieu = m["kieu"]
    if kieu in SHARED or kieu in PAIR:
        keys = [c.get("dap_an") for c in m.get("cau") or []]
        return isinstance(given, list) and [g if isinstance(g, int) else None for g in given] == keys
    if kieu == "doc_sap_xep_doan":
        return isinstance(given, list) and given == m.get("thu_tu_dung")
    if kieu in ("viet_sap_xep", "viet_dien_chu"):
        target = normalize_answer_text(given if isinstance(given, str) else "")
        return bool(target) and any(target == normalize_answer_text(a) for a in m.get("dap_an_chap_nhan") or [])
    if kieu == "viet_tranh":
        return None
    if isinstance(m.get("dap_an"), bool):
        return isinstance(given, bool) and given == m["dap_an"]
    return isinstance(given, int) and not isinstance(given, bool) and given == m.get("dap_an")


def solve_check(items: list[dict], level_name: str) -> list[dict | None]:
    """Kết quả theo từng mục: {"ok": True} | {"ok": False, "ai": ..., "ly_do": ...} | None (chưa kiểm)."""
    targets = [i for i, m in enumerate(items) if m["kieu"] != "viet_tranh"]
    result: list[dict | None] = [None] * len(items)
    if not targets:
        return result
    prompt = (
        f"Đề {level_name}. Làm các mục sau (JSON, lựa chọn đánh số từ 1):\n"
        f"{json.dumps([{'stt': n, **_blind(items[i])} for n, i in enumerate(targets, start=1)], ensure_ascii=False)}\n"
        'Trả JSON: {"ket_qua": [{"stt": 1, "dap_an": ..., "ly_do": "ngắn, tiếng Việt"}]}. "dap_an": số thứ tự lựa chọn; '
        "true/false cho câu Đúng/Sai; mục có nhiều câu con (\"cau\") thì là mảng số, mỗi câu con một số; "
        "sắp xếp 3 câu thì là mảng thứ tự đúng (vd [2,1,3]); câu viết thì là chuỗi câu/chữ hoàn chỉnh."
    )
    try:
        data = _ask_json(SOLVER_PROMPT, [{"role": "user", "content": prompt}])
    except AiDraftError:
        return result
    rows = data.get("ket_qua") if isinstance(data, dict) else None
    for row in rows if isinstance(rows, list) else []:
        if not (isinstance(row, dict) and isinstance(row.get("stt"), int) and 1 <= row["stt"] <= len(targets)):
            continue
        index = targets[row["stt"] - 1]
        same = _same(items[index], row.get("dap_an"))
        if same is not None:
            reason = str(row.get("ly_do") or "")[:300]
            result[index] = {"ok": True} if same else {"ok": False, "ai": row.get("dap_an"), "ly_do": reason}
    return result


# ---------------------------------------------------------------- 2. từ vượt cấp (code)

def load_vocabulary(db: Session, cap_do_id: int) -> set[str]:
    rows = db.execute(text("""
        SELECT t.chu_han FROM tu_vung t JOIN cap_do c ON c.id = t.cap_do_id
        WHERE t.trang_thai = 'xuat_ban' AND c.thu_tu <= (SELECT thu_tu FROM cap_do WHERE id = :id)"""),
        {"id": cap_do_id}).scalars().all()
    words = set()
    for row in rows:
        words.update(_HAN.findall(str(row)))  # bỏ ký hiệu kèm theo như （一）, …
    return words


def _texts(m: dict) -> list[str]:
    out = [m.get("noi_dung"), m.get("loi_nghe"), m.get("tu_bat_buoc"), *(m.get("dap_an_chap_nhan") or [])]
    out += [o.get("noi_dung") for o in m.get("lua_chon") or []]
    for c in m.get("cau") or []:
        out += [c.get("noi_dung"), c.get("loi_nghe")] + [o.get("noi_dung") for o in c.get("lua_chon") or []]
    return [_SPEAKER.sub("", t) for t in out if t]


def outside_words(m: dict, vocab: set[str]) -> list[str]:
    """Chữ Hán không nằm trong từ nào của bảng từ vựng (tách từ dài nhất trước). Rỗng nếu chưa có bảng từ."""
    if not vocab:
        return []
    longest = max(len(w) for w in vocab)
    found: list[str] = []
    for chunk in (c for t in _texts(m) for c in _HAN.findall(t)):
        i, miss = 0, ""
        while i < len(chunk):
            for size in range(min(longest, len(chunk) - i), 0, -1):
                if chunk[i:i + size] in vocab:
                    if miss:
                        found.append(miss)
                        miss = ""
                    i += size
                    break
            else:
                miss += chunk[i]
                i += 1
        if miss:
            found.append(miss)
    return list(dict.fromkeys(found))[:12]


# ---------------------------------------------------------------- 3. nhìn ảnh

def _read_upload(path: str) -> bytes | None:
    target = (UPLOADS_DIR / path).resolve()
    if UPLOADS_DIR.resolve() not in target.parents or not target.is_file():
        return None
    return target.read_bytes()


def image_check(path: str | None, description: str | None) -> dict | None:
    if not (path and description and vision_ready()):
        return None
    data = _read_upload(path)
    if data is None:
        return None
    mime = "image/png" if path.lower().endswith(".png") else ("image/webp" if path.lower().endswith(".webp") else "image/jpeg")
    question = (
        "Ảnh này dùng làm tranh trong đề thi HSK. Yêu cầu của ảnh: " + description[:600] + "\n"
        "Trả JSON: {\"khop\": true/false (ảnh thể hiện rõ đúng yêu cầu, thí sinh nhìn là nhận ra), "
        "\"co_chu\": true/false (ảnh có chữ, số, biển hiệu hay ký tự nào không), \"nhan_xet\": \"ngắn, tiếng Việt\"}"
    )
    try:
        reply = look_at_image(data, mime, question)
        parsed = parse_json_reply(reply)
    except (AiNotConfiguredError, AiProviderError, ValueError):
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("khop"), bool):
        return None
    return {"khop": parsed["khop"], "co_chu": bool(parsed.get("co_chu")), "nhan_xet": str(parsed.get("nhan_xet") or "")[:300]}


# ---------------------------------------------------------------- 4. nghe lại

AUDIO_MATCH = 0.85


def audio_check(path: str | None, script: str | None) -> dict | None:
    if not (path and script and stt_ready()):
        return None
    data = _read_upload(path)
    if data is None:
        return None
    try:
        heard = transcribe(data, path.rsplit("/", 1)[-1])
    except (AiNotConfiguredError, AiProviderError):
        return None
    want = "".join(_HAN.findall(_SPEAKER.sub("", script)))
    got = "".join(_HAN.findall(heard))
    if not want:
        return None
    ratio = SequenceMatcher(None, want, got).ratio() if got else 0.0
    return {"do_khop": round(ratio, 2), "nghe_duoc": heard[:400]}
