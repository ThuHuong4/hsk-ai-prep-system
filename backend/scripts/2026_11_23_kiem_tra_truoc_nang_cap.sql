-- =====================================================================
-- Script KIEM TRA TRUOC NANG CAP CSDL Xianglingo (Chi doc - Read-only)
-- Cach chay:
--   mysql -u root -p ten_csdl < backend/scripts/2026_11_23_kiem_tra_truoc_nang_cap.sql
-- =====================================================================

SET NAMES utf8mb4;

-- 1. Kiem tra phien ban MySQL (can >= 8.0.16) va ten CSDL dang chon
SELECT VERSION() AS phien_ban_mysql, DATABASE() AS csdl_hien_tai;

-- 2. Kiem tra so bang hien co trong CSDL (ban goc truoc nang cap co 19 bang)
SELECT COUNT(*) AS so_bang_vat_ly
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE';

-- 3. Kiem tra xem 5 bang moi da ton tai chua (tat ca phai = 0 truoc khi nang cap)
SELECT table_name AS bang_moi_da_ton_tai
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('nhom_kien_thuc','ket_qua_dau_vao','nhan_dinh_dau_vao','nhan_dinh_bang_chung','lich_su_thay_cau');

-- 4. Kiem tra xem cot moi tren cau_hoi / cau_tra_loi / ket_qua_cham da ton tai chua (phai rong truoc khi nang cap)
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND ((table_name = 'cau_hoi' AND column_name IN ('nhom_kien_thuc_id','da_kiem_tra_audio','goi_y_2','nguon_noi_dung','nguoi_duyet_id','duyet_luc'))
    OR (table_name = 'cau_tra_loi' AND column_name IN ('cap_tham_do_id','trang_thai_thao_tac','muc_goi_y','thoi_gian_lam_giay','xem_loi_giai_luc'))
    OR (table_name = 'ket_qua_cham' AND column_name = 'phien_ban_luu')
    OR (table_name = 'nhat_ky_thuong' AND column_name = 'luot_lam_id')
    OR (table_name = 'goi_y_lo_trinh' AND column_name = 'nhom_kien_thuc_id'));

-- 5. Kiem tra hoi_thoai co dong nao trung cau_tra_loi_id khong (neu > 0 thi uq_hoi_thoai_ctl se bao loi)
SELECT cau_tra_loi_id, COUNT(*) AS so_dong_trung
FROM hoi_thoai
WHERE cau_tra_loi_id IS NOT NULL
GROUP BY cau_tra_loi_id
HAVING COUNT(*) > 1;

-- 6. Kiem tra cau_hoi co dong nao vi pham rang buoc diem_toi_da / nguong_dat khong (phai = 0)
SELECT COUNT(*) AS so_cau_sai_rang_buoc_diem
FROM cau_hoi
WHERE NOT (
  (dang = 'viet_mo' AND diem_toi_da IS NOT NULL AND nguong_dat IS NOT NULL
     AND diem_toi_da > 0 AND nguong_dat > 0 AND nguong_dat <= diem_toi_da)
  OR (dang <> 'viet_mo' AND diem_toi_da IS NULL AND nguong_dat IS NULL)
);

-- 7. Thong ke nhanh so dong cac bang chinh truoc khi nang cap de doi chieu sau khi chay
SELECT 'nguoi_dung' AS bang, COUNT(*) AS so_dong FROM nguoi_dung
UNION ALL SELECT 'cau_hoi', COUNT(*) FROM cau_hoi
UNION ALL SELECT 'bo_de', COUNT(*) FROM bo_de
UNION ALL SELECT 'luot_lam', COUNT(*) FROM luot_lam
UNION ALL SELECT 'cau_tra_loi', COUNT(*) FROM cau_tra_loi
UNION ALL SELECT 'ket_qua_cham', COUNT(*) FROM ket_qua_cham;

-- ---------------------------------------------------------------------
-- Bo sung 2 phep dem: ca hai PHAI = 0, khac 0 thi DUNG LAI va bao lai
-- ---------------------------------------------------------------------
-- Luot danh_gia_dau_vao cu se vi pham rang buoc moi cua luot_lam
SELECT COUNT(*) AS luot_danh_gia_dau_vao_cu
FROM luot_lam WHERE loai_boc_cau = 'danh_gia_dau_vao';

-- Gia tri hanh_dong ngoai danh sach se lam lenh MODIFY nhat_ky_quan_tri loi
SELECT COUNT(*) AS hanh_dong_ngoai_danh_sach
FROM nhat_ky_quan_tri
WHERE hanh_dong NOT IN ('khoa','mo_khoa','doi_vai_tro','tao_tai_khoan');

-- Chi de biet (khong can = 0): cau da xac nhan nhung van_ban la chuoi rong;
-- script nang cap se de cac dong nay o 'chua_thao_tac'
SELECT COUNT(*) AS van_ban_chuoi_rong
FROM cau_tra_loi
WHERE van_ban IS NOT NULL AND TRIM(van_ban) = '';
