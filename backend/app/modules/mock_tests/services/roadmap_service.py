"""AI phân tích kết quả Thi thử và gợi ý lộ trình (mục 6.2 nghiệp vụ).

- Chỉ tạo khi lượt đã nộp và mọi câu đã chấm xong; còn câu chờ chấm/lỗi chấm → chưa tạo.
- Code chia nhóm theo kỹ năng × dạng câu (kèm tên phần thi), lấy tối đa 3 nhóm đúng dưới 60%.
- Mỗi nhóm yếu có các bước ôn do code chọn, đều là nội dung có thật mà Học viên mở được:
    1) bài/kiểm tra cuối thửa đang đăng, ô không khóa; ưu tiên cùng cấp với đề và có câu cùng dạng;
       cấp của đề chưa có bài hoặc chưa mở → tạm lấy cấp đã mở thấp hơn và nói rõ lý do;
    2) tài liệu đang đăng cùng cấp/kỹ năng (cẩm nang làm bài).
  Không có gì phù hợp → báo rõ, không lưu dòng, không tự tạo đường dẫn.
- AI chỉ viết lời nhận xét từ số liệu (không chọn đích, không thấy mã nội bộ); lời AI được lọc mã còn sót.
  AI lỗi/tắt → dùng câu mẫu.
- Lưu vào goi_y_lo_trinh + luot_lam.goi_y_luc; mở lại trang chỉ đọc bản đã lưu, không gọi AI lại.
  Số câu sai, so sánh với lượt trước cùng cấp, ghi chú về cấp được tính lại mỗi lần (không cần AI).
- Hai yêu cầu cùng lúc: chỉ bắt lỗi trùng khóa MySQL 1062 rồi đọc bản đã lưu.
- Không gọi AI khi đang giữ giao dịch; không ghi khóa API hay nội dung trả lời vào log.
"""
import re

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.ai import XIANG_JSON_SYSTEM_PROMPT, json_completion
from app.modules.common.service_errors import ConflictError, NotFoundError
from app.modules.common.sql_helpers import in_params
from app.modules.grading import load_set_items as load_items
from app.modules.materials.services.material_service import external_for
from app.modules.mock_tests.services.attempt_service import _answers, _current_results
from app.modules.mock_tests.services.content import exam_version
from app.modules.practice.services import path_view

WEAK_BELOW = 0.6
MAX_GROUPS = 3
MAX_REASON = 400
SKILL_VI = {"nghe": "Nghe", "doc": "Đọc", "viet": "Viết", "tu_vung": "Từ vựng"}
DANG_VI = {
    "chon_mot": "chọn một đáp án", "dung_sai": "đúng/sai", "chon_bo_chung": "chọn từ bộ phương án chung",
    "sap_xep": "sắp xếp câu", "dien_chu": "điền chữ", "viet_mo": "viết đoạn/câu", "dich_cau": "dịch câu",
}
# Tên phần thi theo cấu trúc đề HSK 2.0 (khớp số phần trong bo_de_cau_hoi.phan và mục lục cẩm nang)
PARTS = {
    "HSK1": {1: "Phần 1 – nghe, xem tranh Đúng/Sai", 2: "Phần 2 – nghe, chọn tranh A/B/C", 3: "Phần 3 – nghe hội thoại, nối tranh",
             4: "Phần 4 – nghe, chọn đáp án chữ", 5: "Phần 1 – tranh và từ Đúng/Sai", 6: "Phần 2 – đọc câu, chọn tranh",
             7: "Phần 3 – ghép câu hỏi – trả lời", 8: "Phần 4 – điền từ"},
    "HSK2": {1: "Phần 1 – nghe, xem tranh Đúng/Sai", 2: "Phần 2 – nghe hội thoại, nối tranh", 3: "Phần 3 – hội thoại ngắn, chọn A/B/C",
             4: "Phần 4 – hội thoại dài, chọn A/B/C", 5: "Phần 1 – đọc câu, chọn tranh", 6: "Phần 2 – điền từ",
             7: "Phần 3 – phán đoán câu ★ Đúng/Sai", 8: "Phần 4 – ghép câu"},
}

_CODE = re.compile(r"\b(?:N|B|T|D|b|t)\d+\b")


# ---------------- Nhóm câu (code) ----------------

def _attempt(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text("""SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, l.goi_y_luc
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.id = :id AND b.loai = 'de_thi'"""),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    if row["trang_thai"] != "da_nop":
        raise ConflictError("Bài chưa nộp")
    return dict(row)


def group_scores(db: Session, attempt: dict, cap_ma: str) -> tuple[list[dict], bool]:
    """Nhóm kỹ năng × dạng câu, xếp từ yếu lên; kèm phần thi và số câu sai. Trả (nhóm, đã chấm xong)."""
    items, questions, _ = load_items(db, attempt["bo_de_id"])
    answers = _answers(db, attempt["id"])
    results = _current_results(db, [a["id"] for a in answers.values()])
    groups: dict[tuple, dict] = {}
    done = True
    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        g = groups.setdefault((item["ky_nang"], q["dang"]), {"ky_nang": item["ky_nang"], "dang": q["dang"], "tong": 0,
                                                              "dung": 0.0, "phan": [], "cau_sai": []})
        g["tong"] += 1
        if item.get("phan") and item["phan"] not in g["phan"]:
            g["phan"].append(item["phan"])
        answer = answers.get(q["id"])
        score = results.get(answer["id"], {}).get("diem_hien_hanh") if answer else 0.0
        if score is None:
            done = False
            continue
        got = score / float(q["diem_toi_da"]) if q["dang"] == "viet_mo" else (1.0 if score >= 1 else 0.0)
        g["dung"] += got
        if got < 1 and item.get("so_cau"):
            g["cau_sai"].append(item["so_cau"])
    out = []
    for g in groups.values():
        g["ty_le"] = round(g["dung"] / g["tong"], 3) if g["tong"] else 0.0
        g["dung"] = round(g["dung"], 2)
        names = PARTS.get(cap_ma, {})
        g["phan_ten"] = [names.get(p, f"Phần {p}") for p in sorted(g["phan"])]
        out.append(g)
    out.sort(key=lambda g: (g["ty_le"], -g["tong"]))
    return out, done


def _previous(db: Session, attempt: dict, cap_do_id: int, cap_ma: str) -> tuple[dict | None, dict]:
    """Lượt Thi thử trước (đã chấm xong) cùng cấp → (thông tin lượt, {(kỹ năng, dạng): nhóm})."""
    rows = db.execute(
        text("""SELECT l.id, l.bo_de_id, l.nop_luc, b.ten FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi' AND b.cap_do_id = :c AND l.trang_thai = 'da_nop'
                  AND l.id < :id ORDER BY l.id DESC LIMIT 5"""),
        {"u": attempt["nguoi_dung_id"], "c": cap_do_id, "id": attempt["id"]},
    ).mappings().all()
    for r in rows:
        groups, done = group_scores(db, dict(r), cap_ma)
        if done:
            return {"id": r["id"], "ten_de": r["ten"], "nop_luc": r["nop_luc"]}, {(g["ky_nang"], g["dang"]): g for g in groups}
    return None, {}


# ---------------- Đích ôn có thật (code) ----------------

def _lesson_types(db: Session, roots: list[int]) -> dict[int, set]:
    if not roots:
        return {}
    marks, params = in_params("r", roots)
    out: dict[int, set] = {r: set() for r in roots}
    for root, dang, child in db.execute(
        text(f"""SELECT b.ma_goc_id, q.dang, c.dang
                 FROM bo_de b JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
                 JOIN cau_hoi q ON q.id = i.cau_hoi_id
                 LEFT JOIN cau_hoi c ON c.cau_cha_id = q.id
                 WHERE b.ma_goc_id IN ({marks}) AND b.trang_thai = 'da_dang'"""),
        params,
    ).all():
        out[int(root)].add(dang)
        if child:
            out[int(root)].add(child)
    return out


def _lesson_ids(db: Session, roots: list[int]) -> dict[int, int]:
    if not roots:
        return {}
    marks, params = in_params("r", roots)
    return {int(r): int(i) for r, i in db.execute(
        text(f"SELECT ma_goc_id, id FROM bo_de WHERE ma_goc_id IN ({marks}) AND trang_thai = 'da_dang'"), params).all()}


def _has_lessons(db: Session, level_id: int, skill: str) -> bool:
    return bool(db.execute(
        text("""SELECT 1 FROM bo_de t JOIN bo_de b ON b.thua_id = t.ma_goc_id AND b.loai IN ('bai', 'cuoi_thua')
                  AND b.trang_thai = 'da_dang'
                WHERE t.loai = 'thua' AND t.trang_thai = 'da_dang' AND t.cap_do_id = :c AND t.ky_nang = :k LIMIT 1"""),
        {"c": level_id, "k": skill},
    ).first())


def _material(db: Session, level_ids: list[int], skill: str) -> dict | None:
    for level_id in level_ids:
        row = db.execute(
            text("""SELECT t.id, t.ten FROM tai_lieu t
                    WHERE t.trang_thai = 'da_dang' AND t.cap_do_id = :c AND t.ky_nang = :k
                    ORDER BY t.id DESC LIMIT 1"""),
            {"c": level_id, "k": skill},
        ).mappings().first()
        if row:
            return {"tai_lieu_id": int(row["id"]), "ten": row["ten"]}
    return None


STATE_RANK = {"dang_lam": 0, "chua_dat": 1, "chua_hoc": 2, "da_vuot": 3, "da_xong": 4}


def _lesson(db: Session, uid: int, level: dict, group: dict) -> dict | None:
    slots = []
    for land in path_view.build_map(db, uid, level["id"], group["ky_nang"]):
        for slot in land["o"]:
            if slot["trang_thai"] in STATE_RANK:
                slots.append({**slot, "thua": land["ten"]})
    types = _lesson_types(db, [s["ma_goc_id"] for s in slots])
    ids = _lesson_ids(db, [s["ma_goc_id"] for s in slots])
    usable = [s for s in slots if s["ma_goc_id"] in ids and types.get(s["ma_goc_id"]) and "viet_mo" not in types[s["ma_goc_id"]]]
    same = [s for s in usable if group["dang"] in types[s["ma_goc_id"]]]
    pool = same or usable
    if not pool:
        return None
    pool.sort(key=lambda s: (STATE_RANK[s["trang_thai"]], s["loai"] != "bai"))
    s = pool[0]
    return {"bo_de_id": ids[s["ma_goc_id"]], "ten": f"{s['thua']} · {s['ten']}", "cung_dang": bool(same), "cap": level["ten"]}


def level_context(db: Session, uid: int, exam_level: dict, skill: str) -> dict:
    """Cấp dùng để ôn và lý do nếu phải lùi xuống cấp dưới."""
    lv = path_view.skill_levels(db, skill)
    opened = path_view.opened_levels(db, uid, skill)
    exam_open = path_view.level_open(exam_level, skill, opened) if any(l["id"] == exam_level["id"] for l in lv) else False
    has = _has_lessons(db, exam_level["id"], skill)
    if exam_open and has:
        return {"levels": [exam_level], "ghi_chu": None, "mo_cap": None}
    lower = [l for l in lv if l["thu_tu"] < exam_level["thu_tu"] and path_view.level_open(l, skill, opened)]
    lower.reverse()
    name = SKILL_VI[skill]
    if not has:
        note = f"{exam_level['ten']} chưa có bài Ôn luyện {name}, tạm ôn nền {lower[0]['ten']} trong lúc chờ bổ sung." if lower \
            else f"{exam_level['ten']} chưa có bài Ôn luyện {name}."
        return {"levels": lower, "ghi_chu": note, "mo_cap": None}
    note = (f"Bài {name} {exam_level['ten']} chưa mở với bạn: làm kiểm tra bắt đầu cấp để mở"
            + (f", trong lúc đó ôn nền {lower[0]['ten']}." if lower else "."))
    return {"levels": lower, "ghi_chu": note, "mo_cap": {"cap_do_id": exam_level["id"], "ky_nang": skill}}


# ---------------- AI viết nhận xét ----------------

def _label(g: dict) -> str:
    parts = f" ({'; '.join(g['phan_ten'])})" if g["phan_ten"] else ""
    return f"{SKILL_VI[g['ky_nang']]} · {DANG_VI[g['dang']]}{parts}"


def _template(g: dict) -> str:
    text_ = f"Bạn đúng {g['dung']:g}/{g['tong']} câu {_label(g)}, đây là phần cần ôn trước."
    if g.get("lesson") and not g["lesson"]["cung_dang"]:
        text_ += f" Chưa có bài ôn đúng dạng này, hãy luyện bài {SKILL_VI[g['ky_nang']]} để quen từ vựng và tốc độ."
    return text_ + " Xem lại các câu sai trước, rồi làm bài ôn bên dưới."


def _prompt(exam: dict, groups: list[dict], prev: dict) -> str:
    lines = [f"Học viên vừa làm đề thi thử {exam['ten']} ({exam['ten_cap_do']}).", "Các nhóm câu còn yếu:"]
    for k, g in enumerate(groups, start=1):
        before = prev.get((g["ky_nang"], g["dang"]))
        trend = f"; lần trước {before['dung']:g}/{before['tong']}" if before else ""
        lesson = g.get("lesson")
        plan = f"bài ôn “{lesson['ten']}” ({lesson['cap']}{'' if lesson['cung_dang'] else ', không cùng dạng'})" if lesson else "chưa có bài ôn"
        lines.append(f"- N{k}: {_label(g)}: đúng {g['dung']:g}/{g['tong']}{trend}; {plan}.")
    lines += [
        "Với mỗi nhóm, viết nhận xét tối đa 2 câu tiếng Việt, xưng 'bạn': nhóm này yếu ở mức nào (dựa vào số liệu),",
        "cần chú ý gì khi làm dạng câu này, và vì sao nên làm bài ôn đã cho.",
        "KHÔNG đoán chủ đề hay nội dung câu sai, KHÔNG nhắc mã N1/N2, KHÔNG bịa bài hay tài liệu khác.",
        'Chỉ trả về JSON: [{"nhom":"N1","ly_do":"..."}]',
    ]
    return "\n".join(lines)


def _ask_ai(prompt: str) -> dict[str, str]:
    data = json_completion(XIANG_JSON_SYSTEM_PROMPT, prompt)
    out = {}
    for row in data if isinstance(data, list) else []:
        if isinstance(row, dict) and isinstance(row.get("nhom"), str) and isinstance(row.get("ly_do"), str):
            out.setdefault(row["nhom"], row["ly_do"])
    return out


def clean_reason(value: str | None) -> str:
    value = _CODE.sub("", value or "")
    value = re.sub(r"\(\s*\)", "", value)
    return re.sub(r"\s+", " ", value).strip(" .,;") [:MAX_REASON]


# ---------------- Đọc / tạo ----------------

def _saved(db: Session, luot_id: int) -> list[dict]:
    rows = db.execute(
        text("""SELECT g.thu_tu, g.ky_nang, g.dang_cau, g.ly_do, g.bo_de_id, g.tai_lieu_id,
                       b.ma_goc_id AS bai_ma_goc, b.ten AS bai_ten, t.ten AS thua_ten, t.cap_do_id AS bai_cap_id, cd.ten AS cap_ten,
                       (SELECT COUNT(*) FROM bo_de x WHERE x.ma_goc_id = b.ma_goc_id AND x.trang_thai = 'da_dang') AS bai_dang,
                       d.ten AS tl_ten, d.trang_thai AS tl_trang_thai
                FROM goi_y_lo_trinh g
                LEFT JOIN bo_de b ON b.id = g.bo_de_id
                LEFT JOIN bo_de t ON t.ma_goc_id = b.thua_id AND t.trang_thai = 'da_dang'
                LEFT JOIN cap_do cd ON cd.id = t.cap_do_id
                LEFT JOIN tai_lieu d ON d.id = g.tai_lieu_id
                WHERE g.luot_lam_id = :l ORDER BY g.thu_tu"""),
        {"l": luot_id},
    ).mappings().all()
    out = []
    for r in rows:
        if r["bo_de_id"]:
            dich = {"loai": "bai", "ma_goc_id": int(r["bai_ma_goc"]), "ten": r["bai_ten"], "thua": r["thua_ten"],
                    "cap": r["cap_ten"], "kha_dung": bool(r["bai_dang"])}
        else:
            dich = {"loai": "tai_lieu", "id": int(r["tai_lieu_id"]), "ten": r["tl_ten"], "kha_dung": r["tl_trang_thai"] == "da_dang"}
        out.append({"thu_tu": r["thu_tu"], "ky_nang": r["ky_nang"], "dang_cau": r["dang_cau"],
                    "ly_do": clean_reason(r["ly_do"]), "dich": dich})
    return out


def _exam_level(db: Session, exam: dict) -> dict:
    row = db.execute(text("SELECT id, ma, ten, thu_tu FROM cap_do WHERE id = :id"), {"id": exam["cap_do_id"]}).mappings().one()
    return dict(row)


def _view(db: Session, uid: int, level: dict, groups: list[dict], prev_info, prev: dict, saved: list[dict], status: str,
          note: str | None = None) -> dict:
    weak = [g for g in groups if g["ty_le"] < WEAK_BELOW][:MAX_GROUPS]
    plans = []
    for g in weak:
        before = prev.get((g["ky_nang"], g["dang"]))
        steps = [s for s in saved if s["ky_nang"] == g["ky_nang"] and s["dang_cau"] == g["dang"]]
        ctx = level_context(db, uid, level, g["ky_nang"])
        lesson_caps = {s["dich"].get("cap") for s in steps if s["dich"]["loai"] == "bai"}
        plans.append({
            "ky_nang": g["ky_nang"], "dang": g["dang"], "phan_ten": g["phan_ten"], "dung": g["dung"], "tong": g["tong"],
            "truoc": {"dung": before["dung"], "tong": before["tong"]} if before else None,
            "cau_sai": g["cau_sai"], "buoc": steps,
            "ghi_chu_cap": ctx["ghi_chu"] if lesson_caps and level["ten"] not in lesson_caps else None,
            "mo_cap": ctx["mo_cap"] if lesson_caps and level["ten"] not in lesson_caps else None,
            "hoc_them": external_for(level["ma"], g["ky_nang"]),
        })
    if status == "co_goi_y" and not any(p["buoc"] for p in plans):
        status = "khong_yeu" if not weak else "chua_co_noi_dung"
    if note is None and status == "khong_yeu":
        note = "Bạn không có nhóm câu nào dưới 60%. Hãy thử đề khác hoặc cấp cao hơn."
    if note is None and status == "chua_co_noi_dung":
        note = "Chưa có bài ôn hay tài liệu phù hợp với phần còn yếu. Giảng viên sẽ bổ sung sau."
    return {
        "trang_thai": status, "ghi_chu": note, "goi_y": plans,
        "lan_truoc": prev_info,
        "nhom": [{"ky_nang": g["ky_nang"], "dang": g["dang"], "tong": g["tong"], "dung": g["dung"], "ty_le": g["ty_le"],
                  "truoc": ({"dung": prev[(g["ky_nang"], g["dang"])]["dung"], "tong": prev[(g["ky_nang"], g["dang"])]["tong"]}
                            if (g["ky_nang"], g["dang"]) in prev else None)} for g in groups],
    }


def get_roadmap(db: Session, luot_id: int, uid: int) -> dict:
    """Đọc gợi ý đã lưu; chưa có thì tạo (gọi AI một lần)."""
    attempt = _attempt(db, luot_id, uid)
    exam = exam_version(db, attempt["bo_de_id"])
    level = _exam_level(db, exam)
    groups, done = group_scores(db, attempt, level["ma"])
    prev_info, prev = _previous(db, attempt, level["id"], level["ma"])
    if not done:
        view = _view(db, uid, level, groups, prev_info, prev, [], "chua_cham",
                     "Bài còn câu đang chấm. Gợi ý lộ trình sẽ có khi chấm xong.")
        view["goi_y"] = []
        db.rollback()
        return view
    if attempt["goi_y_luc"] is None:
        weak = [g for g in groups if g["ty_le"] < WEAK_BELOW][:MAX_GROUPS]
        for g in weak:
            ctx = level_context(db, uid, level, g["ky_nang"])
            g["lesson"] = next((x for x in (_lesson(db, uid, lv, g) for lv in ctx["levels"]) if x), None)
            g["material"] = _material(db, [level["id"]] + [lv["id"] for lv in ctx["levels"]], g["ky_nang"])
        db.rollback()  # kết thúc giao dịch đọc trước khi gọi AI
        targeted = [g for g in weak if g["lesson"] or g["material"]]
        reasons = _ask_ai(_prompt(exam, targeted, prev)) if targeted else {}
        try:
            n = 0
            for k, g in enumerate(targeted, start=1):
                reason = clean_reason(reasons.get(f"N{k}")) or _template(g)
                if g["lesson"]:
                    n += 1
                    db.execute(text("""INSERT INTO goi_y_lo_trinh (luot_lam_id, thu_tu, ky_nang, dang_cau, ly_do, bo_de_id)
                                       VALUES (:l, :t, :k, :d, :r, :b)"""),
                               {"l": luot_id, "t": n, "k": g["ky_nang"], "d": g["dang"], "r": reason, "b": g["lesson"]["bo_de_id"]})
                    reason = None
                if g["material"]:
                    n += 1
                    parts = "; ".join(g["phan_ten"]) or DANG_VI[g["dang"]]
                    db.execute(text("""INSERT INTO goi_y_lo_trinh (luot_lam_id, thu_tu, ky_nang, dang_cau, ly_do, tai_lieu_id)
                                       VALUES (:l, :t, :k, :d, :r, :tl)"""),
                               {"l": luot_id, "t": n, "k": g["ky_nang"], "d": g["dang"],
                                "r": reason or f"Đọc mục {parts} trong cẩm nang: cách làm, bẫy hay gặp và ví dụ có giải thích.",
                                "tl": g["material"]["tai_lieu_id"]})
            db.execute(text("UPDATE luot_lam SET goi_y_luc = NOW() WHERE id = :l AND goi_y_luc IS NULL"), {"l": luot_id})
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if getattr(getattr(error, "orig", None), "args", [None])[0] != 1062:
                raise  # chỉ xử lý trùng khóa do yêu cầu song song
    view = _view(db, uid, level, groups, prev_info, prev, _saved(db, luot_id), "co_goi_y")
    db.rollback()
    return view
