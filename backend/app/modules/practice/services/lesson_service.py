"""Lượt làm bài Ôn luyện (mục 4.1, 4.3, 4.4, 4.6).

- Mở lượt: ô phải đang mở; đã có lượt đang làm của bài đó thì dùng lại (F5 không mất bài, không trừ thêm).
  Mục đích: chưa từng đạt và chưa nộp → hoc_moi; đã nộp chưa đạt → lam_lai; đã đạt → on_lai.
  hoc_moi/lam_lai là lượt tiêu hao: cần năng lượng > 0 lúc mở; on_lai không cần, không trừ, không KN.
- Xáo thứ tự câu và phương án (trừ Đúng/Sai); lưu thứ tự (thu_tu) và hạt xáo (seed_xao) để mở lại y hệt.
- Kiểm tra từng câu theo thứ tự; câu đã xác nhận không sửa; bỏ qua tính như sai.
  Sai/bỏ qua ở lượt tiêu hao trừ 1 năng lượng (đang 0 thì ghi 0); câu sai/bỏ qua vào Sổ tay ngay.
- Câu cuối được kiểm tra → nộp lượt. Đạt lần đầu: +10 KN (bài) hoặc +20 KN (cuối thửa), một lần mỗi bài gốc.
- Bỏ lượt: lượt chuyển da_bo, không hoàn năng lượng; câu sai đã ghi vẫn ở Sổ tay.
"""
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, NotFoundError, RuleError
from app.modules.grading import (
    CHOICE_TYPES,
    correct_option_id,
    is_correct as _is_correct,
    load_set_items as load_items,
    shuffle_choice_options as _shuffled,
)
from app.modules.practice.services import path_view

CONSUMING = ("hoc_moi", "lam_lai")
KN = {"bai": ("kn_bai", 10), "cuoi_thua": ("kn_cuoi_thua", 20)}


def _lesson_scope(db: Session, ma_goc_id: int) -> dict:
    row = db.execute(
        text("""SELECT b.id, b.ma_goc_id, b.loai, b.vi_tri, b.ten, b.thua_id, t.ten AS ten_thua, t.cap_do_id, t.ky_nang, c.ten AS ten_cap_do
                FROM bo_de b
                JOIN bo_de t ON t.ma_goc_id = b.thua_id AND t.trang_thai = 'da_dang'
                JOIN cap_do c ON c.id = t.cap_do_id
                WHERE b.ma_goc_id = :g AND b.loai IN ('bai', 'cuoi_thua') AND b.trang_thai = 'da_dang'"""),
        {"g": ma_goc_id},
    ).mappings().first()
    if row is None:
        raise NotFoundError()
    return dict(row)


def _slot_state(db: Session, uid: int, lesson: dict) -> dict:
    level = next((l for l in path_view.levels(db) if l["id"] == lesson["cap_do_id"]), None)
    if level is None or not path_view.level_open(level, lesson["ky_nang"], path_view.opened_levels(db, uid, lesson["ky_nang"])):
        raise ConflictError("Cấp này của kỹ năng chưa mở")
    for land in path_view.build_map(db, uid, lesson["cap_do_id"], lesson["ky_nang"]):
        for slot in land["o"]:
            if slot.get("ma_goc_id") == lesson["ma_goc_id"]:
                return slot
    raise NotFoundError()


def start_lesson(db: Session, ma_goc_id: int, uid: int) -> int:
    try:
        db.execute(text("SELECT id FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid})
        lesson = _lesson_scope(db, ma_goc_id)
        slot = _slot_state(db, uid, lesson)
        if slot["trang_thai"] == "khoa":
            raise ConflictError("Ô này chưa mở. Hãy hoàn thành ô trước.")
        if slot.get("luot_dang_lam"):
            db.commit()
            return int(slot["luot_dang_lam"])
        purpose = {"da_xong": "on_lai", "da_vuot": "on_lai", "chua_dat": "lam_lai"}.get(slot["trang_thai"], "hoc_moi")
        if purpose in CONSUMING:
            energy = db.execute(text("SELECT nang_luong FROM nguoi_dung WHERE id = :u"), {"u": uid}).scalar_one()
            if energy <= 0:
                raise ConflictError("Hết năng lượng. Hãy làm nhiệm vụ ngày hoặc ôn lại bài đã xong.")
        items, questions, _ = load_items(db, lesson["id"])
        if any(questions[i["cau_hoi_id"]]["dang"] == "viet_mo" for i in items):
            raise RuleError("Bài có câu Viết mở cần AI chấm, chức năng này chưa hỗ trợ")
        if not items:
            raise RuleError("Bài chưa có câu hỏi")
        result = db.execute(
            text("""INSERT INTO luot_lam (nguoi_dung_id, bo_de_id, muc_dich, trang_thai, vi_tri_hien_tai)
                    VALUES (:u, :b, :m, 'dang_lam', 1)"""),
            {"u": uid, "b": lesson["id"], "m": purpose},
        )
        luot_id = int(result.lastrowid)
        order = [i["cau_hoi_id"] for i in items]
        random.SystemRandom().shuffle(order)
        for pos, qid in enumerate(order, start=1):
            db.execute(
                text("INSERT INTO cau_tra_loi (luot_lam_id, cau_hoi_id, thu_tu, seed_xao) VALUES (:l, :q, :t, :s)"),
                {"l": luot_id, "q": qid, "t": pos, "s": random.SystemRandom().randrange(1, 2**31)},
            )
        db.commit()
        return luot_id
    except Exception:
        db.rollback()
        raise


def _lock(db: Session, luot_id: int, uid: int) -> dict:
    row = db.execute(
        text("""SELECT l.id, l.nguoi_dung_id, l.bo_de_id, l.muc_dich, l.trang_thai, l.vi_tri_hien_tai, l.bat_dau_luc, b.ma_goc_id
                FROM luot_lam l JOIN bo_de b ON b.id = l.bo_de_id
                WHERE l.id = :id AND b.loai IN ('bai', 'cuoi_thua') FOR UPDATE"""),
        {"id": luot_id},
    ).mappings().first()
    if row is None or row["nguoi_dung_id"] != uid:
        raise NotFoundError()
    return dict(row)


def _answers(db: Session, luot_id: int) -> list[dict]:
    rows = db.execute(
        text("""SELECT a.id, a.cau_hoi_id, a.thu_tu, a.seed_xao, a.phuong_an_chon_id, a.van_ban, a.xac_nhan_luc, a.nang_luong_tru,
                       v.diem
                FROM cau_tra_loi a LEFT JOIN v_ket_qua_hien_hanh v ON v.cau_tra_loi_id = a.id
                WHERE a.luot_lam_id = :l ORDER BY a.thu_tu"""),
        {"l": luot_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _feedback(q: dict, options: dict, answer: dict, energy_cut: int) -> dict:
    return {
        "dung": answer["diem"] is not None and float(answer["diem"]) >= 1,
        "bo_qua": answer["phuong_an_chon_id"] is None and not answer["van_ban"],
        "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
        "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
        "giai_thich": q["giai_thich"], "dich_nghia": q["dich_nghia"], "loi_nghe": q["loi_nghe"],
        "nang_luong_tru": energy_cut,
    }


def _word(db: Session, tu_vung_id: int | None) -> dict | None:
    if not tu_vung_id:
        return None
    row = db.execute(
        text("""SELECT id, chu_han, pinyin, nghia, vd_cau, vd_pinyin, vd_nghia, vd_audio FROM tu_vung
                WHERE id = :id AND trang_thai = 'xuat_ban'"""),
        {"id": tu_vung_id},
    ).mappings().first()
    return dict(row) if row else None


def _summary(db: Session, attempt: dict, lesson_row: dict, answers: list[dict], questions: dict) -> dict:
    total = len(answers)
    right = sum(1 for a in answers if a["diem"] is not None and float(a["diem"]) >= 1)
    passed = total > 0 and right == total
    kn = 0
    if passed:  # chỉ hiện KN nếu chính lượt này nhận (KN ghi sau lúc bắt đầu lượt); ôn lại bài đã nhận thì 0
        reason, amount = KN[lesson_row["loai"]]
        got = db.execute(
            text("""SELECT so_luong FROM nhat_ky_thuong WHERE nguoi_dung_id = :u AND ly_do = :r AND bo_de_goc_id = :g
                    AND tao_luc >= :t"""),
            {"u": attempt["nguoi_dung_id"], "r": reason, "g": attempt["ma_goc_id"], "t": attempt["bat_dau_luc"]},
        ).scalar_one_or_none()
        kn = int(got or 0)
    wrong = [{"thu_tu": a["thu_tu"], "noi_dung": questions[a["cau_hoi_id"]]["noi_dung"]} for a in answers
             if not (a["diem"] is not None and float(a["diem"]) >= 1)]
    return {"so_dung": right, "tong": total, "dat": passed, "kn_nhan": kn, "cau_can_on": wrong}


def get_attempt(db: Session, luot_id: int, uid: int) -> dict:
    attempt = _lock(db, luot_id, uid)
    db.commit()
    lesson_row = db.execute(text("SELECT id, ma_goc_id, loai, vi_tri, ten, thua_id FROM bo_de WHERE id = :id"), {"id": attempt["bo_de_id"]}).mappings().one()
    land = db.execute(
        text("""SELECT t.ten, t.cap_do_id, t.ky_nang, c.ten AS ten_cap_do FROM bo_de t JOIN cap_do c ON c.id = t.cap_do_id
                WHERE t.ma_goc_id = :g ORDER BY (t.trang_thai = 'da_dang') DESC, t.phien_ban DESC LIMIT 1"""),
        {"g": lesson_row["thua_id"]},
    ).mappings().one()
    _, questions, options = load_items(db, attempt["bo_de_id"])
    answers = _answers(db, luot_id)
    items, words, seen = [], [], set()
    for a in answers:
        q = questions[a["cau_hoi_id"]]
        parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
        confirmed = a["xac_nhan_luc"] is not None
        items.append({
            "thu_tu": a["thu_tu"],
            "cau_hoi": {"id": q["id"], "dang": q["dang"], "noi_dung": q["noi_dung"], "pinyin": q["pinyin"], "tep_hinh": q["tep_hinh"],
                        "tep_audio": q["tep_audio"], "mo_ta_hinh": q["mo_ta_hinh"], "goi_y": q["goi_y"], "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None},
            "ngu_lieu": parent and {"noi_dung": parent["noi_dung"], "pinyin": parent["pinyin"], "tep_hinh": parent["tep_hinh"],
                                    "tep_audio": parent["tep_audio"]},
            "phuong_an": _shuffled(q, options, a["seed_xao"]),
            "tra_loi": {"phuong_an_chon_id": a["phuong_an_chon_id"], "van_ban": a["van_ban"]} if confirmed else None,
            "ket_qua": _feedback(q, options, a, int(a["nang_luong_tru"])) if confirmed else None,
        })
        word = _word(db, q.get("tu_vung_id")) if land["ky_nang"] == "tu_vung" else None
        if word and word["id"] not in seen:
            seen.add(word["id"])
            words.append(word)
    return {
        "id": luot_id, "trang_thai": attempt["trang_thai"], "muc_dich": attempt["muc_dich"],
        "tieu_hao": attempt["muc_dich"] in CONSUMING,
        "bai": {"ma_goc_id": lesson_row["ma_goc_id"], "ten": lesson_row["ten"], "loai": lesson_row["loai"], "vi_tri": lesson_row["vi_tri"],
                "thua": land["ten"], "ky_nang": land["ky_nang"], "cap_do_id": land["cap_do_id"], "ten_cap_do": land["ten_cap_do"]},
        "cau_hoi": items, "the_tu": words,
        "ket_qua": _summary(db, attempt, lesson_row, answers, questions) if attempt["trang_thai"] == "da_nop" else None,
        **path_view.energy_and_kn(db, uid),
    }


def check_answer(db: Session, luot_id: int, uid: int, body) -> dict:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] != "dang_lam":
            raise ConflictError("Lượt này đã kết thúc")
        answers = _answers(db, luot_id)
        answer = next((a for a in answers if a["cau_hoi_id"] == body.cau_hoi_id), None)
        if answer is None:
            raise RuleError("Câu hỏi không thuộc lượt này")
        _, questions, options = load_items(db, attempt["bo_de_id"])
        q = questions[answer["cau_hoi_id"]]
        if answer["xac_nhan_luc"] is not None:  # Gửi lặp: trả lại kết quả cũ, không trừ thêm
            db.commit()
            return {"ket_qua": _feedback(q, options, answer, int(answer["nang_luong_tru"])), "ket_thuc": False,
                    **path_view.energy_and_kn(db, uid)}
        first_open = next(a for a in answers if a["xac_nhan_luc"] is None)
        if first_open["id"] != answer["id"]:
            raise ConflictError("Hãy trả lời các câu theo thứ tự")

        option_id, van_ban = None, None
        if q["dang"] in CHOICE_TYPES:
            if body.phuong_an_chon_id is not None:
                if body.phuong_an_chon_id not in {o["id"] for o in _shuffled(q, options, None)}:
                    raise RuleError("Phương án không thuộc câu hỏi")
                option_id = body.phuong_an_chon_id
        else:
            van_ban = (body.van_ban or "").strip() or None
        answer.update({"phuong_an_chon_id": option_id, "van_ban": van_ban})
        correct = bool(_is_correct(q, answer, options))

        cut = 0
        if not correct:
            if attempt["muc_dich"] in CONSUMING:
                energy = db.execute(text("SELECT nang_luong FROM nguoi_dung WHERE id = :u FOR UPDATE"), {"u": uid}).scalar_one()
                cut = 1 if energy > 0 else 0
                if cut:
                    db.execute(text("UPDATE nguoi_dung SET nang_luong = nang_luong - 1 WHERE id = :u"), {"u": uid})
            db.execute(
                text("""INSERT INTO so_tay (nguoi_dung_id, cau_hoi_goc_id, trang_thai, han_on, cap_nhat_luc)
                        VALUES (:u, :g, 'can_on', CURDATE(), NOW())
                        ON DUPLICATE KEY UPDATE trang_thai = 'can_on', han_on = CURDATE(), cap_nhat_luc = NOW()"""),
                {"u": uid, "g": q["ma_goc_id"]},
            )
        db.execute(
            text("""UPDATE cau_tra_loi SET phuong_an_chon_id = :o, van_ban = :v, xac_nhan_luc = NOW(),
                    phien_ban_luu = phien_ban_luu + 1, nang_luong_tru = :c WHERE id = :id"""),
            {"o": option_id, "v": van_ban, "c": cut, "id": answer["id"]},
        )
        db.execute(
            text("INSERT INTO ket_qua_cham (cau_tra_loi_id, lan, nguon, trang_thai, diem) VALUES (:a, 1, 'code', 'hoan_tat', :d)"),
            {"a": answer["id"], "d": 1 if correct else 0},
        )
        answer.update({"diem": 1 if correct else 0, "xac_nhan_luc": True})
        db.execute(text("UPDATE luot_lam SET vi_tri_hien_tai = :v WHERE id = :id"), {"v": answer["thu_tu"] + 1, "id": luot_id})

        finished = all(a["xac_nhan_luc"] is not None for a in answers)
        if finished:
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_nop', nop_luc = NOW(), ly_do_nop = 'nop_tay' WHERE id = :id"), {"id": luot_id})
            passed = all(a["diem"] is not None and float(a["diem"]) >= 1 for a in answers)
            if passed:  # đạt lần đầu (kể cả ô "Đã vượt" mở dạng ôn lại) → KN; INSERT IGNORE nên mỗi bài chỉ nhận một lần
                loai = db.execute(text("SELECT loai FROM bo_de WHERE id = :id"), {"id": attempt["bo_de_id"]}).scalar_one()
                reason, amount = KN[loai]
                db.execute(
                    text("""INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong, bo_de_goc_id)
                            VALUES (:u, :r, :n, :g)"""),
                    {"u": uid, "r": reason, "n": amount, "g": attempt["ma_goc_id"]},
                )
        db.commit()
        return {"ket_qua": _feedback(q, options, answer, cut), "ket_thuc": finished, **path_view.energy_and_kn(db, uid)}
    except Exception:
        db.rollback()
        raise


def abandon(db: Session, luot_id: int, uid: int) -> None:
    try:
        attempt = _lock(db, luot_id, uid)
        if attempt["trang_thai"] == "dang_lam":
            db.execute(text("UPDATE luot_lam SET trang_thai = 'da_bo' WHERE id = :id"), {"id": luot_id})
        db.commit()
    except Exception:
        db.rollback()
        raise
