"""Kiểm tra "Vượt đến thửa" (mục 4.2).

- Mở khi thửa đích đang khóa; 10 câu rút ngẫu nhiên từ các bài đã đăng của mọi thửa trước thửa đích
  (cùng cấp, cùng kỹ năng), chỉ câu có đáp án xác định. Chưa đủ 10 câu → không mở.
- Không tốn năng lượng; giấu đáp án, giải thích đến khi nộp; được đổi câu trả lời trước khi nộp.
- Nộp: đúng 10/10 → ghi ap_dung_luc (áp dụng quyền), các thửa trước thành "Đã vượt", mở thửa đích;
  +20 KN lần đạt đầu của thửa đích. Câu sai/bỏ trống vào Sổ tay. Chưa đạt → giữ nguyên tiến độ.
- Lưu bằng cột có sẵn: luot_lam.loai_boc_cau = 'vuot_thua', thua_dich_id = phiên bản đang đăng của thửa đích.
- Lượt Bắt đầu cấp / Vượt chặng (level_test_service) dùng chung phần lấy bài, lưu, nộp, Hỏi Xiang ở đây.
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.common.sql_helpers import in_params
from app.modules.grading import (
    CHOICE_TYPES,
    OBJECTIVE_TYPES as GRADABLE,
    correct_option_id,
    is_correct as _is_correct,
    load_questions_by_ids as _load_questions,
    shuffle_choice_options as _options_of,
)
from app.modules.practice.services import path_view

SKIP_SIZE = 10
KN_SKIP = 20
KINDS = ("vuot_thua", "bat_dau_cap", "vuot_chang")
KN_REASON = {"vuot_thua": "kn_vuot_thua", "bat_dau_cap": "kn_bat_dau_cap", "vuot_chang": "kn_vuot_chang"}


def _target(db: Session, thua_ma_goc: int) -> dict:
    row = db.execute(
        text("""SELECT t.id, t.ma_goc_id, t.ten, t.cap_do_id, t.ky_nang, c.ten AS ten_cap_do
                FROM bo_de t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.ma_goc_id = :g AND t.loai = 'thua' AND t.trang_thai = 'da_dang'"""),
        {"g": thua_ma_goc},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def _pool(db: Session, target: dict) -> list[int]:
    """Câu thuộc bài/cuối thửa đang đăng của các thửa đứng trước thửa đích."""
    lands = path_view.build_map(db, 0, target["cap_do_id"], target["ky_nang"])
    roots = [l["ma_goc_id"] for l in lands]
    if target["ma_goc_id"] not in roots:
        raise NotFoundError()
    before = roots[:roots.index(target["ma_goc_id"])]
    if not before:
        raise ConflictError("Thửa đầu tiên luôn mở, không cần vượt")
    marks, params = in_params("t", before)
    rows = db.execute(
        text(f"""SELECT DISTINCT q.id FROM bo_de b
                 JOIN bo_de_cau_hoi i ON i.bo_de_id = b.id
                 JOIN cau_hoi q ON q.id = i.cau_hoi_id
                 WHERE b.thua_id IN ({marks}) AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'
                   AND q.dang IN ('chon_mot', 'dung_sai', 'chon_bo_chung', 'sap_xep', 'dien_chu')"""),
        params,
    ).all()
    return [int(r[0]) for r in rows]


def start_skip(db: Session, thua_ma_goc: int, uid: int) -> int:
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        target = _target(db, thua_ma_goc)
        level = next((l for l in path_view.levels(db) if l["id"] == target["cap_do_id"]), None)
        if level is None or not path_view.level_open(level, target["ky_nang"], path_view.opened_levels(db, uid, target["ky_nang"])):
            raise ConflictError("Cấp này của kỹ năng chưa mở")
        land = next((l for l in path_view.build_map(db, uid, target["cap_do_id"], target["ky_nang"])
                     if l["ma_goc_id"] == target["ma_goc_id"]), None)
        if land is None:
            raise NotFoundError()
        if land["mo"]:
            raise ConflictError("Thửa này đã mở, không cần vượt")
        open_id = db.execute(
            text("""SELECT l.id FROM luot_lam l JOIN bo_de t ON t.id = l.thua_dich_id
                    WHERE l.nguoi_dung_id = :u AND l.loai_boc_cau = 'vuot_thua' AND l.trang_thai = 'dang_lam'
                      AND t.ma_goc_id = :g ORDER BY l.id DESC LIMIT 1"""),
            {"u": uid, "g": target["ma_goc_id"]},
        ).scalar_one_or_none()
        if open_id:
            db.commit()
            return int(open_id)
        pool = _pool(db, target)
        if len(pool) < SKIP_SIZE:
            raise RuleError("Chưa đủ câu hỏi ở các thửa trước để mở kiểm tra vượt")
        rng = random.SystemRandom()
        picked = rng.sample(pool, SKIP_SIZE)
        result = db.execute(
            text("""INSERT INTO luot_lam (nguoi_dung_id, loai_boc_cau, thua_dich_id, trang_thai, vi_tri_hien_tai)
                    VALUES (:u, 'vuot_thua', :t, 'dang_lam', 1)"""),
            {"u": uid, "t": target["id"]},
        )
        luot_id = int(result.lastrowid)
        for pos, qid in enumerate(picked, start=1):
            db.execute(
                text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, seed_xao) VALUES (:l, :q, :t, :s)"),
                {"l": luot_id, "q": qid, "t": pos, "s": rng.randrange(1, 2**31)},
            )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _lock(db: Session, luot_id: int, uid: int, for_update: bool = True) -> dict:
    row = db.execute(
        text(f"""SELECT l.id, l.nguoi_dung_id, l.trang_thai, l.ap_dung_luc, l.thua_dich_id, l.loai_boc_cau AS loai,
                        t.ma_goc_id AS thua_ma_goc, t.ten AS thua,
                        COALESCE(t.cap_do_id, l.cap_do_id) AS cap_do_id, COALESCE(t.ky_nang, l.ky_nang) AS ky_nang,
                        c.ten AS ten_cap_do
                 FROM luot_lam l LEFT JOIN bo_de t ON t.id = l.thua_dich_id
                 JOIN cap_do c ON c.id = COALESCE(t.cap_do_id, l.cap_do_id)
                 WHERE l.id = :id AND l.loai_boc_cau IN ('vuot_thua', 'bat_dau_cap', 'vuot_chang')
                 {' FOR UPDATE' if for_update else ''}"""),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


def _next_level(db: Session, attempt: dict) -> dict | None:
    lv = path_view.levels(db)
    i = next((k for k, l in enumerate(lv) if l["id"] == attempt["cap_do_id"]), None)
    return {"id": lv[i + 1]["id"], "ten": lv[i + 1]["ten"]} if i is not None and i + 1 < len(lv) else None


def _answers(db: Session, luot_id: int) -> list[dict]:
    return [dict(r) for r in db.execute(
        text("""SELECT a.id, a.cau_hoi_id, a.thu_tu, a.seed_xao, a.trang_thai_thao_tac,
                       a.phuong_an_chon_id, a.van_ban, a.xac_nhan_luc, a.phien_ban_luu, v.diem
                FROM cau_tra_loi a LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l ORDER BY a.thu_tu"""),
        {"l": luot_id},
    ).mappings().all()]


def get_skip(db: Session, luot_id: int, uid: int) -> dict:
    attempt = _lock(db, luot_id, uid, for_update=False)
    answers = _answers(db, luot_id)
    questions, options = _load_questions(db, [a["cau_hoi_id"] for a in answers])
    done = attempt["trang_thai"] == "da_nop"
    items = []
    for a in answers:
        q = questions[a["cau_hoi_id"]]
        parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
        item = {
            "thu_tu": a["thu_tu"],
            "cau_hoi": {"id": q["id"], "dang": q["dang"], "noi_dung": q["noi_dung"], "pinyin": q["pinyin"], "tep_hinh": q["tep_hinh"],
                        "tep_audio": q["tep_audio"], "mo_ta_hinh": q["mo_ta_hinh"], "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None},
            "ngu_lieu": parent and {"noi_dung": parent["noi_dung"], "pinyin": parent["pinyin"], "tep_hinh": parent["tep_hinh"],
                                    "tep_audio": parent["tep_audio"]},
            "phuong_an": _options_of(q, options, a["seed_xao"]),
            "tra_loi": {"phuong_an_chon_id": a["phuong_an_chon_id"], "van_ban": a["van_ban"]},
            "ket_qua": None,
        }
        if done:
            item["ket_qua"] = {
                "dung": a["diem"] is not None and float(a["diem"]) >= 1,
                "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
                "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
                "giai_thich": q["giai_thich"], "dich_nghia": q["dich_nghia"], "loi_nghe": q["loi_nghe"],
            }
        items.append(item)
    result = None
    if done:
        right = sum(1 for i in items if i["ket_qua"]["dung"])
        passed = attempt["ap_dung_luc"] is not None
        kn = 0
        if passed:
            kn_row = db.execute(
                text("SELECT so_luong FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND luot_lam_id = :l AND ly_do LIKE 'kn\\_%' LIMIT 1"),
                {"u": uid, "l": luot_id},
            ).scalar_one_or_none()
            kn = int(kn_row or 0)
        result = {"so_dung": right, "tong": len(items), "dat": passed, "kn": kn, "ly_do_kn": KN_REASON[attempt["loai"]] if kn else None}
    return {
        "id": luot_id, "trang_thai": attempt["trang_thai"], "loai": attempt["loai"],
        "cap_ke": _next_level(db, attempt) if attempt["loai"] == "vuot_chang" else None,
        "thua": {"ma_goc_id": attempt["thua_ma_goc"], "ten": attempt["thua"], "cap_do_id": attempt["cap_do_id"],
                 "ky_nang": attempt["ky_nang"], "ten_cap_do": attempt["ten_cap_do"]},
        "cau_hoi": items, "ket_qua": result,
    }


def save_answer(db: Session, luot_id: int, uid: int, cau_hoi_id: int, body) -> None:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Lượt này đã kết thúc")
        answer = next((a for a in _answers(db, luot_id) if a["cau_hoi_id"] == cau_hoi_id), None)
        if answer is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        questions, options = _load_questions(db, [cau_hoi_id])
        q = questions[cau_hoi_id]
        option_id, van_ban = None, None
        if q["dang"] in CHOICE_TYPES:
            if body.phuong_an_chon_id is not None:
                if body.phuong_an_chon_id not in {o["id"] for o in _options_of(q, options, None)}:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            van_ban = (body.van_ban or "").strip() or None
        trang_thai_tt = "da_tra_loi" if (option_id is not None or van_ban is not None) else "chua_thao_tac"
        db.execute(
            text("""UPDATE cau_tra_loi
                    SET phuong_an_chon_id = :o, van_ban = :v, trang_thai_thao_tac = :tt,
                        phien_ban_luu = phien_ban_luu + 1
                    WHERE id = :id"""),
            {"o": option_id, "v": van_ban, "tt": trang_thai_tt, "id": answer["id"]},
        )
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": answer["thu_tu"], "id": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        raise


def submit_skip(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            db.commit()
            return  # gửi lặp: giữ kết quả cũ
        answers = _answers(db, luot_id)
        questions, options = _load_questions(db, [a["cau_hoi_id"] for a in answers])
        right = 0
        for a in answers:
            q = questions[a["cau_hoi_id"]]
            is_skipped = a["phuong_an_chon_id"] is None and not a["van_ban"]
            trang_thai_tt = "bo_qua" if is_skipped else "da_tra_loi"
            correct = (not is_skipped) and bool(_is_correct(q, a, options))
            right += correct
            pbl = int(a.get("phien_ban_luu") or 0)
            db.execute(
                text("UPDATE cau_tra_loi SET trang_thai_thao_tac = :tt, xac_nhan_luc = NOW() WHERE id = :id"),
                {"tt": trang_thai_tt, "id": a["id"]},
            )
            db.execute(
                text("""INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, phien_ban_luu, diem)
                        VALUES (:a, 1, 'code', 'hoan_tat', :pbl, :d)"""),
                {"a": a["id"], "pbl": pbl, "d": 1 if correct else 0},
            )
            if not is_skipped and not correct:
                db.execute(
                    text("""INSERT INTO so_tay (nguoi_dung_id, cau_hoi_goc_id, trang_thai, han_on, cap_nhat_luc)
                            VALUES (:u, :g, 'can_on', CURDATE(), NOW())
                            ON DUPLICATE KEY UPDATE trang_thai = 'can_on', han_on = CURDATE(), cap_nhat_luc = NOW()"""),
                    {"u": uid, "g": q["ma_goc_id"]},
                )
        passed = right == len(answers) and len(answers) > 0
        db.execute(
            text(f"""UPDATE luot_lam SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = 'nop_tay'
                     {', ap_dung_luc = NOW()' if passed else ''} WHERE id = :id"""),
            {"id": luot_id},
        )
        if passed and attempt["loai"] == "vuot_thua":
            db.execute(
                text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, luot_lam_id, ly_do, so_luong, bo_de_goc_id)
                        VALUES (:u, :l, 'kn_vuot_thua', :n, :g)"""),
                {"u": uid, "l": luot_id, "n": KN_SKIP, "g": attempt["thua_ma_goc"]},
            )
        elif passed:  # Bắt đầu cấp / Vượt chặng: +20 KN lần đạt đầu của từng cấp × kỹ năng
            db.execute(
                text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, luot_lam_id, ly_do, so_luong, cap_do_id, ky_nang)
                        VALUES (:u, :l, :r, :n, :c, :k)"""),
                {"u": uid, "l": luot_id, "r": KN_REASON[attempt["loai"]], "n": KN_SKIP, "c": attempt["cap_do_id"], "k": attempt["ky_nang"]},
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def abandon_skip(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] == "dang_lam":
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_bo' WHERE id = :id"), {"id": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        raise


def skip_context(db: Session, luot_id: int, uid: int, cau_hoi_id: int) -> str:
    """Ngữ cảnh Hỏi Xiang cho một câu của lượt vượt — chỉ sau khi nộp (mục 4.4)."""
    attempt = _lock(db, luot_id, uid, for_update=False)
    if attempt["trang_thai"] != "da_nop":
        raise ConflictError("Hỏi Xiang mở sau khi nộp bài kiểm tra")
    answer = next((a for a in _answers(db, luot_id) if a["cau_hoi_id"] == cau_hoi_id), None)
    if answer is None:
        raise RuleError("Câu hỏi không thuộc lượt này")
    questions, options = _load_questions(db, [cau_hoi_id])
    q = questions[cau_hoi_id]
    parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
    owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
    letters = "ABCDEFGH"
    opts = options[owner]["lua_chon"]
    label = {o["id"]: f"{letters[i]}. {o['noi_dung'] or '(hình)'}" for i, o in enumerate(opts)}
    title = {"vuot_thua": f"Kiểm tra vượt tới thửa {attempt['thua']}",
             "bat_dau_cap": f"Kiểm tra bắt đầu cấp {attempt['ten_cap_do']} (câu của cấp thấp hơn)",
             "vuot_chang": f"Kiểm tra vượt cấp {attempt['ten_cap_do']}"}[attempt["loai"]]
    lines = [f"{title} ({attempt['ten_cap_do']}, kỹ năng {attempt['ky_nang']})"]
    if parent and parent["noi_dung"]:
        lines.append(f"Ngữ liệu: {parent['noi_dung']}")
    lines.append(f"Đề: {q['noi_dung'] or '(không có chữ)'}")
    for key, name in (("pinyin", "Pinyin"), ("mo_ta_hinh", "Mô tả hình"), ("loi_nghe", "Lời nghe")):
        if q.get(key):
            lines.append(f"{name}: {q[key]}")
    if opts:
        lines.append("Phương án: " + " | ".join(label[o["id"]] for o in opts))
    if q["dang"] in CHOICE_TYPES:
        lines.append(f"Học viên chọn: {label.get(answer['phuong_an_chon_id'], 'bỏ trống')}")
        lines.append(f"Đáp án đúng: {label.get(correct_option_id(q, options), 'không rõ')}")
    else:
        lines.append(f"Học viên viết: {answer['van_ban'] or 'bỏ trống'}")
        lines.append("Đáp án chấp nhận: " + " / ".join(o["noi_dung"] for o in options[q["id"]]["chap_nhan"]))
    lines.append(f"Kết quả: {'Đúng' if answer['diem'] is not None and float(answer['diem']) >= 1 else 'Sai'}")
    for key, name in (("dich_nghia", "Dịch nghĩa"), ("giai_thich", "Giải thích")):
        if q.get(key):
            lines.append(f"{name}: {q[key]}")
    return "\n".join(lines)
