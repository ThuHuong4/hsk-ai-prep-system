"""Bộ chấm câu hỏi có đáp án xác định (dùng chung cho Thi thử, Ôn luyện, Kiểm tra vượt, Sổ tay và Đánh giá đầu vào)."""
import re
import unicodedata

CHOICE_TYPES = ("chon_mot", "dung_sai", "chon_bo_chung")
TEXT_OBJECTIVE_TYPES = ("sap_xep", "dien_chu")
OBJECTIVE_TYPES = (*CHOICE_TYPES, *TEXT_OBJECTIVE_TYPES)
AI_GRADED_TYPES = ("viet_mo", "dich_cau")

_PUNCTUATION_AND_SPACE = re.compile(r"[\s　.,!?;:'\"“”‘’。，！？；：、（）()《》…·-]+")


def normalize_answer_text(value: str | None) -> str:
    """Chuẩn hóa câu trả lời dạng chữ (gộp Unicode NFKC, bỏ khoảng trắng và dấu câu) để so khớp đáp án."""
    if not value:
        return ""
    return _PUNCTUATION_AND_SPACE.sub("", unicodedata.normalize("NFKC", value)).lower()


def correct_option_id(q: dict, options: dict) -> int | None:
    """Tìm ID phương án đúng của câu trắc nghiệm (hỗ trợ cả câu đơn và câu con dùng chung bộ phương án)."""
    if q["dang"] == "chon_bo_chung":
        shared = options[q["cau_cha_id"]]["lua_chon"]
        match = next((o for o in shared if o["thu_tu"] == q["dap_an_thu_tu"]), None)
        return match["id"] if match else None
    match = next((o for o in options[q["id"]]["lua_chon"] if o["la_dap_an_dung"]), None)
    return match["id"] if match else None


def is_correct(q: dict, answer: dict, options: dict) -> bool | None:
    """Trả về True/False cho câu chấm tự động bằng code; trả về None cho câu tự luận (viet_mo, dich_cau)."""
    if q["dang"] in CHOICE_TYPES:
        chosen_id = answer.get("phuong_an_chon_id")
        return chosen_id is not None and chosen_id == correct_option_id(q, options)
    if q["dang"] in TEXT_OBJECTIVE_TYPES:
        given = normalize_answer_text(answer.get("van_ban"))
        return bool(given) and any(
            given == normalize_answer_text(o["noi_dung"]) for o in options[q["id"]]["chap_nhan"]
        )
    return None
