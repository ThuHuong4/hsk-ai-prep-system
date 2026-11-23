-- =====================================================================
-- Script HOAN TAC (ROLLBACK) NANG CAP CSDL Xianglingo
--   Dua CSDL tu 24 bang + 4 View + 2 Trigger ve lai dung 19 bang goc + 2 View goc.
--
-- Luu y an toan:
--   - KHONG ghi cung USE xianglingo; -> phai chi dinh ten CSDL khi chay lenh:
--       mysql -u root -p ten_csdl < backend/scripts/2026_11_23_hoan_tac_nang_cap.sql
--   - Neu CSDL da phat sinh du lieu thuoc nghiep vu moi (cau hoi 'dich_cau',
--     goi y lo trinh 'dich_cau', ket qua dau vao, lich su thay cau), script se
--     dung ngay va bao loi ro rang thay vi am tham xoa mat du lieu.
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '+07:00';

DROP PROCEDURE IF EXISTS _kiem_tra_an_toan_hoan_tac;

DELIMITER $$

CREATE PROCEDURE _kiem_tra_an_toan_hoan_tac()
BEGIN
  IF EXISTS (SELECT 1 FROM cau_hoi WHERE dang = 'dich_cau' LIMIT 1) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the hoan tac tu dong: da co cau_hoi dang dich_cau.';
  END IF;
  IF EXISTS (SELECT 1 FROM goi_y_lo_trinh WHERE dang_cau = 'dich_cau' LIMIT 1) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the hoan tac tu dong: da co goi_y_lo_trinh dang dich_cau.';
  END IF;
  IF EXISTS (SELECT 1 FROM luot_lam WHERE loai_boc_cau = 'danh_gia_dau_vao' AND cap_do_id IS NULL LIMIT 1) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the hoan tac tu dong: da co luot danh_gia_dau_vao moi (cap_do_id IS NULL).';
  END IF;
  IF EXISTS (SELECT 1 FROM ket_qua_dau_vao LIMIT 1)
     OR EXISTS (SELECT 1 FROM nhan_dinh_dau_vao LIMIT 1)
     OR EXISTS (SELECT 1 FROM lich_su_thay_cau LIMIT 1) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the hoan tac tu dong: cac bang ket_qua_dau_vao / nhan_dinh_dau_vao / lich_su_thay_cau da co du lieu.';
  END IF;
END$$

DELIMITER ;

CALL _kiem_tra_an_toan_hoan_tac();
DROP PROCEDURE _kiem_tra_an_toan_hoan_tac;

-- 1. Go Trigger va 2 View moi
DROP TRIGGER IF EXISTS trg_cau_hoi_bi_audio;
DROP TRIGGER IF EXISTS trg_cau_hoi_bu_audio;
DROP VIEW IF EXISTS v_bai_on;
DROP VIEW IF EXISTS v_cau_hoi;

-- 2. Hoan tac hoi_thoai
ALTER TABLE hoi_thoai
  ADD KEY ix_hoi_thoai_ctl (cau_tra_loi_id);
ALTER TABLE hoi_thoai
  DROP INDEX uq_hoi_thoai_ctl;

-- 3. Hoan tac goi_y_lo_trinh
ALTER TABLE goi_y_lo_trinh
  DROP FOREIGN KEY fk_goi_y_nhom,
  MODIFY dang_cau ENUM('chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo') NULL,
  DROP COLUMN nhom_kien_thuc_id;

-- 4. Hoan tac nhat_ky_thuong
ALTER TABLE nhat_ky_thuong
  DROP FOREIGN KEY fk_nkt_luot,
  DROP INDEX ix_nkt_luot,
  DROP COLUMN luot_lam_id;

-- 5. Xoa 4 bang phu thuoc cau_tra_loi / luot_lam / nhom_kien_thuc truoc khi go cot va bang nhom_kien_thuc
DROP TABLE IF EXISTS lich_su_thay_cau;
DROP TABLE IF EXISTS nhan_dinh_bang_chung;
DROP TABLE IF EXISTS nhan_dinh_dau_vao;
DROP TABLE IF EXISTS ket_qua_dau_vao;

-- 6. Hoan tac ket_qua_cham va tao lai v_ket_qua_hien_hanh dung 12 cot goc
ALTER TABLE ket_qua_cham
  DROP COLUMN phien_ban_luu;

CREATE OR REPLACE VIEW v_ket_qua_hien_hanh AS
SELECT k.id,
       k.cau_tra_loi_id,
       k.lan,
       k.nguon,
       k.trang_thai,
       k.diem,
       k.nhan_xet,
       k.cau_sua,
       k.ly_do_sua,
       k.nguoi_cham_id,
       k.mo_hinh,
       k.tao_luc
FROM ket_qua_cham k
JOIN (SELECT cau_tra_loi_id, MAX(lan) AS lan
      FROM ket_qua_cham
      WHERE trang_thai = 'hoan_tat'
      GROUP BY cau_tra_loi_id) m
  ON m.cau_tra_loi_id = k.cau_tra_loi_id AND m.lan = k.lan;

-- 7. Hoan tac cau_tra_loi
ALTER TABLE cau_tra_loi
  DROP FOREIGN KEY fk_ctl_cap_tham_do,
  DROP CHECK ck_ctl_muc_goi_y,
  DROP CHECK ck_ctl_thao_tac,
  DROP COLUMN xem_loi_giai_luc,
  DROP COLUMN thoi_gian_lam_giay,
  DROP COLUMN muc_goi_y,
  DROP COLUMN trang_thai_thao_tac,
  DROP COLUMN cap_tham_do_id;

-- 8. Hoan tac luot_lam
ALTER TABLE luot_lam DROP CHECK ck_luot_lam_pham_vi;
ALTER TABLE luot_lam
  ADD CONSTRAINT ck_luot_lam_pham_vi CHECK (
    (COALESCE(loai_boc_cau, '') IN ('bat_dau_cap','vuot_chang','danh_gia_dau_vao','on_ho_tro')
       AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (COALESCE(loai_boc_cau, '') NOT IN ('bat_dau_cap','vuot_chang','danh_gia_dau_vao','on_ho_tro')
       AND cap_do_id IS NULL AND ky_nang IS NULL));

-- 9. Hoan tac cau_hoi (go 2 CHECK cung ten bang lenh rieng truoc)
ALTER TABLE cau_hoi DROP CHECK ck_cau_hoi_ngu_lieu;
ALTER TABLE cau_hoi DROP CHECK ck_cau_hoi_diem;
ALTER TABLE cau_hoi
  DROP FOREIGN KEY fk_cau_hoi_nhom,
  DROP FOREIGN KEY fk_cau_hoi_nguoi_duyet,
  DROP INDEX ix_cau_hoi_nhom,
  DROP CHECK ck_cau_hoi_audio_duyet,
  DROP CHECK ck_cau_hoi_duyet,
  MODIFY dang ENUM('ngu_lieu','chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo') NOT NULL,
  DROP COLUMN duyet_luc,
  DROP COLUMN nguoi_duyet_id,
  DROP COLUMN nguon_noi_dung,
  DROP COLUMN goi_y_2,
  DROP COLUMN da_kiem_tra_audio,
  DROP COLUMN nhom_kien_thuc_id,
  ADD CONSTRAINT ck_cau_hoi_ngu_lieu CHECK (dang <> 'ngu_lieu' OR cau_cha_id IS NULL),
  ADD CONSTRAINT ck_cau_hoi_diem CHECK (
    (dang = 'viet_mo' AND diem_toi_da IS NOT NULL AND nguong_dat IS NOT NULL
       AND diem_toi_da > 0 AND nguong_dat > 0 AND nguong_dat <= diem_toi_da)
    OR (dang <> 'viet_mo' AND diem_toi_da IS NULL AND nguong_dat IS NULL));

-- 10. Xoa bang nhom_kien_thuc cuoi cung
DROP TABLE IF EXISTS nhom_kien_thuc;
