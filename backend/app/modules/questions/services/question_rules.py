"""Kiểm tra nội dung câu hỏi theo dạng trước khi lưu."""


class QuestionRuleError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


DANG_LABELS = {
    "ngu_lieu": "Ngữ liệu chung",
    "chon_mot": "Chọn một đáp án",
    "dung_sai": "Đúng/Sai",
    "chon_bo_chung": "Chọn từ bộ phương án chung",
    "sap_xep": "Sắp xếp câu",
    "dien_chu": "Điền chữ",
    "viet_mo": "Viết mở",
}


def resolve_audio_verified_flag(
    old_audio: str | None,
    new_audio: str | None,
    requested_verified: bool = False,
) -> bool:
    """Tự động đặt lại cờ da_kiem_tra_audio = False khi không có audio hoặc khi đổi sang tệp audio khác."""
    if not new_audio:
        return False
    if old_audio != new_audio:
        return False
    return bool(requested_verified)


def _has_content(q) -> bool:
    # Câu Nghe trong đề dùng âm thanh chung của đề: lời nghe (transcript) cũng tính là nội dung
    return bool(q.noi_dung or q.tep_audio or q.tep_hinh or q.loi_nghe)


def _check_options(q, where: str, need_correct: bool, min_count: int) -> None:
    options = q.phuong_an
    if len(options) < min_count:
        raise QuestionRuleError(f"{where}: cần ít nhất {min_count} phương án")
    for index, option in enumerate(options, start=1):
        if not (option.noi_dung or option.tep_hinh):
            raise QuestionRuleError(f"{where}: phương án {index} chưa có nội dung hoặc hình")
    correct = sum(1 for o in options if o.la_dap_an_dung)
    if need_correct and correct != 1:
        raise QuestionRuleError(f"{where}: phải chọn đúng 1 đáp án đúng")
    if not need_correct and correct:
        raise QuestionRuleError(f"{where}: dạng này không đánh dấu đáp án đúng trong phương án")


def _check_no_options(q, where: str) -> None:
    if q.phuong_an:
        raise QuestionRuleError(f"{where}: dạng này không có phương án lựa chọn")


def _check_answerable(q, where: str, shared_count: int) -> None:
    """Kiểm tra một câu có chấm điểm (câu đơn hoặc câu con)."""
    dang = q.dang
    if dang != "chon_bo_chung" and not _has_content(q):
        raise QuestionRuleError(f"{where}: cần nội dung, hình, âm thanh hoặc lời nghe")
    if dang != "chon_bo_chung" and q.dap_an_thu_tu is not None:
        raise QuestionRuleError(f"{where}: chỉ dạng chọn từ bộ chung mới có số thứ tự đáp án")
    if dang != "viet_mo" and (q.diem_toi_da is not None or q.nguong_dat is not None):
        raise QuestionRuleError(f"{where}: chỉ dạng Viết mở mới có điểm tối đa và ngưỡng đạt")
    if dang not in ("sap_xep", "dien_chu") and q.dap_an_chap_nhan:
        raise QuestionRuleError(f"{where}: dạng này không có danh sách đáp án chấp nhận")

    if dang == "chon_mot":
        _check_options(q, where, need_correct=True, min_count=2)
    elif dang == "dung_sai":
        _check_options(q, where, need_correct=True, min_count=2)
        if len(q.phuong_an) != 2:
            raise QuestionRuleError(f"{where}: Đúng/Sai có đúng 2 phương án")
    elif dang == "chon_bo_chung":
        _check_no_options(q, where)
        if shared_count < 2:
            raise QuestionRuleError(f"{where}: ngữ liệu cha cần ít nhất 2 phương án dùng chung")
        if q.dap_an_thu_tu is None or q.dap_an_thu_tu > shared_count:
            raise QuestionRuleError(f"{where}: chọn đáp án trong bộ phương án chung (1–{shared_count})")
    elif dang == "sap_xep":
        _check_options(q, where, need_correct=False, min_count=2)
        if not q.dap_an_chap_nhan:
            raise QuestionRuleError(f"{where}: cần ít nhất 1 câu đúng sau khi sắp xếp")
    elif dang == "dien_chu":
        _check_no_options(q, where)
        if not q.dap_an_chap_nhan:
            raise QuestionRuleError(f"{where}: cần ít nhất 1 đáp án chấp nhận")
    elif dang == "viet_mo":
        _check_no_options(q, where)
        if q.diem_toi_da is None or q.nguong_dat is None:
            raise QuestionRuleError(f"{where}: cần điểm tối đa và ngưỡng đạt")
        if q.nguong_dat > q.diem_toi_da:
            raise QuestionRuleError(f"{where}: ngưỡng đạt không được lớn hơn điểm tối đa")
        if not q.tieu_chi_mo_ta:
            raise QuestionRuleError(f"{where}: cần mô tả tiêu chí chấm")
    if dang != "viet_mo" and q.tu_bat_buoc:
        raise QuestionRuleError(f"{where}: chỉ dạng Viết mở mới có từ bắt buộc")


def validate_question(q) -> None:
    if q.tu_vung_id is not None and q.ky_nang != "tu_vung":
        raise QuestionRuleError("Chỉ câu kỹ năng Từ vựng mới gắn từ")
    if q.dang == "ngu_lieu":
        if not _has_content(q) and len(q.phuong_an) < 2:
            raise QuestionRuleError("Ngữ liệu: cần nội dung, hình, âm thanh hoặc bộ phương án chung")
        if not q.cau_con:
            raise QuestionRuleError("Ngữ liệu: cần ít nhất 1 câu con")
        if q.dap_an_chap_nhan or q.dap_an_thu_tu is not None or q.diem_toi_da is not None:
            raise QuestionRuleError("Ngữ liệu: không có đáp án riêng; đáp án nằm ở từng câu con")
        if q.phuong_an:
            _check_options(q, "Bộ phương án chung", need_correct=False, min_count=2)
        shared = len(q.phuong_an)
        for index, child in enumerate(q.cau_con, start=1):
            _check_answerable(child, f"Câu con {index}", shared)
        return
    if q.cau_con:
        raise QuestionRuleError("Chỉ Ngữ liệu chung mới có câu con")
    if q.dang == "chon_bo_chung":
        raise QuestionRuleError("Dạng chọn từ bộ chung phải là câu con của ngữ liệu")
    _check_answerable(q, "Câu hỏi", 0)
