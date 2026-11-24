"""Cấu trúc đề HSK 2.0 cấp 1–4 (theo mô tả đề chính thức của Chinese Testing International / chinesetest.cn).

Mỗi phần (phan) gồm một hoặc nhiều đoạn (seg); mỗi đoạn là một kiểu câu (kieu) với số câu (so_cau).
Kiểu câu "cụm" (ngữ liệu chung) tính theo câu con: so_cau phải chia hết cho kích thước cụm.
thoi_luong_phut = thời gian làm bài (không tính 5 phút điền thông tin cá nhân).
"""
import re

# kieu -> (kỹ năng, kích thước cụm; 1 = câu đơn)
KINDS = {
    "nghe_tranh_dung_sai": ("nghe", 1),
    "nghe_chon_tranh": ("nghe", 1),
    "nghe_noi_tranh": ("nghe", 5),
    "nghe_chon_chu": ("nghe", 1),
    "nghe_phan_doan": ("nghe", 1),
    "nghe_doan_2cau": ("nghe", 2),
    "doc_tranh_tu": ("doc", 1),
    "doc_noi_tranh": ("doc", 5),
    "doc_ghep_cau": ("doc", 5),
    "doc_chon_tu": ("doc", 5),
    "doc_phan_doan": ("doc", 1),
    "doc_doan_chon": ("doc", 1),
    "doc_doan_2cau": ("doc", 2),
    "doc_sap_xep_doan": ("doc", 1),
    "viet_sap_xep": ("viet", 1),
    "viet_dien_chu": ("viet", 1),
    "viet_tranh": ("viet", 1),
}


def _seg(kieu: str, so_cau: int, so_lua_chon: int | None = None, dai: bool = False) -> dict:
    return {"kieu": kieu, "so_cau": so_cau, "so_lua_chon": so_lua_chon, "dai": dai}


def _part(phan: int, ten: str, mo_ta: str, *segs: dict) -> dict:
    skill = KINDS[segs[0]["kieu"]][0]
    return {"phan": phan, "ky_nang": skill, "ten": ten, "mo_ta": mo_ta,
            "so_cau": sum(s["so_cau"] for s in segs), "doan": list(segs)}


BLUEPRINT = {
    1: {"thoi_luong_phut": 40, "phat_nghe": 2, "phan": [
        _part(1, "听力 第一部分", "Nghe cụm từ, xem tranh, phán đoán Đúng/Sai", _seg("nghe_tranh_dung_sai", 5)),
        _part(2, "听力 第二部分", "Nghe câu, chọn 1 trong 3 tranh", _seg("nghe_chon_tranh", 5, 3)),
        _part(3, "听力 第三部分", "Nghe hội thoại, chọn tranh A–F", _seg("nghe_noi_tranh", 5)),
        _part(4, "听力 第四部分", "Nghe câu và câu hỏi, chọn A/B/C", _seg("nghe_chon_chu", 5, 3)),
        _part(5, "阅读 第一部分", "Xem tranh và từ, phán đoán Đúng/Sai", _seg("doc_tranh_tu", 5)),
        _part(6, "阅读 第二部分", "Đọc câu, chọn tranh A–F", _seg("doc_noi_tranh", 5)),
        _part(7, "阅读 第三部分", "Ghép câu hỏi với câu trả lời A–F", _seg("doc_ghep_cau", 5)),
        _part(8, "阅读 第四部分", "Chọn từ A–F điền vào chỗ trống", _seg("doc_chon_tu", 5)),
    ]},
    2: {"thoi_luong_phut": 55, "phat_nghe": 2, "phan": [
        _part(1, "听力 第一部分", "Nghe câu, xem tranh, phán đoán Đúng/Sai", _seg("nghe_tranh_dung_sai", 10)),
        _part(2, "听力 第二部分", "Nghe hội thoại, chọn tranh A–F", _seg("nghe_noi_tranh", 10)),
        _part(3, "听力 第三部分", "Hội thoại ngắn 2 câu, câu hỏi do người thứ ba đọc, chọn A/B/C",
              _seg("nghe_chon_chu", 10, 3)),
        _part(4, "听力 第四部分", "Hội thoại dài 4–5 câu, chọn A/B/C", _seg("nghe_chon_chu", 5, 3, dai=True)),
        _part(5, "阅读 第一部分", "Đọc câu, chọn tranh A–F", _seg("doc_noi_tranh", 5)),
        _part(6, "阅读 第二部分", "Chọn từ A–F điền vào chỗ trống", _seg("doc_chon_tu", 5)),
        _part(7, "阅读 第三部分", "Đọc đoạn, phán đoán câu ★ Đúng/Sai", _seg("doc_phan_doan", 5)),
        _part(8, "阅读 第四部分", "Ghép câu với câu trả lời A–F", _seg("doc_ghep_cau", 10)),
    ]},
    3: {"thoi_luong_phut": 90, "phat_nghe": 2, "phan": [
        _part(1, "听力 第一部分", "Nghe hội thoại, chọn tranh A–F", _seg("nghe_noi_tranh", 10)),
        _part(2, "听力 第二部分", "Nghe đoạn nói, phán đoán câu ★ Đúng/Sai", _seg("nghe_phan_doan", 10)),
        _part(3, "听力 第三部分", "Hội thoại ngắn, câu hỏi do người thứ ba đọc, chọn A/B/C",
              _seg("nghe_chon_chu", 10, 3)),
        _part(4, "听力 第四部分", "Hội thoại dài 4–5 câu, chọn A/B/C", _seg("nghe_chon_chu", 10, 3, dai=True)),
        _part(5, "阅读 第一部分", "Ghép câu với câu trả lời A–F", _seg("doc_ghep_cau", 10)),
        _part(6, "阅读 第二部分", "Chọn từ A–F điền vào chỗ trống", _seg("doc_chon_tu", 10)),
        _part(7, "阅读 第三部分", "Đọc đoạn ngắn, chọn A/B/C", _seg("doc_doan_chon", 10, 3)),
        _part(8, "书写 第一部分", "Sắp xếp từ thành câu", _seg("viet_sap_xep", 5)),
        _part(9, "书写 第二部分", "Viết chữ Hán theo pinyin", _seg("viet_dien_chu", 5)),
    ]},
    4: {"thoi_luong_phut": 105, "phat_nghe": 1, "phan": [
        _part(1, "听力 第一部分", "Nghe đoạn nói, phán đoán câu ★ Đúng/Sai", _seg("nghe_phan_doan", 10)),
        _part(2, "听力 第二部分", "Hội thoại ngắn, chọn A/B/C/D", _seg("nghe_chon_chu", 15, 4)),
        _part(3, "听力 第三部分", "Hội thoại dài và đoạn nói (mỗi đoạn 2 câu hỏi), chọn A/B/C/D",
              _seg("nghe_chon_chu", 10, 4, dai=True), _seg("nghe_doan_2cau", 10, 4)),
        _part(4, "阅读 第一部分", "Chọn từ A–F điền vào chỗ trống", _seg("doc_chon_tu", 10)),
        _part(5, "阅读 第二部分", "Sắp xếp 3 câu A, B, C thành đoạn", _seg("doc_sap_xep_doan", 10)),
        _part(6, "阅读 第三部分", "Đọc đoạn văn (có đoạn 2 câu hỏi), chọn A/B/C/D",
              _seg("doc_doan_chon", 14, 4), _seg("doc_doan_2cau", 6, 4)),
        _part(7, "书写 第一部分", "Sắp xếp từ thành câu", _seg("viet_sap_xep", 10)),
        _part(8, "书写 第二部分", "Xem tranh, dùng từ cho sẵn viết câu", _seg("viet_tranh", 5)),
    ]},
}

_DIGIT = re.compile(r"(\d+)")


def level_number(ma: str | None, ten: str | None) -> int | None:
    """Lấy số cấp HSK từ mã hoặc tên cấp ("HSK1", "HSK 2"...); không có trong bảng cấu trúc thì None."""
    for value in (ma, ten):
        found = _DIGIT.search(value or "")
        if found and int(found.group(1)) in BLUEPRINT:
            return int(found.group(1))
    return None


def find_part(level: int, phan: int) -> dict | None:
    return next((p for p in BLUEPRINT[level]["phan"] if p["phan"] == phan), None)
