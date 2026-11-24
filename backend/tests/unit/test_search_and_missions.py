"""Kiểm thử đơn vị cho Tra từ Hán tự ghép cụm, kiểm duyệt văn bản phát âm TTS và mục tiêu động Nhiệm vụ ngày."""
from pathlib import Path
import sys
import unittest

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.modules.mistake_notebook.services.missions import _effective_target
from app.modules.search.services.pronounce_service import clean_pronounce_text
from app.modules.search.services.search_service import _score_han


class SearchAndMissionsUnitTest(unittest.TestCase):
    def test_score_han_matches_exact_prefix_and_compound_phrase(self):
        word = {"chu_han": "你好"}
        self.assertEqual(_score_han(word, "你好"), 100)
        self.assertEqual(_score_han(word, "你"), 85)
        # Khi người học gõ cả câu chào "你好吗", từ mục "你好" vẫn được tìm thấy hợp lý
        self.assertGreaterEqual(_score_han(word, "你好吗"), 60)
        self.assertEqual(_score_han(word, "谢谢"), 0)

    def test_clean_pronounce_text_validates_chinese_and_length(self):
        self.assertEqual(clean_pronounce_text("  你好，很高兴认识你！\n "), "你好，很高兴认识你！")
        with self.assertRaises(HTTPException):
            clean_pronounce_text("hello world")
        with self.assertRaises(HTTPException):
            clean_pronounce_text("   ")
        with self.assertRaises(HTTPException):
            clean_pronounce_text("好" * 81)

    def test_effective_target_adapts_notebook_mission_for_new_learners(self):
        spec_nb = {"ma": "nv_so_tay", "ten": "Ôn 5 câu trong Sổ tay", "can": 5}
        self.assertEqual(_effective_target(spec_nb, notebook_count=0, done_raw=0), (5, "Ôn 5 câu trong Sổ tay"))
        self.assertEqual(_effective_target(spec_nb, notebook_count=2, done_raw=0), (2, "Ôn hết 2 câu trong Sổ tay"))
        self.assertEqual(_effective_target(spec_nb, notebook_count=1, done_raw=3), (3, "Ôn hết 3 câu trong Sổ tay"))
        self.assertEqual(_effective_target(spec_nb, notebook_count=9, done_raw=0), (5, "Ôn 5 câu trong Sổ tay"))

        spec_lesson = {"ma": "nv_on_luyen", "ten": "Hoàn thành 1 bài Ôn luyện", "can": 1}
        self.assertEqual(_effective_target(spec_lesson, notebook_count=2, done_raw=0), (1, "Hoàn thành 1 bài Ôn luyện"))


if __name__ == "__main__":
    unittest.main()
