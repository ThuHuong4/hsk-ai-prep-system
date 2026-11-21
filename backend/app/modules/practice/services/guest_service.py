"""Học thử Ôn luyện cho Khách (chưa đăng nhập).

- Bản đồ giống Học viên (thửa/bài đang đăng); tiến độ và năng lượng của Khách nằm trên trình duyệt.
- Máy chủ KHÔNG ghi gì vào CSDL: không lượt làm, không KN, không Sổ tay.
- Câu hỏi gửi xuống không kèm đáp án; chấm từng câu ở máy chủ.
"""
import random

from sqlalchemy.orm import Session

from app.modules.common.service_errors import ConflictError, RuleError
from app.modules.mock_tests.services.attempt_service import _is_correct
from app.modules.mock_tests.services.content import correct_option_id, load_items
from app.modules.practice.services import path_view
from app.modules.practice.services.lesson_service import CHOICE_TYPES, _lesson_scope, _shuffled, _word

GUEST_UID = 0  # không trùng tài khoản nào → mọi ô ở trạng thái gốc


def _strip(lands: list[dict]) -> list[dict]:
    for land in lands:
        for slot in land["o"]:
            slot.pop("luot_dang_lam", None)
    return lands


def guest_path(db: Session, skill: str, cap_do_id: int | None) -> dict:
    lv = path_view.skill_levels(db, skill)
    tabs = []
    for level in lv:
        opened = path_view.level_open(level, skill)
        info = {"id": level["id"], "ten": level["ten"], "mo": opened}
        if opened:
            lands = path_view.build_map(db, GUEST_UID, level["id"], skill)
            info["so_bai"] = sum(1 for land in lands for o in land["o"] if o["trang_thai"] != "chua_xuat_ban")
        tabs.append(info)
    chosen = next((l for l in lv if l["id"] == cap_do_id), None) if cap_do_id else None
    if chosen is None:
        chosen = next((l for l in lv if path_view.level_open(l, skill)), lv[0] if lv else None)
    opened = bool(chosen) and path_view.level_open(chosen, skill)
    lands = _strip(path_view.build_map(db, GUEST_UID, chosen["id"], skill)) if opened else []
    return {
        "ky_nang": skill, "cap": tabs, "thua": lands,
        "cap_do": chosen and {"id": chosen["id"], "ten": chosen["ten"], "mo": opened},
    }


def guest_overview(db: Session) -> dict:
    """Mỗi kỹ năng: cấp mở sẵn và các thửa của cấp đó (trình duyệt tự tính tiến độ của Khách)."""
    lv = path_view.levels(db)
    skills = []
    for skill in path_view.SKILLS:
        level = next((l for l in lv if path_view.level_open(l, skill)), None)
        lands = _strip(path_view.build_map(db, GUEST_UID, level["id"], skill)) if level else []
        skills.append({"ky_nang": skill, "cap_do": level and {"id": level["id"], "ten": level["ten"]}, "thua": lands})
    return {"ky_nang": skills}


def _scope(db: Session, ma_goc_id: int) -> dict:
    lesson = _lesson_scope(db, ma_goc_id)
    level = next((l for l in path_view.levels(db) if l["id"] == lesson["cap_do_id"]), None)
    if level is None or not path_view.level_open(level, lesson["ky_nang"]):
        raise ConflictError("Cấp này của kỹ năng chưa mở")
    return lesson


def guest_lesson(db: Session, ma_goc_id: int) -> dict:
    lesson = _scope(db, ma_goc_id)
    items, questions, options = load_items(db, lesson["id"])
    if not items:
        raise RuleError("Bài chưa có câu hỏi")
    if any(questions[i["cau_hoi_id"]]["dang"] == "viet_mo" for i in items):
        raise RuleError("Bài có câu Viết mở cần AI chấm, chức năng này chưa hỗ trợ")
    rng = random.SystemRandom()
    order = [i["cau_hoi_id"] for i in items]
    rng.shuffle(order)
    out, words, seen = [], [], set()
    for pos, qid in enumerate(order, start=1):
        q = questions[qid]
        parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
        out.append({
            "thu_tu": pos,
            "cau_hoi": {"id": q["id"], "dang": q["dang"], "noi_dung": q["noi_dung"], "pinyin": q["pinyin"], "tep_hinh": q["tep_hinh"],
                        "tep_audio": q["tep_audio"], "mo_ta_hinh": q["mo_ta_hinh"], "goi_y": q["goi_y"], "nghia_cau": q["dich_nghia"] if q["dang"] == "sap_xep" else None},
            "ngu_lieu": parent and {"noi_dung": parent["noi_dung"], "pinyin": parent["pinyin"], "tep_hinh": parent["tep_hinh"],
                                    "tep_audio": parent["tep_audio"]},
            "phuong_an": _shuffled(q, options, rng.randrange(1, 2**31)),
        })
        word = _word(db, q.get("tu_vung_id")) if lesson["ky_nang"] == "tu_vung" else None
        if word and word["id"] not in seen:
            seen.add(word["id"])
            words.append(word)
    return {
        "bai": {"ma_goc_id": lesson["ma_goc_id"], "ten": lesson["ten"], "loai": lesson["loai"], "vi_tri": lesson["vi_tri"],
                "thua": lesson["ten_thua"], "thua_id": lesson["thua_id"], "ky_nang": lesson["ky_nang"],
                "cap_do_id": lesson["cap_do_id"], "ten_cap_do": lesson["ten_cap_do"]},
        "cau_hoi": out, "the_tu": words,
    }


def _question_in_lesson(db: Session, ma_goc_id: int, cau_hoi_id: int) -> tuple[dict, dict, dict]:
    lesson = _scope(db, ma_goc_id)
    items, questions, options = load_items(db, lesson["id"])
    if cau_hoi_id not in {i["cau_hoi_id"] for i in items}:
        raise RuleError("Câu hỏi không thuộc bài này")
    return lesson, questions, options


def guest_check(db: Session, ma_goc_id: int, body) -> dict:
    _, questions, options = _question_in_lesson(db, ma_goc_id, body.cau_hoi_id)
    q = questions[body.cau_hoi_id]
    answer = {"phuong_an_chon_id": None, "van_ban": None}
    if q["dang"] in CHOICE_TYPES:
        if body.phuong_an_chon_id is not None:
            if body.phuong_an_chon_id not in {o["id"] for o in _shuffled(q, options, None)}:
                raise RuleError("Phương án không thuộc câu hỏi")
            answer["phuong_an_chon_id"] = body.phuong_an_chon_id
    else:
        answer["van_ban"] = (body.van_ban or "").strip() or None
    return {"ket_qua": {
        "dung": bool(_is_correct(q, answer, options)),
        "bo_qua": answer["phuong_an_chon_id"] is None and not answer["van_ban"],
        "dap_an_id": correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None,
        "dap_an_chap_nhan": [o["noi_dung"] for o in options[q["id"]]["chap_nhan"]],
        "giai_thich": q["giai_thich"], "dich_nghia": q["dich_nghia"], "loi_nghe": q["loi_nghe"],
    }}


def guest_context(db: Session, ma_goc_id: int, cau_hoi_id: int, option_id: int | None, van_ban: str | None) -> str:
    """Ngữ cảnh cho Hỏi Xiang, chỉ lấy câu thuộc bài đang đăng."""
    lesson, questions, options = _question_in_lesson(db, ma_goc_id, cau_hoi_id)
    q = questions[cau_hoi_id]
    parent = questions[q["cau_cha_id"]] if q["cau_cha_id"] else None
    owner = q["cau_cha_id"] if q["dang"] == "chon_bo_chung" else q["id"]
    letters = "ABCDEFGH"
    opts = options[owner]["lua_chon"]
    right_id = correct_option_id(q, options) if q["dang"] in CHOICE_TYPES else None
    label = {o["id"]: f"{letters[i]}. {o['noi_dung'] or '(hình)'}" for i, o in enumerate(opts)}
    answer = {"phuong_an_chon_id": option_id if option_id in label else None, "van_ban": (van_ban or "").strip() or None}
    lines = [f"Bài: {lesson['ten']} (thửa {lesson['ten_thua']}, {lesson['ten_cap_do']}, kỹ năng {lesson['ky_nang']})"]
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
        lines.append(f"Đáp án đúng: {label.get(right_id, 'không rõ')}")
    else:
        lines.append(f"Học viên viết: {answer['van_ban'] or 'bỏ qua'}")
        lines.append("Đáp án chấp nhận: " + " / ".join(o["noi_dung"] for o in options[q["id"]]["chap_nhan"]))
    lines.append(f"Kết quả: {'Đúng' if _is_correct(q, answer, options) else 'Sai'}")
    for key, name in (("dich_nghia", "Dịch nghĩa"), ("giai_thich", "Giải thích")):
        if q.get(key):
            lines.append(f"{name}: {q[key]}")
    return "\n".join(lines)

