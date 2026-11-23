"""Thi thử HSK của Học viên (mục 5.1–5.3 nghiệp vụ).

- Không xáo câu, không tốn năng lượng; đếm giờ theo thoi_luong_phut của phiên bản đề (hạn = bắt đầu + thời lượng, tính khi cần).
- Mỗi học viên tối đa 1 lượt đang làm cho mỗi đề (khóa dòng nguoi_dung trước khi tạo lượt).
- Hết giờ: máy chủ tự nộp khi có yêu cầu tiếp theo tới lượt đó.
- Nộp: chấm bằng code các câu có đáp án xác định (ket_qua_cham lần 1, nguồn code);
  câu Viết mở chưa có AI chấm → ghi lần chấm 'loi' để Giảng viên chấm ở mục Chấm bài Viết.
- Câu sai/bỏ trống vào Sổ tay (theo câu gốc); nộp chỉ chạy một lần nên không ghi trùng.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.common.sql_helpers import in_params
from app.modules.grading import OBJECTIVE_TYPES as AUTO_TYPES, is_correct, load_set_items as load_items
from app.modules.mock_tests.services.content import (
    exam_version,
    published_version,
    shape_passage,
    shape_question,
)


def _remaining_seconds_sql() -> str:
    return "TIMESTAMPDIFF(SECOND, NOW(), l.bat_dau_luc + INTERVAL b.thoi_luong_phut MINUTE)"


def _lock_attempt(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text(f"""
            SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.trang_thai, l.bat_dau_luc, l.nop_luc, l.ly_do_nop,
                   l.vi_tri_hien_tai, {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
            WHERE l.id = :id AND b.loai = 'de_thi' FOR UPDATE
        """),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


# ---------------- Danh sách và thông tin đề (công khai) ----------------

def list_exams(db: Session, cap_do_id: int) -> list[dict]:
    rows = db.execute(
        text("""
            SELECT b.id, b.ma_goc_id, b.ten, g.ma_de, b.nguon, b.thoi_luong_phut,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'nghe' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_nghe,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'doc' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_doc,
                   SUM(CASE WHEN COALESCE(q.ky_nang, p.ky_nang) = 'viet' AND i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_viet,
                   SUM(CASE WHEN i.la_cau_vi_du = 0 THEN 1 ELSE 0 END) AS so_cau
            FROM bo_de b
            JOIN bo_de g ON g.id = b.ma_goc_id
            JOIN cap_do cd ON cd.id = b.cap_do_id AND cd.trang_thai = 'da_dang'
            LEFT JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
            LEFT JOIN cau_hoi q ON q.id = i.cau_hoi_id
            LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id
            WHERE b.loai = 'de_thi' AND b.trang_thai = 'da_dang' AND b.cap_do_id = :cap
            GROUP BY b.id, b.ma_goc_id, b.ten, g.ma_de, b.nguon, b.thoi_luong_phut
            ORDER BY g.ma_de
        """),
        {"cap": cap_do_id},
    ).mappings().all()
    return [{k: (int(v) if k.startswith("so_") else v) for k, v in dict(r).items()} for r in rows]


def exam_info(db: Session, ma_goc_id: int) -> dict:
    exam = published_version(db, ma_goc_id)
    if exam is None:
        raise NotFoundError()
    items, _, _ = load_items(db, exam["id"])
    parts: list[dict] = []
    for item in items:
        if not parts or parts[-1]["phan"] != item["phan"]:
            parts.append({"phan": item["phan"], "ky_nang": item["ky_nang"], "so_cau": 0, "tu": None, "den": None})
        if item["so_cau"]:
            part = parts[-1]
            part["so_cau"] += 1
            part["tu"] = part["tu"] or item["so_cau"]
            part["den"] = item["so_cau"]
    exam["cac_phan"] = parts
    exam["so_cau"] = sum(p["so_cau"] for p in parts)
    return exam


# ---------------- Làm bài ----------------

def start_attempt(db: Session, ma_goc_id: int, uid: int) -> int:
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        open_row = db.execute(
            text(f"""
                SELECT l.id, {_remaining_seconds_sql()} AS con_lai_giay
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.nguoi_dung_id = :u AND b.ma_goc_id = :g AND l.trang_thai = 'dang_lam'
                ORDER BY l.id DESC LIMIT 1
            """),
            {"u": uid, "g": ma_goc_id},
        ).mappings().first()
        if open_row and open_row["con_lai_giay"] > 0:
            db.commit()
            return int(open_row["id"])  # Tiếp tục lượt đang làm
        if open_row:
            _submit_locked(db, _lock_attempt(db, open_row["id"], uid), "het_gio")

        exam = published_version(db, ma_goc_id)
        if exam is None:
            raise NotFoundError()
        if not exam["thoi_luong_phut"]:
            raise ConflictError("Đề chưa có thời lượng")
        items, _, _ = load_items(db, exam["id"])
        scored = [i for i in items if not i["la_cau_vi_du"]]
        if not scored:
            raise ConflictError("Đề chưa có câu hỏi")
        result = db.execute(
            text("INSERT INTO luot_lam (nguoi_dung_id, bo_de_id, trang_thai) VALUES (:u, :b, 'dang_lam')"),
            {"u": uid, "b": exam["id"]},
        )
        luot_id = int(result.lastrowid)
        for item in scored:  # Ghim bộ câu và thứ tự của phiên bản đề lúc bắt đầu
            db.execute(
                text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu) VALUES (:l, :q, :t)"),
                {"l": luot_id, "q": item["cau_hoi_id"], "t": item["so_cau"]},
            )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _answers(db: Session, luot_id: int) -> dict[int, dict]:
    rows = db.execute(
        text("SELECT id, cau_hoi_id, thu_tu, phuong_an_chon_id, van_ban, phien_ban_luu FROM cau_tra_loi WHERE luot_lam_id = :l"),
        {"l": luot_id},
    ).mappings().all()
    return {r["cau_hoi_id"]: dict(r) for r in rows}


def get_attempt(db: Session, luot_id: int, uid: int) -> dict:
    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] == "dang_lam" and attempt["con_lai_giay"] <= 0:
            _submit_locked(db, attempt, "het_gio")
            attempt = _lock_attempt(db, luot_id, uid)
        db.commit()
    except Exception:
        db.rollback()
        raise
    exam = exam_version(db, attempt["bo_de_id"])
    if attempt["trang_thai"] != "dang_lam":
        return {"id": luot_id, "trang_thai": attempt["trang_thai"], "de": exam}

    items, questions, options = load_items(db, exam["id"])
    answers = _answers(db, luot_id)
    passages, shaped = {}, []
    for item in items:
        q = questions[item["cau_hoi_id"]]
        data = shape_question(q, options, reveal=item["la_cau_vi_du"])
        if q["cau_cha_id"] and q["cau_cha_id"] not in passages:
            passages[q["cau_cha_id"]] = shape_passage(questions[q["cau_cha_id"]], options, reveal=False)
        answer = answers.get(q["id"])
        shaped.append({
            **{k: item[k] for k in ("thu_tu", "phan", "la_cau_vi_du", "so_cau", "ky_nang")},
            "cau_cha_id": q["cau_cha_id"],
            "cau_hoi": data,
            "tra_loi": {"phuong_an_chon_id": answer["phuong_an_chon_id"], "van_ban": answer["van_ban"]} if answer else None,
        })
    return {
        "id": luot_id, "trang_thai": "dang_lam", "con_lai_giay": int(attempt["con_lai_giay"]),
        "vi_tri_hien_tai": attempt["vi_tri_hien_tai"], "de": exam, "cau_hoi": shaped, "ngu_lieu": passages,
    }


def save_answer(db: Session, luot_id: int, uid: int, body) -> dict:
    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Bài đã nộp, không sửa được")
        if attempt["con_lai_giay"] <= 0:
            _submit_locked(db, attempt, "het_gio")
            db.commit()
            raise ConflictError("Đã hết giờ, bài được nộp tự động")
        answer = db.execute(
            text("SELECT a.id, q.dang, q.cau_cha_id FROM cau_tra_loi a JOIN cau_hoi q ON q.id = a.cau_hoi_id "
                 "WHERE a.luot_lam_id = :l AND a.cau_hoi_id = :q FOR UPDATE"),
            {"l": luot_id, "q": body.cau_hoi_id},
        ).mappings().first()
        if answer is None:
            raise RuleError("Câu hỏi không thuộc bài thi này")
        option_id, van_ban = None, None
        if answer["dang"] in ("chon_mot", "dung_sai", "chon_bo_chung"):
            if body.van_ban is not None:
                raise RuleError("Câu này chọn phương án, không nhập chữ")
            if body.phuong_an_chon_id is not None:
                owner = answer["cau_cha_id"] if answer["dang"] == "chon_bo_chung" else body.cau_hoi_id
                ok = db.execute(
                    text("SELECT 1 FROM phuong_an WHERE id = :o AND cau_hoi_id = :q AND vai_tro = 'lua_chon'"),
                    {"o": body.phuong_an_chon_id, "q": owner},
                ).first()
                if not ok:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            if body.phuong_an_chon_id is not None:
                raise RuleError("Câu này nhập câu trả lời, không chọn phương án")
            van_ban = (body.van_ban or "").strip() or None
        db.execute(
            text("""UPDATE cau_tra_loi SET phuong_an_chon_id = :o, van_ban = :v, phien_ban_luu = phien_ban_luu + 1
                    WHERE id = :id"""),
            {"o": option_id, "v": van_ban, "id": answer["id"]},
        )
        if body.vi_tri:
            db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": body.vi_tri, "id": luot_id})
        db.commit()
        return {"con_lai_giay": int(attempt["con_lai_giay"])}
    except Exception:
        db.rollback()
        raise


def _submit_locked(db: Session, attempt: dict, reason: str) -> None:
    """Chấm và đóng lượt. Gọi khi đã khóa dòng luot_lam và lượt đang làm."""
    items, questions, options = load_items(db, attempt["bo_de_id"])
    answers = _answers(db, attempt["id"])
    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        answer = answers.get(q["id"])
        if answer is None:
            continue
        correct = is_correct(q, answer, options)
        if correct is None:  # Viết mở
            if answer["van_ban"]:
                db.execute(
                    text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, nhan_xet)
                            VALUES (:a, 1, 'ai', 'loi', 'Chưa có AI chấm tự động; chờ Giảng viên chấm')"""),
                    {"a": answer["id"]},
                )
            else:
                db.execute(text("INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, diem) VALUES (:a, 1, 'code', 'hoan_tat', 0)"),
                           {"a": answer["id"]})
            continue
        db.execute(
            text("INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, diem) VALUES (:a, 1, 'code', 'hoan_tat', :d)"),
            {"a": answer["id"], "d": 1 if correct else 0},
        )
        # Câu đề Thi thử dùng chung âm thanh/hình/đoạn văn nên KHÔNG đưa vào Sổ tay;
        # học viên xem lại nguyên đề trong Lịch sử thi (nghiệp vụ 5.3 đã sửa).
    db.execute(
        text("UPDATE luot_lam SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = :r WHERE id = :id AND trang_thai = 'dang_lam'"),
        {"r": reason, "id": attempt["id"]},
    )


def submit_attempt(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _lock_attempt(db, luot_id, uid)
        if attempt["trang_thai"] == "dang_lam":
            _submit_locked(db, attempt, "nop_tay" if attempt["con_lai_giay"] > 0 else "het_gio")
        db.commit()
    except Exception:
        db.rollback()
        raise


# ---------------- Kết quả ----------------

def _current_results(db: Session, answer_ids: list[int]) -> dict[int, dict]:
    if not answer_ids:
        return {}
    marks, params = in_params("a", answer_ids)
    rows = db.execute(
        text(f"""
            SELECT k.cau_tra_loi_id, k.lan, k.nguon, k.trang_thai, k.diem, k.nhan_xet, k.cau_sua
            FROM ket_qua_cham k
            JOIN (SELECT cau_tra_loi_id, MAX(lan) AS lan FROM ket_qua_cham WHERE cau_tra_loi_id IN ({marks}) GROUP BY cau_tra_loi_id) m
              ON m.cau_tra_loi_id = k.cau_tra_loi_id AND m.lan = k.lan
        """),
        params,
    ).mappings().all()
    current = {r["cau_tra_loi_id"]: dict(r) for r in rows}
    done = db.execute(
        text(f"""SELECT cau_tra_loi_id, diem FROM v_ket_qua_hien_hanh WHERE cau_tra_loi_id IN ({marks})"""), params
    ).mappings().all()
    for r in done:
        current.setdefault(r["cau_tra_loi_id"], {})["diem_hien_hanh"] = float(r["diem"])
    return current


def score_attempt(db: Session, attempt: dict, items, questions, answers) -> dict:
    exam = exam_version(db, attempt["bo_de_id"])
    results = _current_results(db, [a["id"] for a in answers.values()])
    skills: dict[str, dict] = {}
    pending = 0
    for item in items:
        if item["la_cau_vi_du"]:
            continue
        q = questions[item["cau_hoi_id"]]
        answer = answers.get(q["id"])
        skill = skills.setdefault(item["ky_nang"], {"ky_nang": item["ky_nang"], "so_cau": 0, "tong_ty_le": 0.0, "dung": 0})
        skill["so_cau"] += 1
        score = results.get(answer["id"], {}).get("diem_hien_hanh") if answer else None
        if score is None:
            pending += 1
            continue
        ratio = score / float(q["diem_toi_da"]) if q["dang"] == "viet_mo" else score
        skill["tong_ty_le"] += ratio
        if q["dang"] != "viet_mo" and score >= 1:
            skill["dung"] += 1
    skill_list = []
    for s in skills.values():
        s["diem"] = round(100 * s["tong_ty_le"] / s["so_cau"], 2) if s["so_cau"] else 0.0
        skill_list.append(s)
    raw_total = sum(100 * s["tong_ty_le"] / s["so_cau"] for s in skills.values() if s["so_cau"])
    scale = exam["diem_toi_da_thi"] / (100 * len(skills)) if skills else 0
    total = raw_total * scale
    return {
        "ky_nang": skill_list,
        "tong_diem": round(total, 2),
        "diem_toi_da": exam["diem_toi_da_thi"],
        "diem_dat": exam["diem_dat_thi"],
        "dat": pending == 0 and total >= exam["diem_dat_thi"],  # Xét đạt trên điểm chưa làm tròn
        "so_cau_cho_cham": pending,
    }


def get_result(db: Session, luot_id: int, uid: int) -> dict:
    attempt = db.execute(
        text("SELECT id, nguoi_dung_id, bo_de_id, trang_thai, bat_dau_luc, nop_luc, ly_do_nop FROM luot_lam WHERE id = :id"),
        {"id": luot_id},
    ).mappings().first()
    if attempt is None or attempt["nguoi_dung_id"] != uid:
        raise NotFoundError()
    attempt = dict(attempt)
    if attempt["trang_thai"] != "da_nop":
        raise ConflictError("Bài chưa nộp")
    exam = exam_version(db, attempt["bo_de_id"])
    items, questions, options = load_items(db, exam["id"])
    answers = _answers(db, luot_id)
    results = _current_results(db, [a["id"] for a in answers.values()])
    passages, shaped = {}, []
    for item in items:
        q = questions[item["cau_hoi_id"]]
        if q["cau_cha_id"] and q["cau_cha_id"] not in passages:
            passages[q["cau_cha_id"]] = shape_passage(questions[q["cau_cha_id"]], options, reveal=True)
        answer = answers.get(q["id"])
        result = results.get(answer["id"]) if answer else None
        entry = {
            **{k: item[k] for k in ("thu_tu", "phan", "la_cau_vi_du", "so_cau", "ky_nang")},
            "cau_cha_id": q["cau_cha_id"],
            "cau_hoi": shape_question(q, options, reveal=True),
            "tra_loi": {"phuong_an_chon_id": answer["phuong_an_chon_id"], "van_ban": answer["van_ban"]} if answer else None,
        }
        if answer and not item["la_cau_vi_du"]:
            score = result.get("diem_hien_hanh") if result else None
            entry["ket_qua"] = {
                "diem": score,
                "dung": (score is not None and score >= 1) if q["dang"] != "viet_mo" else None,
                "bo_trong": answer["phuong_an_chon_id"] is None and not answer["van_ban"],
                "trang_thai_cham": result.get("trang_thai") if result else None,
                "nhan_xet": result.get("nhan_xet") if result else None,
                "cau_sua": result.get("cau_sua") if result else None,
                "cau_tra_loi_id": answer["id"],
            }
        shaped.append(entry)
    return {
        "id": luot_id, "de": exam, "bat_dau_luc": attempt["bat_dau_luc"], "nop_luc": attempt["nop_luc"],
        "ly_do_nop": attempt["ly_do_nop"], "diem": score_attempt(db, attempt, items, questions, answers),
        "cau_hoi": shaped, "ngu_lieu": passages,
    }


def history(db: Session, uid: int) -> list[dict]:
    rows = db.execute(
        text(f"""
            SELECT l.id, l.bo_de_id, l.trang_thai, l.bat_dau_luc, l.nop_luc, l.ly_do_nop, b.ma_goc_id, b.ten,
                   g.ma_de, cd.ten AS ten_cap_do, {_remaining_seconds_sql()} AS con_lai_giay
            FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id JOIN bo_de g ON g.id = b.ma_goc_id
            JOIN cap_do cd ON cd.id = b.cap_do_id
            WHERE l.nguoi_dung_id = :u AND b.loai = 'de_thi'
            ORDER BY l.bat_dau_luc DESC LIMIT 100
        """),
        {"u": uid},
    ).mappings().all()
    out = []
    for r in rows:
        item = dict(r)
        if item["trang_thai"] == "da_nop":
            items, questions, _ = load_items(db, item["bo_de_id"])
            item["diem"] = score_attempt(db, item, items, questions, _answers(db, item["id"]))
        item["con_lai_giay"] = max(0, int(item["con_lai_giay"]))
        out.append(item)
    return out
