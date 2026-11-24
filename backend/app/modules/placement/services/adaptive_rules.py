"""Các hàm thuần (Pure Functions) cho thuật toán Đánh giá trình độ đầu vào thích ứng 8 câu.

- Vai trò: Quyết định cấp HSK cần thăm dò cho từng vị trí câu (1..8), thứ tự cấp dự phòng khi thiếu câu
  và ước lượng cấp HSK bắt đầu đề xuất từ kết quả làm bài.
- Đặc điểm thiết kế: KHÔNG truy cập CSDL, KHÔNG gọi AI, đầu vào -> đầu ra hoàn toàn tất định (deterministic),
  giúp chạy kiểm thử tự động toàn bộ 4^6 = 4.096 tổ hợp rẽ nhánh trong vài mili-giây (AT46).
"""
from typing import Literal

ActionState = Literal["chua_thao_tac", "da_tra_loi", "bo_qua", "loi_ky_thuat"]

# Cấu trúc 8 câu đánh giá đầu vào theo đúng Mục 1 tài liệu nghiệp vụ đã chốt:
# Cặp (1,2): Từ vựng | Cặp (3,4): Đọc | Cặp (5,6): Nghe | Câu 7: Dịch câu | Câu 8: Sắp xếp câu
SLOT_SPEC: dict[int, dict] = {
    1: {"ky_nang": "tu_vung", "dang": ("chon_mot",), "pair_first": None, "require_audio": False},
    2: {"ky_nang": "tu_vung", "dang": ("chon_mot",), "pair_first": 1, "require_audio": False},
    3: {"ky_nang": "doc", "dang": ("chon_mot", "dung_sai"), "pair_first": None, "require_audio": False},
    4: {"ky_nang": "doc", "dang": ("chon_mot", "dung_sai"), "pair_first": 3, "require_audio": False},
    5: {"ky_nang": "nghe", "dang": ("chon_mot", "dung_sai"), "pair_first": None, "require_audio": True},
    6: {"ky_nang": "nghe", "dang": ("chon_mot", "dung_sai"), "pair_first": 5, "require_audio": True},
    7: {"ky_nang": "viet", "dang": ("dich_cau",), "pair_first": None, "require_audio": False},
    8: {"ky_nang": "viet", "dang": ("sap_xep",), "pair_first": None, "require_audio": False},
}


def next_pair_target_order(
    first_action: ActionState,
    first_correct: bool | None,
    current_target_order: int = 2,
) -> int:
    """Tính cấp HSK mục tiêu (1..4) cho câu thứ hai trong cặp (1->2), (3->4), (5->6).

    - Câu đầu cặp gặp 'loi_ky_thuat': giữ nguyên cấp đang thăm dò (mặc định HSK 2).
    - Câu đầu cặp trả lời đúng ('da_tra_loi' và first_correct=True): tăng lên HSK 3.
    - Câu đầu cặp làm sai hoặc chủ động 'bo_qua': lùi xuống HSK 1.
    """
    if first_action == "loi_ky_thuat":
        return max(1, min(4, current_target_order))
    if first_action == "da_tra_loi" and first_correct is True:
        return 3
    return 1


def writing_target_order(first_four_outcomes: list[dict]) -> int:
    """Tính cấp HSK mục tiêu (1..4) cho Câu 7 (Dịch câu) và Câu 8 (Sắp xếp từ) dựa trên kết quả Câu 1–4.

    Mỗi phần tử trong `first_four_outcomes` có dạng:
      {"trang_thai_thao_tac": str, "dung": bool, "cap_thuc_te_thu_tu": int}
    Câu gặp 'loi_ky_thuat' hoặc 'bo_qua' được xem là chưa có bằng chứng đúng ở vị trí đó.
    """
    high_correct = 0
    hsk2_correct = 0
    for item in first_four_outcomes:
        if item.get("trang_thai_thao_tac") != "da_tra_loi" or not item.get("dung"):
            continue
        actual_order = int(item.get("cap_thuc_te_thu_tu") or 1)
        if actual_order >= 3:
            high_correct += 1
        elif actual_order == 2:
            hsk2_correct += 1

    if high_correct >= 2:
        return 4
    if high_correct == 1:
        return 3
    if hsk2_correct >= 1:
        return 2
    return 1


def compute_slot_target_order(slot_pos: int, prior_outcomes: dict[int, dict]) -> int:
    """Xác định cấp HSK mục tiêu (thu_tu 1..4) cho vị trí câu `slot_pos` (1..8) dựa vào các câu trước đó."""
    if slot_pos in (1, 3, 5):
        return 2
    if slot_pos in (2, 4, 6):
        first_pos = SLOT_SPEC[slot_pos]["pair_first"]
        first = prior_outcomes.get(first_pos, {})
        return next_pair_target_order(
            first.get("trang_thai_thao_tac", "bo_qua"),
            first.get("dung"),
            int(first.get("cap_muc_tieu_thu_tu") or 2),
        )
    if slot_pos in (7, 8):
        first_four = [prior_outcomes[i] for i in (1, 2, 3, 4) if i in prior_outcomes]
        return writing_target_order(first_four)
    raise ValueError(f"Vị trí câu đánh giá đầu vào không hợp lệ: {slot_pos}")


def fallback_level_orders(target_order: int, max_order: int = 4) -> list[int]:
    """Trả về thứ tự cấp HSK (1..max_order) cần thử khi ngân hàng thiếu câu ở cấp `target_order`.

    Ưu tiên chính cấp `target_order`, sau đó xét khoảng cách tăng dần:
    cấp liền dưới trước (`target - d`), cấp liền trên sau (`target + d`).
    Ví dụ target=2 -> [2, 1, 3, 4]; target=3 -> [3, 2, 4, 1].
    """
    result: list[int] = []
    if 1 <= target_order <= max_order:
        result.append(target_order)
    for delta in range(1, max_order):
        lower = target_order - delta
        if 1 <= lower <= max_order and lower not in result:
            result.append(lower)
        higher = target_order + delta
        if 1 <= higher <= max_order and higher not in result:
            result.append(higher)
    return result


def propose_starting_level_order(outcomes: list[dict]) -> int:
    """Tính cấp HSK bắt đầu đề xuất (1..4) một cách thận trọng từ kết quả 8 câu đã chấm.

    Nguyên tắc sư phạm:
    - Bỏ qua các câu 'loi_ky_thuat' khi tính tỷ lệ, không phạt học viên vì lỗi hệ thống.
    - Chỉ đề xuất bắt đầu ở cấp L (L >= 2) khi học viên đã trả lời đúng đủ bằng chứng nền ở cấp <= L
      và không bị hổng nặng ở các câu cơ bản (HSK 1–2).
    """
    valid = [o for o in outcomes if o.get("trang_thai_thao_tac") in ("da_tra_loi", "bo_qua")]
    if not valid:
        return 1

    right_by_level = {1: 0, 2: 0, 3: 0, 4: 0}
    total_by_level = {1: 0, 2: 0, 3: 0, 4: 0}
    total_right = 0

    for o in valid:
        lv = max(1, min(4, int(o.get("cap_thuc_te_thu_tu") or 1)))
        total_by_level[lv] += 1
        if o.get("trang_thai_thao_tac") == "da_tra_loi" and o.get("dung"):
            right_by_level[lv] += 1
            total_right += 1

    high_right = right_by_level[3] + right_by_level[4]
    mid_or_high_right = right_by_level[2] + high_right

    if total_right >= 7 and high_right >= 3 and right_by_level[4] >= 1:
        return 4
    if total_right >= 5 and high_right >= 2:
        return 3
    if total_right >= 3 and mid_or_high_right >= 2:
        return 2
    return 1
