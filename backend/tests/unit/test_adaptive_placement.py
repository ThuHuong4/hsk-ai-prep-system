"""Kiểm thử đơn vị toàn diện cho thuật toán Đánh giá đầu vào thích ứng 8 câu (AT46, AT47) và quy tắc audio.

- Chạy độc lập không cần kết nối CSDL vì `adaptive_rules.py` và `resolve_audio_verified_flag` là các hàm thuần.
- Kiểm chứng vét cạn toàn bộ 4^6 = 4.096 tổ hợp trạng thái của 6 câu đầu tiên (Đúng, Sai, Bỏ qua, Lỗi kỹ thuật).
"""
import itertools
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.placement.services.adaptive_rules import (
    compute_slot_target_order,
    fallback_level_orders,
    next_pair_target_order,
    propose_starting_level_order,
    writing_target_order,
)
from app.modules.questions.services.question_rules import resolve_audio_verified_flag

STATES = (
    ("da_tra_loi", True),   # Trả lời đúng
    ("da_tra_loi", False),  # Trả lời sai
    ("bo_qua", False),      # Chủ động bỏ qua
    ("loi_ky_thuat", False) # Lỗi kỹ thuật âm thanh / hiển thị
)


def test_exhaustive_4096_adaptive_combinations_at46():
    """AT46: Vét cạn toàn bộ 4^6 = 4.096 tổ hợp kết quả của câu 1..6, đảm bảo mọi nhánh đều hợp lệ 1..4 và tất định."""
    count = 0
    for combo in itertools.product(STATES, repeat=6):
        count += 1
        prior: dict[int, dict] = {}
        for slot_pos in range(1, 7):
            target = compute_slot_target_order(slot_pos, prior)
            assert target in (1, 2, 3, 4), f"Slot {slot_pos} sinh cấp ngoài miền 1..4: {target}"
            action, is_right = combo[slot_pos - 1]
            prior[slot_pos] = {
                "trang_thai_thao_tac": action,
                "dung": is_right,
                "cap_muc_tieu_thu_tu": target,
                "cap_thuc_te_thu_tu": target,
            }

        # Kiểm tra bất biến cặp (1->2), (3->4), (5->6)
        for first_pos, second_pos in ((1, 2), (3, 4), (5, 6)):
            assert prior[first_pos]["cap_muc_tieu_thu_tu"] == 2
            f_act = prior[first_pos]["trang_thai_thao_tac"]
            f_ok = prior[first_pos]["dung"]
            sec_target = prior[second_pos]["cap_muc_tieu_thu_tu"]
            if f_act == "loi_ky_thuat":
                assert sec_target == 2
            elif f_act == "da_tra_loi" and f_ok:
                assert sec_target == 3
            else:
                assert sec_target == 1

        # Câu 7 và Câu 8 chỉ phụ thuộc vào Câu 1..4 (độc lập với Câu 5..6)
        t7 = compute_slot_target_order(7, prior)
        t8 = compute_slot_target_order(8, prior)
        assert t7 == t8
        assert t7 in (1, 2, 3, 4)

    assert count == 4096


def test_pair_and_writing_edge_cases():
    """Kiểm tra riêng trường hợp lỗi kỹ thuật không phạt tụt cấp và tính cấp câu 7–8 theo cấp thực tế."""
    assert next_pair_target_order("loi_ky_thuat", None, 2) == 2
    assert next_pair_target_order("da_tra_loi", True, 2) == 3
    assert next_pair_target_order("da_tra_loi", False, 2) == 1
    assert next_pair_target_order("bo_qua", False, 2) == 1

    # Đúng 2 câu HSK 3 ở câu 2 và câu 4 -> câu 7–8 lên HSK 4
    outcomes_hsk4 = [
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 2},
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 3},
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 2},
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 3},
    ]
    assert writing_target_order(outcomes_hsk4) == 4

    # Câu 2 bị lỗi kỹ thuật, câu 4 đúng HSK 3 -> còn 1 bằng chứng HSK 3 -> câu 7–8 ở HSK 3
    outcomes_tech_err = [
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 2},
        {"trang_thai_thao_tac": "loi_ky_thuat", "dung": False, "cap_thuc_te_thu_tu": 3},
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 2},
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": 3},
    ]
    assert writing_target_order(outcomes_tech_err) == 3


def test_fallback_level_orders_at47():
    """AT47: Ưu tiên chính cấp mục tiêu, sau đó cấp liền dưới trước rồi cấp liền trên."""
    assert fallback_level_orders(2, 4) == [2, 1, 3, 4]
    assert fallback_level_orders(3, 4) == [3, 2, 4, 1]
    assert fallback_level_orders(1, 4) == [1, 2, 3, 4]
    assert fallback_level_orders(4, 4) == [4, 3, 2, 1]


def test_propose_starting_level_conservative():
    all_wrong = [{"trang_thai_thao_tac": "da_tra_loi", "dung": False, "cap_thuc_te_thu_tu": 1} for _ in range(8)]
    assert propose_starting_level_order(all_wrong) == 1

    strong_hsk4 = [
        {"trang_thai_thao_tac": "da_tra_loi", "dung": True, "cap_thuc_te_thu_tu": lv}
        for lv in (2, 3, 2, 3, 2, 3, 4, 4)
    ]
    assert propose_starting_level_order(strong_hsk4) == 4


def test_audio_verified_flag_auto_resets():
    assert resolve_audio_verified_flag("audio/a.mp3", "audio/a.mp3", True) is True
    assert resolve_audio_verified_flag("audio/a.mp3", "audio/b.mp3", True) is False
    assert resolve_audio_verified_flag("audio/a.mp3", None, True) is False


import unittest


class AdaptivePlacementUnitTests(unittest.TestCase):
    def test_exhaustive_4096_at46(self):
        test_exhaustive_4096_adaptive_combinations_at46()

    def test_pair_and_writing_edges(self):
        test_pair_and_writing_edge_cases()

    def test_fallback_orders_at47(self):
        test_fallback_level_orders_at47()

    def test_starting_level_proposal(self):
        test_propose_starting_level_conservative()

    def test_audio_flag_reset(self):
        test_audio_verified_flag_auto_resets()


if __name__ == "__main__":
    unittest.main()
