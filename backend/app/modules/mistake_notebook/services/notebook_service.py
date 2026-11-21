"""Sổ tay câu sai & lượt ôn Sổ tay (mục 5.3).

- Chỉ câu thuộc bài Ôn luyện/cuối thửa (câu đề Thi thử, kể cả câu hình và câu nghe, không vào); câu sai Thi thử xem lại trong Lịch sử thi.
- Danh sách: nội dung, pinyin/nghĩa, kỹ năng, đáp án, số lần sai, ngày cần ôn, nguồn gần nhất (suy ra từ lượt làm, không lưu thêm).
- Lượt ôn tối đa 10 câu: ưu tiên câu đến hạn, rồi câu sai nhiều/cũ; vẫn ôn sớm được; không cần năng lượng; dùng bản mới nhất đã đăng.
- Trạng thái: Cần ôn →(đúng)→ Chờ ôn lại (hẹn hôm sau) →(đúng khi đến hạn)→ Đã củng cố (+1 KN lần đầu).
  Sai ở bất kỳ trạng thái nào → Cần ôn. Ôn sớm đúng không nâng Chờ ôn lại lên Đã củng cố.
- Câu đã trả lời trong lượt ôn được đếm cho nhiệm vụ "Ôn 5 câu trong Sổ tay".
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.common.sql_helpers import in_params
from app.modules.mock_tests.services.attempt_service import _is_correct
from app.modules.mock_tests.services.content import correct_option_id
from app.modules.practice.services.skip_service import CHOICE_TYPES, _load_questions, _options_of
from app.modules.mistake_notebook.services import missions

REVIEW_SIZE = 10
GRADABLE = "('chon_mot', 'dung_sai', 'chon_bo_chung', 'sap_xep', 'dien_chu')"
SOURCE_SQL = """(SELECT COALESCE(b.ten, CASE l.loai_boc_cau WHEN 'vuot_thua' THEN 'Kiểm tra vượt thửa' WHEN 'so_tay' THEN 'Ôn Sổ tay'
                                       ELSE 'Bài kiểm tra' END)
                 FROM cau_tra_loi a JOIN cau_hoi x ON x.id = a.cau_hoi_id JOIN luot_lam l ON l.id = a.luot_lam_id
                 JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id LEFT JOIN bo_de b ON b.id = l.bo_de_id
                 WHERE l.nguoi_dung_id = s.nguoi_dung_id AND x.ma_goc_id = s.cau_hoi_goc_id AND v.diem < 1
                 ORDER BY a.id DESC LIMIT 1)"""
WRONG_SQL = """(SELECT COUNT(DISTINCT a.luot_lam_id) FROM cau_tra_loi a JOIN cau_hoi x ON x.id = a.cau_hoi_id
                 JOIN luot_lam l ON l.id = a.luot_lam_id JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                 WHERE l.nguoi_dung_id = s.nguoi_dung_id AND x.ma_goc_id = s.cau_hoi_goc_id AND v.diem < 1)"""
# Sổ tay chỉ gồm câu nằm trong bài Ôn luyện/cuối thửa (câu đề Thi thử dùng chung âm thanh/hình nên xem lại ở Lịch sử thi)
PRACTICE_ONLY = """EXISTS(SELECT 1 FROM bo_de_cau_hoi i JOIN bo_de b ON b.id = i.bo_de_id JOIN cau_hoi v ON v.id = i.cau_hoi_id
                          WHERE v.ma_goc_id = s.cau_hoi_goc_id AND b.loai IN ('bai', 'cuoi_thua'))"""
# bản đang đăng của câu gốc (nếu có), không thì bản gốc
CURRENT_SQL = """COALESCE((SELECT p.id FROM cau_hoi p WHERE p.ma_goc_id = s.cau_hoi_goc_id AND p.trang_thai = 'da_dang'
                           ORDER BY p.phien_ban DESC LIMIT 1), s.cau_hoi_goc_id)"""


def _answer_text(q: dict, options: dict) -> str | None:
    if q["dang"] in CHOICE_TYPES:
        right = correct_option_id(q, options)
        owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
        o = next((x for x in options[owner]["lua_chon"] if x["id"] == right), None)
        return (o["noi_dung"] or "(hình)") if o else None
    return " / ".join(o["noi_dung"] for o in options[q["id"]]["chap_nhan"]) or None


def list_notebook(db: Session, uid: int, trang_thai: str | None) -> dict:
    counts = {r[0]: int(r[1]) for r in db.execute(text(f"""
        SELECT s.trang_thai, COUNT(*) FROM so_tay s WHERE s.nguoi_dung_id = :u AND s.trang_thai <> 'da_loai' AND {PRACTICE_ONLY}
        GROUP BY s.trang_thai"""), {"u": uid}).all()}
    due = int(db.execute(text(f"""SELECT COUNT(*) FROM so_tay s WHERE s.nguoi_dung_id = :u AND s.trang_thai IN ('can_on', 'cho_on_lai')
                                  AND (s.han_on IS NULL OR s.han_on <= CURDATE()) AND {PRACTICE_ONLY}"""), {"u": uid}).scalar_one())
    where, params = ["s.nguoi_dung_id = :u", "s.trang_thai <> 'da_loai'", PRACTICE_ONLY], {"u": uid}
    if trang_thai:
        where.append("s.trang_thai = :t")
        params["t"] = trang_thai
    rows = db.execute(text(f"""
        SELECT s.cau_hoi_goc_id, s.trang_thai, s.han_on, s.cap_nhat_luc, {CURRENT_SQL} AS cau_hoi_id,
               {WRONG_SQL} AS so_lan_sai, {SOURCE_SQL} AS nguon
        FROM so_tay s WHERE {' AND '.join(where)}
        ORDER BY (s.trang_thai = 'da_cung_co'), (s.han_on IS NULL OR s.han_on <= CURDATE()) DESC, s.cap_nhat_luc DESC
        LIMIT 200"""), params).mappings().all()
    items = []
    if rows:
        questions, options = _load_questions(db, [int(r["cau_hoi_id"]) for r in rows])
        levels = {int(r[0]): r[1] for r in db.execute(text("SELECT id, ten FROM cap_do")).all()}
        for r in rows:
            q = questions[int(r["cau_hoi_id"])]
            parent = questions.get(q["cau_cha_id"]) if q["cau_cha_id"] else None
            items.append({
                "cau_hoi_goc_id": int(r["cau_hoi_goc_id"]), "trang_thai": r["trang_thai"],
                "han_on": r["han_on"].isoformat() if r["han_on"] else None,
                "so_lan_sai": max(1, int(r["so_lan_sai"] or 0)), "nguon": r["nguon"],
                "noi_dung": q["noi_dung"] or (parent and parent["noi_dung"]) or ("(Câu nghe)" if q["tep_audio"] else "(Câu hình)"),
                "pinyin": q["pinyin"], "dich_nghia": q["dich_nghia"], "ky_nang": q["ky_nang"],
                "cap_do": levels.get(q["cap_do_id"]), "dap_an": _answer_text(q, options),
            })
    return {"dem": {"can_on": counts.get("can_on", 0), "cho_on_lai": counts.get("cho_on_lai", 0),
                    "da_cung_co": counts.get("da_cung_co", 0), "den_han": due}, "cau": items}


def start_review(db: Session, uid: int) -> int:
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        open_id = db.execute(text("""SELECT id FROM luot_lam WHERE nguoi_dung_id = :u AND loai_boc_cau = 'so_tay'
                                     AND trang_thai = 'dang_lam' ORDER BY id DESC LIMIT 1"""), {"u": uid}).scalar_one_or_none()
        if open_id:
            # lượt ôn tạo trước khi lọc câu Thi thử: còn câu không thuộc bài Ôn luyện → bỏ lượt đó, tạo lượt mới
            stale = db.execute(text("""
                SELECT 1 FROM cau_tra_loi a JOIN cau_hoi c ON c.id = a.cau_hoi_id
                WHERE a.luot_lam_id = :l AND NOT EXISTS(
                    SELECT 1 FROM bo_de_cau_hoi i JOIN bo_de b ON b.id = i.bo_de_id JOIN cau_hoi v ON v.id = i.cau_hoi_id
                    WHERE v.ma_goc_id = COALESCE(c.ma_goc_id, c.id) AND b.loai IN ('bai', 'cuoi_thua'))
                LIMIT 1"""), {"l": open_id}).first()
            if stale is None:
                db.commit()
                return int(open_id)
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_bo' WHERE id = :id"), {"id": open_id})
        rows = db.execute(text(f"""
            SELECT s.cau_hoi_goc_id, p.id AS cau_hoi_id
            FROM so_tay s
            JOIN cau_hoi p ON p.id = (SELECT x.id FROM cau_hoi x WHERE x.ma_goc_id = s.cau_hoi_goc_id AND x.trang_thai = 'da_dang'
                                      ORDER BY x.phien_ban DESC LIMIT 1)
            WHERE s.nguoi_dung_id = :u AND s.trang_thai IN ('can_on', 'cho_on_lai') AND p.dang IN {GRADABLE}
              AND {PRACTICE_ONLY}
            ORDER BY (s.han_on IS NULL OR s.han_on <= CURDATE()) DESC, {WRONG_SQL} DESC, s.cap_nhat_luc ASC
            LIMIT {REVIEW_SIZE}"""), {"u": uid}).mappings().all()
        if not rows:
            any_row = db.execute(text(f"SELECT 1 FROM so_tay s WHERE s.nguoi_dung_id = :u AND s.trang_thai <> 'da_loai' AND {PRACTICE_ONLY} LIMIT 1"),
                                 {"u": uid}).first()
            raise RuleError("Không còn câu cần ôn, các câu đều đã củng cố" if any_row
                            else "Sổ tay trống. Câu làm sai ở Ôn luyện sẽ tự vào đây")
        rng = random.SystemRandom()
        rows = list(rows)
        rng.shuffle(rows)
        luot_id = int(db.execute(text("""INSERT INTO luot_lam (nguoi_dung_id, loai_boc_cau, trang_thai, vi_tri_hien_tai)
                                         VALUES (:u, 'so_tay', 'dang_lam', 1)"""), {"u": uid}).lastrowid)
        for pos, r in enumerate(rows, start=1):
            db.execute(text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, seed_xao) VALUES (:l, :q, :t, :s)"),
                       {"l": luot_id, "q": int(r["cau_hoi_id"]), "t": pos, "s": rng.randrange(1, 2**31)})
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _attempt(db: Session, luot_id: int, uid: int, for_update: bool = False) -> dict:
    row = db.execute(text(f"""SELECT id, nguoi_dung_id, trang_thai FROM luot_lam
                              WHERE id = :id AND loai_boc_cau = 'so_tay'{' FOR UPDATE' if for_update else ''}"""),
                     {"id": luot_id}).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


def _answers(db: Session, luot_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(text("""
        SELECT a.id, a.cau_hoi_id, a.thu_tu, a.seed_xao, a.phuong_an_chon_id, a.van_ban, a.xac_nhan_luc, v.diem
        FROM cau_tra_loi a LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
        WHERE a.luot_lam_id = :l ORDER BY a.thu_tu"""), {"l": luot_id}).mappings().all()]


def _feedback(q: dict, options: dict, a: dict, state: str | None = None) -> dict:
    return {
        "dung": a["diem"] is not None and float(a["diem"]) >= 1,
        "bo_qua": a["phuong_an_chon_id"] is None and not a["van_ban"],
        "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
        "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
        "giai_thich": q["giai_thich"], "dich_nghia": q["dich_nghia"], "loi_nghe": q["loi_nghe"],
        "trang_thai_moi": state,
    }


def get_review(db: Session, luot_id: int, uid: int) -> dict:
    attempt = _attempt(db, luot_id, uid)
    answers = _answers(db, luot_id)
    questions, options = _load_questions(db, [a["cau_hoi_id"] for a in answers])
    roots = [questions[a["cau_hoi_id"]]["ma_goc_id"] for a in answers]
    marks, params = in_params("g", roots)
    states = {int(r[0]): r[1] for r in db.execute(
        text(f"SELECT cau_hoi_goc_id, trang_thai FROM so_tay WHERE nguoi_dung_id = :u AND cau_hoi_goc_id IN ({marks})"),
        {**params, "u": uid}).all()}
    items = []
    for a in answers:
        q = questions[a["cau_hoi_id"]]
        parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
        confirmed = a["xac_nhan_luc"] is not None
        items.append({
            "thu_tu": a["thu_tu"],
            "cau_hoi": {"id": q["id"], "dang": q["dang"], "noi_dung": q["noi_dung"], "pinyin": q["pinyin"], "tep_hinh": q["tep_hinh"],
                        "tep_audio": q["tep_audio"], "mo_ta_hinh": q["mo_ta_hinh"], "goi_y": q["goi_y"], "ky_nang": q["ky_nang"], "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None},
            "ngu_lieu": parent and {"noi_dung": parent["noi_dung"], "pinyin": parent["pinyin"], "tep_hinh": parent["tep_hinh"],
                                    "tep_audio": parent["tep_audio"]},
            "phuong_an": _options_of(q, options, a["seed_xao"]),
            "tra_loi": {"phuong_an_chon_id": a["phuong_an_chon_id"], "van_ban": a["van_ban"]} if confirmed else None,
            "ket_qua": _feedback(q, options, a, states.get(q["ma_goc_id"])) if confirmed else None,
        })
    done = all(i["ket_qua"] for i in items)
    result = None
    if done:
        result = {"so_dung": sum(1 for i in items if i["ket_qua"]["dung"]), "tong": len(items),
                  "cung_co": sum(1 for i in items if i["ket_qua"]["trang_thai_moi"] == "da_cung_co" and i["ket_qua"]["dung"])}
    return {"id": luot_id, "trang_thai": attempt["trang_thai"], "cau_hoi": items, "ket_qua": result,
            "nhiem_vu": missions.list_missions(db, uid)}


def check_answer(db: Session, luot_id: int, uid: int, body) -> dict:
    try:
        attempt = _attempt(db, luot_id, uid, for_update=True)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Lượt ôn này đã kết thúc")
        answers = _answers(db, luot_id)
        answer = next((a for a in answers if a["cau_hoi_id"] == body.cau_hoi_id), None)
        if answer is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        questions, options = _load_questions(db, [body.cau_hoi_id])
        q = questions[body.cau_hoi_id]
        if answer["xac_nhan_luc"] is not None:  # gửi lặp: trả kết quả cũ
            db.commit()
            return {"ket_qua": _feedback(q, options, answer)}
        option_id, van_ban = None, None
        if q["dang"] in CHOICE_TYPES:
            if body.phuong_an_chon_id is not None:
                if body.phuong_an_chon_id not in {o["id"] for o in _options_of(q, options, None)}:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            van_ban = (body.van_ban or "").strip() or None
        answer.update({"phuong_an_chon_id": option_id, "van_ban": van_ban})
        correct = bool(_is_correct(q, answer, options))
        root = q["ma_goc_id"]
        note = db.execute(text("""SELECT trang_thai, han_on <= CURDATE() AS den_han FROM so_tay
                                  WHERE nguoi_dung_id = :u AND cau_hoi_goc_id = :g FOR UPDATE"""), {"u": uid, "g": root}).mappings().first()
        state = note["trang_thai"] if note else "can_on"
        if not correct:
            state, due = "can_on", "CURDATE()"
        elif state == "can_on":
            state, due = "cho_on_lai", "CURDATE() + INTERVAL 1 DAY"
        elif state == "cho_on_lai" and note and note["den_han"]:
            state, due = "da_cung_co", "NULL"
        else:
            due = None  # ôn sớm đúng hoặc đã củng cố: giữ nguyên
        if due is not None:
            db.execute(text(f"""INSERT INTO so_tay (nguoi_dung_id, cau_hoi_goc_id, trang_thai, han_on, cap_nhat_luc)
                               VALUES (:u, :g, :t, {due}, NOW())
                               ON DUPLICATE KEY UPDATE trang_thai = :t, han_on = {due}, cap_nhat_luc = NOW()"""),
                       {"u": uid, "g": root, "t": state})
        if state == "da_cung_co" and correct:
            db.execute(text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong, cau_hoi_goc_id)
                               VALUES (:u, 'kn_cung_co', 1, :g)"""), {"u": uid, "g": root})
        db.execute(text("""UPDATE cau_tra_loi SET phuong_an_chon_id = :o, van_ban = :v, xac_nhan_luc = NOW(),
                           phien_ban_luu = phien_ban_luu + 1 WHERE id = :id"""), {"o": option_id, "v": van_ban, "id": answer["id"]})
        db.execute(text("INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, diem) VALUES (:a, 1, 'code', 'hoan_tat', :d)"),
                   {"a": answer["id"], "d": 1 if correct else 0})
        answer.update({"diem": 1 if correct else 0, "xac_nhan_luc": True})
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": answer["thu_tu"] + 1, "id": luot_id})
        finished = all(a["xac_nhan_luc"] is not None for a in answers)
        if finished:
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = 'nop_tay' WHERE id = :id"),
                       {"id": luot_id})
        db.commit()
        return {"ket_qua": _feedback(q, options, answer, state), "ket_thuc": finished}
    except Exception:
        db.rollback()
        raise


def abandon(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _attempt(db, luot_id, uid, for_update=True)
        if attempt["trang_thai"] == "dang_lam":
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_bo' WHERE id = :id"), {"id": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        raise


def review_context(db: Session, luot_id: int, uid: int, cau_hoi_id: int) -> str:
    """Ngữ cảnh Hỏi Xiang: chỉ sau khi đã Kiểm tra câu đó (mục 6.1)."""
    _attempt(db, luot_id, uid)
    answer = next((a for a in _answers(db, luot_id) if a["cau_hoi_id"] == cau_hoi_id), None)
    if answer is None:
        raise RuleError("Câu hỏi không thuộc lượt này")
    if answer["xac_nhan_luc"] is None:
        raise ConflictError("Hỏi Xiang mở sau khi bấm Kiểm tra")
    questions, options = _load_questions(db, [cau_hoi_id])
    q = questions[cau_hoi_id]
    parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
    owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
    opts = options[owner]["lua_chon"]
    label = {o["id"]: f"{'ABCDEFGH'[i]}. {o['noi_dung'] or '(hình)'}" for i, o in enumerate(opts)}
    lines = ["Ôn lại câu sai trong Sổ tay"]
    if parent and parent["noi_dung"]:
        lines.append(f"Ngữ liệu: {parent['noi_dung']}")
    lines.append(f"Đề: {q['noi_dung'] or '(không có chữ)'}")
    for key, name in (("pinyin", "Pinyin"), ("mo_ta_hinh", "Mô tả hình"), ("loi_nghe", "Lời nghe")):
        if q.get(key):
            lines.append(f"{name}: {q[key]}")
    if opts:
        lines.append("Phương án: " + " | ".join(label[o["id"]] for o in opts))
    if q["dang"] in CHOICE_TYPES:
        lines.append(f"Học viên chọn: {label.get(answer['phuong_an_chon_id'], 'bỏ qua')}")
        lines.append(f"Đáp án đúng: {label.get(correct_option_id(q, options), 'không rõ')}")
    else:
        lines.append(f"Học viên viết: {answer['van_ban'] or 'bỏ qua'}")
        lines.append("Đáp án chấp nhận: " + " / ".join(o["noi_dung"] for o in options[q["id"]]["chap_nhan"]))
    lines.append(f"Kết quả: {'Đúng' if answer['diem'] is not None and float(answer['diem']) >= 1 else 'Sai'}")
    for key, name in (("dich_nghia", "Dịch nghĩa"), ("giai_thich", "Giải thích")):
        if q.get(key):
            lines.append(f"{name}: {q[key]}")
    return "\n".join(lines)
