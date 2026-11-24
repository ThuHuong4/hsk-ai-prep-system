-- =====================================================================
-- 2026-11-24: NANG CAP TRAN NANG LUONG THEO TRINH DO HSK (5 -> 6 -> 8 -> 10)
--   1. Mo rong rang buoc ck_nguoi_dung_nang_luong len 0..10.
--   2. Bo sung cac ly_do hoi nang luong vao nhat_ky_thuong:
--      - hoi_ngay: tu hoi day binh nang luong vao dau ngay moi (1 lan/ngay).
--      - thang_cap_nl: cong phan mo rong binh nang luong khi thang cap HSK.
--      - hoi_so_tay: hoi +1 nang luong khi hoan thanh luot On So tay dat >= 80%.
--      - thuong_cuoi_thua: thuong +1 nang luong khi vuot Kiem tra cuoi thua 10/10.
--   3. Cap nhat v_doi_soat_nang_luong de giu can bang tuyet doi so_du_luu = so_du_tinh.
-- =====================================================================

-- 1. Cap nhat rang buoc nang_luong tren bang nguoi_dung (0..10)
SET @has_ck := (
    SELECT COUNT(*)
    FROM information_schema.table_constraints
    WHERE table_schema = DATABASE()
      AND table_name = 'nguoi_dung'
      AND constraint_name = 'ck_nguoi_dung_nang_luong'
);
SET @sql_drop_ck := IF(@has_ck > 0, 'ALTER TABLE nguoi_dung DROP CHECK ck_nguoi_dung_nang_luong', 'SELECT 1');
PREPARE stmt FROM @sql_drop_ck;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE nguoi_dung
  ADD CONSTRAINT ck_nguoi_dung_nang_luong CHECK (nang_luong BETWEEN 0 AND 10);

-- 2. Mo rong ENUM ly_do va chi muc chong trung tren bang nhat_ky_thuong
ALTER TABLE nhat_ky_thuong
  MODIFY COLUMN ly_do ENUM(
    'khoi_tao',
    'nv_so_tay',
    'nv_on_luyen',
    'nv_thi_thu',
    'hoi_ngay',
    'thang_cap_nl',
    'hoi_so_tay',
    'thuong_cuoi_thua',
    'kn_bai',
    'kn_cuoi_thua',
    'kn_vuot_thua',
    'kn_bat_dau_cap',
    'kn_vuot_chang',
    'kn_cung_co'
  ) NOT NULL;

SET @has_uq_ngay := (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'nhat_ky_thuong'
      AND index_name = 'uq_nkt_nhiem_vu_ngay'
);
SET @sql_drop_uq_ngay := IF(@has_uq_ngay > 0, 'DROP INDEX uq_nkt_nhiem_vu_ngay ON nhat_ky_thuong', 'SELECT 1');
PREPARE stmt2 FROM @sql_drop_uq_ngay;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;

CREATE UNIQUE INDEX uq_nkt_nhiem_vu_ngay
  ON nhat_ky_thuong (
    nguoi_dung_id,
    ly_do,
    ((CASE WHEN ly_do IN ('nv_so_tay','nv_on_luyen','nv_thi_thu','hoi_ngay') THEN DATE(tao_luc) END))
  );

SET @has_uq_luot := (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'nhat_ky_thuong'
      AND index_name = 'uq_nkt_hoi_luot'
);
SET @sql_drop_uq_luot := IF(@has_uq_luot > 0, 'DROP INDEX uq_nkt_hoi_luot ON nhat_ky_thuong', 'SELECT 1');
PREPARE stmt3 FROM @sql_drop_uq_luot;
EXECUTE stmt3;
DEALLOCATE PREPARE stmt3;

CREATE UNIQUE INDEX uq_nkt_hoi_luot
  ON nhat_ky_thuong (
    nguoi_dung_id,
    ly_do,
    ((CASE WHEN ly_do IN ('hoi_so_tay','thuong_cuoi_thua') THEN luot_lam_id END))
  );

-- 3. Cap nhat view doi soat nang luong
CREATE OR REPLACE VIEW v_doi_soat_nang_luong AS
SELECT n.id AS nguoi_dung_id,
       n.nang_luong AS so_du_luu,
       COALESCE(t.cong, 0) - COALESCE(c.tru, 0) + COALESCE(c.hoan, 0) AS so_du_tinh
FROM nguoi_dung n
LEFT JOIN (SELECT nguoi_dung_id, SUM(so_luong) AS cong
           FROM nhat_ky_thuong
           WHERE ly_do IN (
             'khoi_tao','nv_so_tay','nv_on_luyen','nv_thi_thu',
             'hoi_ngay','thang_cap_nl','hoi_so_tay','thuong_cuoi_thua'
           )
           GROUP BY nguoi_dung_id) t ON t.nguoi_dung_id = n.id
LEFT JOIN (SELECT l.nguoi_dung_id,
                  SUM(a.nang_luong_tru) AS tru,
                  SUM(a.nang_luong_hoan) AS hoan
           FROM cau_tra_loi a
           JOIN luot_lam l ON l.id = a.luot_lam_id
           GROUP BY l.nguoi_dung_id) c ON c.nguoi_dung_id = n.id;
