"""Tìm kiếm gần đúng theo chuỗi con (mục 3.2): từ vựng đã xuất bản và đề thi thử đã đăng.

- Một ô tìm nhận chữ Hán, pinyin (có/không thanh điệu, có/không dấu cách, ü gõ u hoặc v) hoặc nghĩa tiếng Việt
  (có/không dấu, đ = d). So khớp chuỗi con; nếu không có kết quả khớp thì thử "gần đúng" (sai 1–2 ký tự).
- Xếp hạng: khớp trọn > khớp đầu > khớp một từ > chứa chuỗi > gần đúng; cấp thấp và từ ngắn lên trước.
- Không tìm trong ngân hàng câu hỏi hay bài Ôn luyện (giữ cơ chế mở khóa theo thửa); không trả tài liệu.
- Dữ liệu từ vựng nạp một lần rồi giữ trong bộ nhớ 60 giây (vài nghìn dòng), không truy vấn LIKE mỗi lần gõ.
"""
import re
import threading
import time
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session

MAX_QUERY = 40
MAX_WORDS = 20
MAX_EXAMS = 5
CACHE_SECONDS = 60
_CJK = re.compile(r"[㐀-鿿]")
_SPLIT = re.compile(r"[,;/()（）、，；]+")
_lock = threading.Lock()
_cache = {"at": 0.0, "words": [], "exams": []}


def fold(value: str | None) -> str:
    """Chữ thường, bỏ dấu tiếng Việt và thanh điệu pinyin (ā→a, ǚ→u, đ→d), gom khoảng trắng."""
    value = unicodedata.normalize("NFKD", (value or "").lower().replace("đ", "d"))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^\w㐀-鿿]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def compact(value: str) -> str:
    return value.replace(" ", "").replace("'", "")


def distance(a: str, b: str, limit: int) -> int:
    """Khoảng cách Levenshtein, dừng sớm khi vượt limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def _load(db: Session) -> dict:
    with _lock:
        if time.monotonic() - _cache["at"] < CACHE_SECONDS:
            return _cache
    words = [dict(r) for r in db.execute(text("""
        SELECT t.id, t.chu_han, t.pinyin, t.nghia, t.vd_cau, t.vd_pinyin, t.vd_nghia, t.vd_audio,
               t.cap_do_id, cd.ten AS cap, cd.thu_tu AS cap_thu_tu
        FROM tu_vung t JOIN cap_do cd ON cd.id = t.cap_do_id AND cd.trang_thai = 'da_dang'
        WHERE t.trang_thai = 'xuat_ban'
    """)).mappings().all()]
    for w in words:
        w["_vi"] = fold(w["nghia"])
        w["_vi_parts"] = [fold(p) for p in _SPLIT.split(w["nghia"]) if fold(p)]
        w["_py"] = compact(fold(w["pinyin"]))
    exams = [dict(r) for r in db.execute(text("""
        SELECT b.ma_goc_id, b.ten, cd.ten AS cap, cd.ma, cd.thu_tu
        FROM bo_de b JOIN cap_do cd ON cd.id = b.cap_do_id AND cd.trang_thai = 'da_dang'
        WHERE b.loai = 'de_thi' AND b.trang_thai = 'da_dang'
    """)).mappings().all()]
    for e in exams:
        e["_key"] = compact(fold(f"{e['ten']} {e['cap']} {e['ma']}"))
    with _lock:
        _cache.update({"at": time.monotonic(), "words": words, "exams": exams})
        return _cache


def _score_han(w: dict, q: str) -> int:
    han = w["chu_han"]
    if han == q:
        return 100
    if han.startswith(q):
        return 85
    if q in han:
        return 75
    return 60 if w["vd_cau"] and q in w["vd_cau"] else 0


def _score_pinyin(w: dict, qc: str) -> int:
    py = w["_py"]
    if qc == py:
        return 96
    if len(qc) >= 2 and py.startswith(qc):
        return 72
    if len(qc) >= 3 and qc in py:
        return 50
    return 0


def _score_meaning(w: dict, q: str, qc: str, exact: str | None) -> int:
    """Nghĩa phải chứa trọn cụm từ khóa, tính từ đầu một tiếng: "cái" → cái bàn, cái ghế; "cái bàn" → chỉ cái bàn.
    exact: từ khóa gõ có dấu → so cả dấu, để "bàn" không ra "bằng"."""
    vi = w["_vi"]
    if exact and not re.search(r"(?:^|[\s,;(])" + re.escape(exact), w["nghia"].lower()):
        return 0
    if q == vi:
        return 98
    if q in w["_vi_parts"]:
        return 94
    if qc in (compact(p) for p in w["_vi_parts"]):
        return 90  # gõ liền không dấu cách: "maybay" = "máy bay"
    if re.search(r"(?:^|\s)" + re.escape(q) + r"(?:\s|$)", vi):
        return 80  # trùng trọn tiếng: "bàn" → "cái bàn"
    if re.search(r"(?:^|\s)" + re.escape(q), vi):
        return 60  # đang gõ dở tiếng cuối
    return 0


def _near_word(w: dict, q: str, qc: str) -> int:
    """Gần đúng: sai 1 ký tự (từ khóa ≥ 4 ký tự) hoặc 2 ký tự (≥ 7 ký tự) so với pinyin hoặc một nghĩa."""
    limit = 2 if len(qc) >= 7 else 1
    if distance(qc, w["_py"], limit) <= limit:
        return 30
    for p in w["_vi_parts"]:
        if distance(q, p, limit) <= limit:
            return 28
        words = p.split()
        n = len(q.split())
        for i in range(max(0, len(words) - n + 1)):
            if distance(q, " ".join(words[i:i + n]), limit) <= limit:
                return 22
    return 0


def search(db: Session, keyword: str) -> dict:
    raw = (keyword or "").strip()[:MAX_QUERY]
    q = fold(raw)
    if not q:
        return {"tu_khoa": raw, "tu_vung": [], "de_thi": [], "gan_dung": False}
    data = _load(db)
    db.rollback()
    cjk = bool(_CJK.search(q))
    qc = compact(q).replace("v", "u") if not cjk else q
    lowered = unicodedata.normalize("NFC", raw.lower())
    exact = lowered if not cjk and fold(lowered) != re.sub(r"\s+", " ", lowered).strip() else None  # có gõ dấu
    if cjk:
        scored = [(sc, w) for w in data["words"] if (sc := _score_han(w, q))]
    else:
        by_meaning = [(sc, w) for w in data["words"] if (sc := _score_meaning(w, q, qc, exact))]
        by_pinyin = [(sc, w) for w in data["words"] if (sc := _score_pinyin(w, qc))]
        if by_meaning:
            # Có nghĩa khớp: chỉ hiện các từ đó; thêm từ trùng khít pinyin (gõ có dấu thì phải đúng cả thanh điệu)
            # xếp sau cùng, để "cái" không lẫn với cài (菜) hay "bàn" với bāngzhù.
            seen = {w["id"] for _, w in by_meaning}
            extra = [(sc - 100, w) for sc, w in by_pinyin if sc >= 96 and w["id"] not in seen
                     and (not exact or compact(exact) == compact(w["pinyin"].lower()))]
            scored = by_meaning + extra
        else:
            scored = by_pinyin
    near = False
    if not scored and not cjk and len(qc) >= 4:
        scored = [(s, w) for w in data["words"] if (s := _near_word(w, q, qc))]
        near = bool(scored)
    scored.sort(key=lambda x: (-x[0], x[1]["cap_thu_tu"], len(x[1]["chu_han"]), x[1]["id"]))
    words = [{
        "id": w["id"], "chu_han": w["chu_han"], "pinyin": w["pinyin"], "nghia": w["nghia"],
        "cap": w["cap"], "cap_do_id": w["cap_do_id"], "vd_cau": w["vd_cau"], "vd_pinyin": w["vd_pinyin"],
        "vd_nghia": w["vd_nghia"], "vd_audio": w["vd_audio"],
    } for s, w in scored[:MAX_WORDS]]
    exams = []
    if not cjk and len(qc) >= 2:
        hits = [e for e in data["exams"] if qc in e["_key"]]
        hits.sort(key=lambda e: (e["thu_tu"], e["ten"]))
        exams = [{"ma_goc_id": e["ma_goc_id"], "ten": e["ten"], "cap": e["cap"]} for e in hits[:MAX_EXAMS]]
    return {"tu_khoa": raw, "tu_vung": words, "de_thi": exams, "gan_dung": near}
