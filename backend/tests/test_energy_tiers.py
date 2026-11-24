"""Kiểm thử hệ thống Năng lượng mở rộng theo Trình độ HSK (5 -> 6 -> 8 -> 10) và đối soát v_doi_soat_nang_luong."""
import unittest

from sqlalchemy import text

from app.database.session import engine
from app.modules.practice.services import path_view
from sqlalchemy.orm import Session


class TestEnergyTiers(unittest.TestCase):
    def test_max_energy_by_hsk_order(self):
        self.assertEqual(path_view.max_energy_for_order(1), 5)
        self.assertEqual(path_view.max_energy_for_order(2), 6)
        self.assertEqual(path_view.max_energy_for_order(3), 8)
        self.assertEqual(path_view.max_energy_for_order(4), 10)
        self.assertEqual(path_view.max_energy_for_order(None), 5)

    def test_sync_energy_level_up_and_daily_refill_keep_ledger_balanced(self):
        """Mở giao dịch thử nghiệm rồi rollback hoàn toàn để chứng minh v_doi_soat_nang_luong luôn khớp 100%."""
        conn = engine.connect()
        trans = conn.begin()
        db = Session(bind=conn)
        try:
            res = db.execute(
                text("""INSERT INTO nguoi_dung (vai_tro_id, email, ho_ten, mat_khau_bam, trang_thai, nang_luong)
                        VALUES (1, 'test_energy_tier_tmp@example.com', 'Test Tier', 'hash', 'hoat_dong', 5)""")
            )
            uid = int(res.lastrowid)
            db.execute(
                text("INSERT INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong) VALUES (:u, 'khoi_tao', 5)"),
                {"u": uid},
            )

            # 1) Thăng cấp lên HSK 3 (trần 8): năng lượng tự cộng +3 từ 5 -> 8
            cur, max_e = path_view.sync_user_energy(db, uid, max_e=8, auto_commit=False)
            self.assertEqual((cur, max_e), (8, 8))

            # 2) Thăng tiếp lên HSK 4 (trần 10): năng lượng tự cộng +2 từ 8 -> 10
            cur, max_e = path_view.sync_user_energy(db, uid, max_e=10, auto_commit=False)
            self.assertEqual((cur, max_e), (10, 10))

            # Gọi lặp lại phải idempotent (không cộng thừa)
            cur, max_e = path_view.sync_user_energy(db, uid, max_e=10, auto_commit=False)
            self.assertEqual((cur, max_e), (10, 10))

            # Kiểm tra bảng đối soát v_doi_soat_nang_luong = 0 lệch
            row = db.execute(
                text("SELECT so_du_luu, so_du_tinh FROM v_doi_soat_nang_luong WHERE nguoi_dung_id = :u"),
                {"u": uid},
            ).mappings().one()
            self.assertEqual(int(row["so_du_luu"]), 10)
            self.assertEqual(int(row["so_du_tinh"]), 10)
        finally:
            db.close()
            trans.rollback()
            conn.close()


if __name__ == "__main__":
    unittest.main()
