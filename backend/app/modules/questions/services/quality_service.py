"""Kiểm định chất lượng câu hỏi bằng dữ liệu làm bài thật (phân tích câu hỏi theo lý thuyết khảo thí cổ điển)
và kiểm tra trùng lặp nội dung khi soạn câu.

Chỉ số cho từng phiên bản câu đang đăng:
- ti_le_dung (độ khó p): tỉ lệ lượt trả lời đúng trên số lượt đã trả lời và đã chấm.
- do_phan_biet (D): tỉ lệ đúng của nhóm 27% lượt làm điểm cao trừ nhóm 27% điểm thấp (điểm lượt không tính câu đang xét).
- phương án sai được chọn nhiều nhất (câu chọn đáp án): nếu được chọn nhiều hơn đáp án đúng thì nghi khóa đáp án.
Chỉ gắn cảnh báo khi đủ số lượt tối thiểu, tránh kết luận từ vài lượt làm.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from sqlalchemy import text
from sqlalchemy.orm import Session

MIN_ANSWERS = 10      # tối thiểu 10 lượt trả lời mới đánh giá
GROUP_SHARE = 0.27    # nhóm cao/thấp 27%
SIMILAR_RATIO = 0.85  # ngưỡng coi là gần trùng

_SEVERITY = {"nghi_dap_an": 3, "phan_biet_am": 3, "bao_loi": 3, "qua_kho": 2, "phan_biet_kem": 1, "qua_de": 1}


def _graded_answers(db: Session, cap_do_id: int | None, ky_nang: str | None) -> list[dict]:
    where, params = ["q.trang_thai = 'da_dang'", "v.diem IS NOT NULL",
                     "(a.phuong_an_chon_id IS NOT NULL OR a.van_ban IS NOT NULL)"], {}
    if cap_do_id:
        where.append("COALESCE(q.cap_do_id, p.cap_do_id) = :c")
        params["c"] = cap_do_id
    if ky_nang:
        where.append("COALESCE(q.ky_nang, p.ky_nang) = :k")
        params["k"] = ky_nang
    rows = db.execute(text(f"""
        SELECT a.luot_lam_id, a.cau_hoi_id, a.phuong_an_chon_id, v.diem, q.dang, q.nguong_dat
        FROM cau_tra_loi a
        JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
        JOIN cau_hoi q ON q.id = a.cau_hoi_id
        LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
        WHERE {' AND '.join(where)}
    """), params).mappings().all()
    return [dict(r) for r in rows]


def _is_right(r: dict) -> bool:
    if r["dang"] in ("viet_mo", "dich_cau"):
        return float(r["diem"]) >= float(r["nguong_dat"] or 6)
    return float(r["diem"]) >= 1


def _attempt_scores(db: Session, attempt_ids: list[int]) -> dict[int, tuple[int, int]]:
    """Tổng (số đúng, số câu đã chấm) của mỗi lượt, tính trên mọi câu của lượt."""
    if not attempt_ids:
        return {}
    rows = db.execute(text(f"""
        SELECT a.luot_lam_id, v.diem, q.dang, q.nguong_dat
        FROM cau_tra_loi a
        JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
        JOIN cau_hoi q ON q.id = a.cau_hoi_id
        WHERE v.diem IS NOT NULL AND a.luot_lam_id IN ({",".join(str(int(i)) for i in attempt_ids)})
    """)).mappings().all()
    scores: dict[int, list[int]] = {}
    for r in rows:
        s = scores.setdefault(r["luot_lam_id"], [0, 0])
        s[0] += 1 if _is_right(r) else 0
        s[1] += 1
    return {k: (v[0], v[1]) for k, v in scores.items()}


def _discrimination(answers: list[dict], scores: dict[int, tuple[int, int]]) -> float | None:
    rest = []
    for a in answers:
        right, total = scores.get(a["luot_lam_id"], (0, 0))
        own = 1 if a["dung"] else 0
        if total - 1 >= 2:  # lượt phải còn ít nhất 2 câu khác để xếp hạng
            rest.append(((right - own) / (total - 1), own))
    if len(rest) < MIN_ANSWERS:
        return None
    rest.sort(key=lambda x: x[0])
    size = max(1, round(len(rest) * GROUP_SHARE))
    low, high = rest[:size], rest[-size:]
    return round(sum(o for _, o in high) / size - sum(o for _, o in low) / size, 2)


def item_quality(db: Session, cap_do_id: int | None, ky_nang: str | None, only_flagged: bool) -> dict:
    rows = _graded_answers(db, cap_do_id, ky_nang)
    for r in rows:
        r["dung"] = _is_right(r)
    by_question: dict[int, list[dict]] = {}
    for r in rows:
        by_question.setdefault(r["cau_hoi_id"], []).append(r)
    scores = _attempt_scores(db, sorted({r["luot_lam_id"] for r in rows}))

    ids = list(by_question)
    meta, options, reports = {}, {}, {}
    if ids:
        id_list = ",".join(str(int(i)) for i in ids)
        meta = {r["id"]: dict(r) for r in db.execute(text(f"""
            SELECT q.id, q.ma_goc_id, q.phien_ban, q.dang, COALESCE(q.cau_cha_id, q.id) AS cau_soan_id,
                   COALESCE(q.ky_nang, p.ky_nang) AS ky_nang, cd.ten AS ten_cap_do,
                   LEFT(COALESCE(q.noi_dung, p.noi_dung, ''), 140) AS noi_dung, q.nguon_noi_dung
            FROM cau_hoi q LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            LEFT JOIN cap_do cd ON cd.id = COALESCE(q.cap_do_id, p.cap_do_id)
            WHERE q.id IN ({id_list})
        """)).mappings().all()}
        for r in db.execute(text(f"""
            SELECT id, cau_hoi_id, noi_dung, la_dap_an_dung FROM phuong_an WHERE cau_hoi_id IN ({id_list})
        """)).mappings().all():
            options.setdefault(r["cau_hoi_id"], []).append(dict(r))
        reports = {r[0]: int(r[1]) for r in db.execute(text(f"""
            SELECT a.cau_hoi_id, COUNT(*) FROM bao_loi b JOIN cau_tra_loi a ON a.id = b.cau_tra_loi_id
            WHERE b.loai = 'noi_dung' AND b.xu_ly_luc IS NULL AND a.cau_hoi_id IN ({id_list})
            GROUP BY a.cau_hoi_id
        """)).all()}
    db.rollback()

    items = []
    for qid, answers in by_question.items():
        n = len(answers)
        p_value = round(sum(1 for a in answers if a["dung"]) / n, 2)
        d_value = _discrimination(answers, scores)
        flags = []
        distractor = None
        if meta[qid]["dang"] in ("chon_mot", "dung_sai", "chon_bo_chung") and options.get(qid):
            counts = {o["id"]: 0 for o in options[qid]}
            for a in answers:
                if a["phuong_an_chon_id"] in counts:
                    counts[a["phuong_an_chon_id"]] += 1
            correct = [o for o in options[qid] if o["la_dap_an_dung"]]
            wrong = [o for o in options[qid] if not o["la_dap_an_dung"]]
            if wrong:
                top = max(wrong, key=lambda o: counts[o["id"]])
                distractor = {"noi_dung": top["noi_dung"], "ti_le": round(counts[top["id"]] / n, 2)}
                if n >= MIN_ANSWERS and correct and counts[top["id"]] > max(counts[o["id"]] for o in correct):
                    flags.append({"ma": "nghi_dap_an", "mo_ta": "Một phương án sai được chọn nhiều hơn đáp án đúng: kiểm tra lại khóa đáp án"})
        if n >= MIN_ANSWERS:
            if p_value < 0.2:
                flags.append({"ma": "qua_kho", "mo_ta": "Dưới 20% làm đúng: câu quá khó hoặc đáp án có thể sai"})
            elif p_value > 0.95:
                flags.append({"ma": "qua_de", "mo_ta": "Trên 95% làm đúng: câu quá dễ, ít giá trị phân loại"})
            if d_value is not None and d_value < 0:
                flags.append({"ma": "phan_biet_am", "mo_ta": "Nhóm điểm cao làm sai nhiều hơn nhóm điểm thấp: nghi đề hoặc đáp án có vấn đề"})
            elif d_value is not None and d_value < 0.2:
                flags.append({"ma": "phan_biet_kem", "mo_ta": "Độ phân biệt thấp (< 0,2): câu chưa phân loại được người học"})
        if reports.get(qid):
            flags.append({"ma": "bao_loi", "mo_ta": f"{reports[qid]} báo lỗi của học viên đang chờ xử lý"})
        if only_flagged and not flags:
            continue
        items.append({
            **meta[qid], "so_luot": n, "ti_le_dung": p_value, "do_phan_biet": d_value,
            "phuong_an_sai_nhieu_nhat": distractor, "canh_bao": flags,
            "du_du_lieu": n >= MIN_ANSWERS, "muc_do": max((_SEVERITY[f["ma"]] for f in flags), default=0),
        })
    items.sort(key=lambda x: (-x["muc_do"], -x["so_luot"]))
    return {"muc": items, "toi_thieu_luot": MIN_ANSWERS}


def count_flagged(db: Session) -> int:
    return sum(1 for i in item_quality(db, None, None, True)["muc"] if i["muc_do"] >= 2)


# ---------------------------------------------------------------- kiểm tra trùng lặp

def _normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = re.sub(r"_+|（\s*）|\(\s*\)", "", value)
    return re.sub(r"[\s\W]+", "", value)


def find_similar(db: Session, items: list[dict], limit: int = 3) -> list[list[dict]]:
    """Với mỗi câu (noi_dung, cap_do_id, dang), tìm câu đã có cùng cấp và dạng có nội dung gần trùng."""
    levels = {(int(i["cap_do_id"]), i["dang"]) for i in items if i.get("cap_do_id") and i.get("dang")}
    bank: dict[tuple[int, str], list[dict]] = {}
    for cap, dang in levels:
        rows = db.execute(text("""
            SELECT q.id, q.ma_goc_id, q.trang_thai, q.noi_dung
            FROM cau_hoi q LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            WHERE q.dang = :d AND COALESCE(q.cap_do_id, p.cap_do_id) = :c AND q.trang_thai IN ('nhap', 'da_dang')
              AND q.noi_dung IS NOT NULL
        """), {"d": dang, "c": cap}).mappings().all()
        bank[(cap, dang)] = [dict(r, chuan=_normalize(r["noi_dung"])) for r in rows]
    db.rollback()
    result = []
    for item in items:
        target = _normalize(item.get("noi_dung"))
        found = []
        if len(target) >= 4:
            for row in bank.get((int(item.get("cap_do_id") or 0), item.get("dang")), []):
                if item.get("bo_qua_ma_goc") and row["ma_goc_id"] == item["bo_qua_ma_goc"]:
                    continue
                ratio = 1.0 if row["chuan"] == target else SequenceMatcher(None, target, row["chuan"]).ratio()
                if ratio >= SIMILAR_RATIO:
                    found.append({"id": row["id"], "ma_goc_id": row["ma_goc_id"], "trang_thai": row["trang_thai"],
                                  "noi_dung": (row["noi_dung"] or "")[:120], "do_giong": round(ratio, 2)})
        found.sort(key=lambda x: -x["do_giong"])
        result.append(found[:limit])
    return result
