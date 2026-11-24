"""Kiểm thử đơn vị cho hàm thuần `select_today_lesson` (MT02: AT12, AT39, AT40, AT48–AT50, AT53).

- Không kết nối CSDL, không gọi mạng AI.
- Chứng minh 4 Học viên mẫu A, B, C, D cùng mở HSK 2 nhưng nhận đề xuất bài & lý do khác nhau khớp dữ liệu riêng.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.practice.services.recommendation_rules import select_today_lesson


def _sample_candidates() -> list[dict]:
    return [
        {
            "ma_goc_id": 101,
            "loai": "bai",
            "trang_thai_dang": "da_dang",
            "ten": "Hẹn giờ và lịch trình",
            "ky_nang": "nghe",
            "cap_do_id": 2,
            "ten_cap": "HSK 2",
            "cap_thu_tu": 2,
            "ten_thua": "Thửa 1",
            "so_thua": 1,
            "vi_tri": 1,
            "so_cau": 5,
            "trang_thai": "chua_hoc",
            "luot_dang_lam": None,
            "nhom_cau_count": {3: 4},  # thoi_gian_lich_hen = 3
            "so_cau_den_han": 0,
            "so_ngay_tu_lan_dat": None,
        },
        {
            "ma_goc_id": 102,
            "loai": "bai",
            "trang_thai_dang": "da_dang",
            "ten": "Trợ từ 了 và 过 trong câu",
            "ky_nang": "doc",
            "cap_do_id": 2,
            "ten_cap": "HSK 2",
            "cap_thu_tu": 2,
            "ten_thua": "Thửa 1",
            "so_thua": 1,
            "vi_tri": 2,
            "so_cau": 5,
            "trang_thai": "chua_hoc",
            "luot_dang_lam": None,
            "nhom_cau_count": {7: 3},  # tro_tu_dong_thai = 7
            "so_cau_den_han": 0,
            "so_ngay_tu_lan_dat": None,
        },
        {
            "ma_goc_id": 103,
            "loai": "bai",
            "trang_thai_dang": "da_dang",
            "ten": "Chào hỏi cơ bản",
            "ky_nang": "tu_vung",
            "cap_do_id": 1,
            "ten_cap": "HSK 1",
            "cap_thu_tu": 1,
            "ten_thua": "Thửa 1",
            "so_thua": 1,
            "vi_tri": 1,
            "so_cau": 5,
            "trang_thai": "chua_hoc",
            "luot_dang_lam": None,
            "nhom_cau_count": {1: 5},
            "so_cau_den_han": 0,
            "so_ngay_tu_lan_dat": None,
        },
        # AT53: Bài bị khóa và bài nháp -> tuyệt đối không bao giờ được chọn
        {
            "ma_goc_id": 999,
            "loai": "bai",
            "trang_thai_dang": "da_dang",
            "ten": "Bài nâng cao đang khóa",
            "ky_nang": "nghe",
            "cap_do_id": 3,
            "ten_cap": "HSK 3",
            "cap_thu_tu": 3,
            "ten_thua": "Thửa 5",
            "so_thua": 5,
            "vi_tri": 1,
            "so_cau": 5,
            "trang_thai": "khoa",
            "nhom_cau_count": {3: 10},
        },
        {
            "ma_goc_id": 998,
            "loai": "bai",
            "trang_thai_dang": "nhap",
            "ten": "Bài nháp chưa xuất bản",
            "ky_nang": "doc",
            "cap_do_id": 2,
            "ten_cap": "HSK 2",
            "cap_thu_tu": 2,
            "ten_thua": "Thửa 1",
            "so_thua": 1,
            "vi_tri": 3,
            "so_cau": 5,
            "trang_thai": "chua_hoc",
            "nhom_cau_count": {7: 10},
        },
    ]


class TodayRecommendationUnitTests(unittest.TestCase):
    def test_four_personas_personalization_at12_at48(self):
        candidates = _sample_candidates()

        # Học viên A: Sai 3/4 câu Nghe nhóm Thời gian & lịch hẹn (id=3)
        profile_a = [{
            "ky_nang": "nghe",
            "nhom_kien_thuc_id": 3,
            "ten_nhom": "Thời gian & Lịch hẹn",
            "cap_nhom_thu_tu": 2,
            "tong": 4,
            "tu_lam_dung": 1,
            "dung_nho_ho_tro": 0,
            "lam_sai": 3,
            "bo_qua": 0,
            "sai_gan_day": 3,
            "tu_dung_3_gan_nhat_ty_le": 0.333,
        }]
        rec_a = select_today_lesson(profile_a, target_level_order=2, candidate_lessons=candidates, total_valid_answers=8)
        self.assertEqual(rec_a["ma_goc_id"], 101)
        self.assertEqual(rec_a["uu_tien"], 1)
        self.assertIn("3/4", rec_a["ly_do"])

        # Học viên B: Nghe tốt, nhưng sai lặp lại nhóm Trợ từ động thái 了 / 过 (id=7) ở Đọc
        profile_b = [
            {
                "ky_nang": "nghe",
                "nhom_kien_thuc_id": 3,
                "ten_nhom": "Thời gian & Lịch hẹn",
                "cap_nhom_thu_tu": 2,
                "tong": 4,
                "tu_lam_dung": 4,
                "dung_nho_ho_tro": 0,
                "lam_sai": 0,
                "bo_qua": 0,
                "sai_gan_day": 0,
                "tu_dung_3_gan_nhat_ty_le": 1.0,
            },
            {
                "ky_nang": "doc",
                "nhom_kien_thuc_id": 7,
                "ten_nhom": "Trợ từ động thái (了 / 过)",
                "cap_nhom_thu_tu": 2,
                "tong": 5,
                "tu_lam_dung": 2,
                "dung_nho_ho_tro": 1,
                "lam_sai": 2,
                "bo_qua": 0,
                "sai_gan_day": 2,
                "tu_dung_3_gan_nhat_ty_le": 0.333,
            },
        ]
        rec_b = select_today_lesson(profile_b, target_level_order=2, candidate_lessons=candidates, total_valid_answers=9)
        self.assertEqual(rec_b["ma_goc_id"], 102)
        self.assertEqual(rec_b["uu_tien"], 1)
        self.assertNotEqual(rec_a["ma_goc_id"], rec_b["ma_goc_id"])

        # Học viên C: Làm đúng 100% nhưng 3/4 câu ở nhóm 7 phải mở gợi ý / Hỏi Xiang -> Ưu tiên 3
        profile_c = [{
            "ky_nang": "doc",
            "nhom_kien_thuc_id": 7,
            "ten_nhom": "Trợ từ động thái (了 / 过)",
            "cap_nhom_thu_tu": 2,
            "tong": 4,
            "tu_lam_dung": 1,
            "dung_nho_ho_tro": 3,
            "lam_sai": 0,
            "bo_qua": 0,
            "sai_gan_day": 0,
            "tu_dung_3_gan_nhat_ty_le": 0.333,
        }]
        rec_c = select_today_lesson(profile_c, target_level_order=2, candidate_lessons=candidates, total_valid_answers=6)
        self.assertEqual(rec_c["ma_goc_id"], 102)
        self.assertEqual(rec_c["uu_tien"], 3)
        self.assertIn("3/4", rec_c["ly_do"])

        # Học viên D: Chưa có dữ liệu lịch sử câu trả lời & chưa chọn mục tiêu -> Ưu tiên 5 + ghi chú rõ giới hạn (AT40)
        rec_d = select_today_lesson([], target_level_order=None, candidate_lessons=candidates, total_valid_answers=0)
        self.assertEqual(rec_d["uu_tien"], 5)
        self.assertEqual(rec_d["ma_goc_id"], 103)
        self.assertIsNotNone(rec_d["ghi_chu_du_lieu"])

    def test_single_mistake_does_not_trigger_weak_group_at39(self):
        candidates = _sample_candidates()
        single_err_profile = [{
            "ky_nang": "doc",
            "nhom_kien_thuc_id": 7,
            "ten_nhom": "Trợ từ động thái (了 / 过)",
            "cap_nhom_thu_tu": 2,
            "tong": 3,
            "tu_lam_dung": 2,
            "dung_nho_ho_tro": 0,
            "lam_sai": 1,
            "bo_qua": 0,
            "sai_gan_day": 1,
            "tu_dung_3_gan_nhat_ty_le": 0.667,
        }]
        rec = select_today_lesson(single_err_profile, target_level_order=2, candidate_lessons=candidates, total_valid_answers=5)
        # Chỉ sai 1 câu đơn lẻ -> rơi thẳng về Ưu tiên 5 (bài mới theo lộ trình), không báo lỗi nhóm kiến thức
        self.assertEqual(rec["uu_tien"], 5)

    def test_locked_and_draft_lessons_excluded_at53(self):
        locked_only = [c for c in _sample_candidates() if c["ma_goc_id"] in (998, 999)]
        self.assertIsNone(select_today_lesson([], target_level_order=3, candidate_lessons=locked_only, total_valid_answers=10))


if __name__ == "__main__":
    unittest.main()
