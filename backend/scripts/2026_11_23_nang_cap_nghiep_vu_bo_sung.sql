-- =====================================================================
-- Script NANG CAP CAU TRUC CSDL Xianglingo (DDL + dong bo cot moi)
--   Tu 19 bang goc -> 24 bang + 4 View + 2 Trigger kiem soat da_kiem_tra_audio.
--
-- Nguyen tac an toan:
--   1. KHONG ghi cung USE xianglingo; -> phai chi dinh ten CSDL khi chay lenh
--      de thu nghiem tren ban sao truoc khi chay vao CSDL that.
--   2. KHONG sua du lieu nghiep vu cu ngoai pham vi cot moi (khong chen nhat_ky_thuong,
--      khong doi co dung_on_luyen, khong tu gan nguon 'tu_soan' cho cau hoi cu).
--
-- Quy trinh khuyen nghi:
--   Buoc 1: Tao ban sao thu nghiem va kiem tra truoc:
--     mysqldump -u root -p xianglingo > xianglingo_truoc_nang_cap.sql
--     mysql -u root -p -e "CREATE DATABASE xianglingo_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
--     mysql -u root -p xianglingo_test < xianglingo_truoc_nang_cap.sql
--     mysql -u root -p xianglingo_test < backend/scripts/2026_11_23_kiem_tra_truoc_nang_cap.sql
--   Buoc 2: Chay nang cap tren ban thu nghiem truoc, kiem tra xong moi chay tren xianglingo:
--     mysql -u root -p xianglingo_test < backend/scripts/2026_11_23_nang_cap_nghiep_vu_bo_sung.sql
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '+07:00';

-- ---------------------------------------------------------------------
-- 1. Dong bo ENUM nhat_ky_quan_tri (an toan idempotent neu da chay script 2026_11_18)
-- ---------------------------------------------------------------------
ALTER TABLE nhat_ky_quan_tri
  MODIFY hanh_dong ENUM('khoa','mo_khoa','doi_vai_tro','tao_tai_khoan') NOT NULL;

-- ---------------------------------------------------------------------
-- 2. Tao 5 bang moi (tat ca deu dat BCNF)
-- ---------------------------------------------------------------------

-- Bang moi #1: nhom_kien_thuc
CREATE TABLE nhom_kien_thuc (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma            VARCHAR(50)  NOT NULL,
  ten           VARCHAR(100) NOT NULL,
  mo_ta         TEXT NULL,
  trang_thai    ENUM('hoat_dong','da_an') NOT NULL DEFAULT 'hoat_dong',
  nguoi_tao_id  BIGINT UNSIGNED NULL,
  tao_luc       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_nhom_kien_thuc_ma (ma),
  CONSTRAINT fk_nkt_dm_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bang moi #2: ket_qua_dau_vao
CREATE TABLE ket_qua_dau_vao (
  luot_lam_id             BIGINT UNSIGNED NOT NULL,
  trang_thai_phan_tich    ENUM('chua','dang','xong','loi') NOT NULL DEFAULT 'chua',
  bat_dau_phan_tich_luc   DATETIME NULL,
  hoan_tat_phan_tich_luc  DATETIME NULL,
  cap_de_xuat_id          INT UNSIGNED NULL,
  ghi_chu_gioi_han        TEXT NULL,
  PRIMARY KEY (luot_lam_id),
  CONSTRAINT fk_kqdv_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  CONSTRAINT fk_kqdv_cap_de_xuat FOREIGN KEY (cap_de_xuat_id) REFERENCES cap_do (id),
  CONSTRAINT ck_kqdv_thoi_gian CHECK (
    hoan_tat_phan_tich_luc IS NULL OR bat_dau_phan_tich_luc IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bang moi #3: nhan_dinh_dau_vao (ky_nang cho phep NULL de luu nhan xet chung)
CREATE TABLE nhan_dinh_dau_vao (
  luot_lam_id        BIGINT UNSIGNED NOT NULL,
  thu_tu             TINYINT UNSIGNED NOT NULL,
  ky_nang            ENUM('nghe','doc','viet','tu_vung') NULL DEFAULT NULL,
  nhom_kien_thuc_id  INT UNSIGNED NULL,
  loai               ENUM('diem_manh','diem_yeu','nhan_xet') NOT NULL,
  noi_dung           TEXT NOT NULL,
  PRIMARY KEY (luot_lam_id, thu_tu),
  CONSTRAINT fk_nddv_kqdv FOREIGN KEY (luot_lam_id) REFERENCES ket_qua_dau_vao (luot_lam_id),
  CONSTRAINT fk_nddv_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id),
  CONSTRAINT ck_nddv_thu_tu CHECK (thu_tu >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bang moi #4: nhan_dinh_bang_chung (khoa ngoai kep bao dam bang chung thuoc dung luot)
CREATE TABLE nhan_dinh_bang_chung (
  luot_lam_id       BIGINT UNSIGNED NOT NULL,
  thu_tu_nhan_dinh  TINYINT UNSIGNED NOT NULL,
  thu_tu_cau        SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (luot_lam_id, thu_tu_nhan_dinh, thu_tu_cau),
  CONSTRAINT fk_ndbc_nhan_dinh FOREIGN KEY (luot_lam_id, thu_tu_nhan_dinh)
    REFERENCES nhan_dinh_dau_vao (luot_lam_id, thu_tu),
  CONSTRAINT fk_ndbc_cau_tra_loi FOREIGN KEY (luot_lam_id, thu_tu_cau)
    REFERENCES cau_tra_loi (luot_lam_id, thu_tu)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Bang moi #5: lich_su_thay_cau (ly_do dung ENUM thong nhat)
CREATE TABLE lich_su_thay_cau (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  luot_lam_id     BIGINT UNSIGNED NOT NULL,
  thu_tu_vi_tri   SMALLINT UNSIGNED NOT NULL,
  cau_hoi_cu_id   BIGINT UNSIGNED NOT NULL,
  cau_hoi_moi_id  BIGINT UNSIGNED NOT NULL,
  ly_do           ENUM('loi_audio','loi_hinh_anh','loi_hien_thi','loi_noi_dung') NOT NULL DEFAULT 'loi_audio',
  tao_luc         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_lstc_luot (luot_lam_id, thu_tu_vi_tri),
  CONSTRAINT fk_lstc_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  CONSTRAINT fk_lstc_cau_cu FOREIGN KEY (cau_hoi_cu_id) REFERENCES cau_hoi (id),
  CONSTRAINT fk_lstc_cau_moi FOREIGN KEY (cau_hoi_moi_id) REFERENCES cau_hoi (id),
  CONSTRAINT ck_lstc_khac_cau CHECK (cau_hoi_cu_id <> cau_hoi_moi_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------
-- 3. Mo rong cac bang hien co (giu nguyen du lieu cu)
-- ---------------------------------------------------------------------

-- 3.1 cau_hoi: nguon_noi_dung de NULL DEFAULT NULL de khong gan sai nguon cho cau/de cu (vd de mau Hanban)
-- Go 2 CHECK cu bang lenh rieng truoc (tranh bao trung ten khi tao lai cung lenh)
ALTER TABLE cau_hoi DROP CHECK ck_cau_hoi_ngu_lieu;
ALTER TABLE cau_hoi DROP CHECK ck_cau_hoi_diem;
ALTER TABLE cau_hoi
  MODIFY dang ENUM('ngu_lieu','chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo','dich_cau') NOT NULL,
  ADD COLUMN nhom_kien_thuc_id INT UNSIGNED NULL AFTER ky_nang,
  ADD COLUMN da_kiem_tra_audio BOOLEAN NOT NULL DEFAULT 0 AFTER tep_audio,
  ADD COLUMN goi_y_2 TEXT NULL AFTER goi_y,
  ADD COLUMN nguon_noi_dung ENUM('tu_soan','soan_voi_ai','nguon_duoc_phep') NULL DEFAULT NULL AFTER tu_vung_id,
  ADD COLUMN nguoi_duyet_id BIGINT UNSIGNED NULL AFTER nguoi_tao_id,
  ADD COLUMN duyet_luc DATETIME NULL AFTER nguoi_duyet_id,
  ADD KEY ix_cau_hoi_nhom (nhom_kien_thuc_id, trang_thai),
  ADD CONSTRAINT fk_cau_hoi_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id),
  ADD CONSTRAINT fk_cau_hoi_nguoi_duyet FOREIGN KEY (nguoi_duyet_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT ck_cau_hoi_ngu_lieu CHECK (dang <> 'ngu_lieu' OR (cau_cha_id IS NULL AND nhom_kien_thuc_id IS NULL)),
  ADD CONSTRAINT ck_cau_hoi_diem CHECK (
    (dang IN ('viet_mo','dich_cau') AND diem_toi_da IS NOT NULL AND nguong_dat IS NOT NULL
       AND diem_toi_da > 0 AND nguong_dat > 0 AND nguong_dat <= diem_toi_da)
    OR (dang NOT IN ('viet_mo','dich_cau') AND diem_toi_da IS NULL AND nguong_dat IS NULL)),
  ADD CONSTRAINT ck_cau_hoi_audio_duyet CHECK (da_kiem_tra_audio = 0 OR tep_audio IS NOT NULL),
  ADD CONSTRAINT ck_cau_hoi_duyet CHECK (
    (nguoi_duyet_id IS NULL AND duyet_luc IS NULL)
    OR (nguoi_duyet_id IS NOT NULL AND duyet_luc IS NOT NULL));

-- 3.2 luot_lam: cho phep danh_gia_dau_vao de cap_do_id = NULL, ky_nang = NULL
ALTER TABLE luot_lam DROP CHECK ck_luot_lam_pham_vi;
ALTER TABLE luot_lam
  ADD CONSTRAINT ck_luot_lam_pham_vi CHECK (
    (COALESCE(loai_boc_cau, '') IN ('bat_dau_cap','vuot_chang','on_ho_tro')
       AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (COALESCE(loai_boc_cau, '') NOT IN ('bat_dau_cap','vuot_chang','on_ho_tro')
       AND cap_do_id IS NULL AND ky_nang IS NULL));

-- 3.3 cau_tra_loi: them 5 cot moi
ALTER TABLE cau_tra_loi
  ADD COLUMN cap_tham_do_id INT UNSIGNED NULL AFTER thu_tu,
  ADD COLUMN trang_thai_thao_tac ENUM('chua_thao_tac','da_tra_loi','bo_qua','loi_ky_thuat') NOT NULL DEFAULT 'chua_thao_tac' AFTER seed_xao,
  ADD COLUMN muc_goi_y TINYINT UNSIGNED NOT NULL DEFAULT 0 AFTER trang_thai_thao_tac,
  ADD COLUMN thoi_gian_lam_giay SMALLINT UNSIGNED NULL AFTER van_ban,
  ADD COLUMN xem_loi_giai_luc DATETIME NULL AFTER xac_nhan_luc,
  ADD CONSTRAINT fk_ctl_cap_tham_do FOREIGN KEY (cap_tham_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT ck_ctl_muc_goi_y CHECK (muc_goi_y IN (0, 1, 2)),
  ADD CONSTRAINT ck_ctl_thao_tac CHECK (
    trang_thai_thao_tac NOT IN ('bo_qua','loi_ky_thuat')
    OR (phuong_an_chon_id IS NULL AND van_ban IS NULL));

-- Gan trang_thai_thao_tac chinh xac cho du lieu cu:
-- Chi gan 'bo_qua' khi hoc vien da bam xac nhan (xac_nhan_luc IS NOT NULL) ma de trong;
-- cau de trong trong bai Thi thu (xac_nhan_luc IS NULL) giu nguyen 'chua_thao_tac'.
UPDATE cau_tra_loi
SET trang_thai_thao_tac = CASE
  WHEN phuong_an_chon_id IS NOT NULL OR (van_ban IS NOT NULL AND TRIM(van_ban) <> '') THEN 'da_tra_loi'
  -- chi gan bo_qua khi ca hai o dap an NULL (khop rang buoc ck_ctl_thao_tac)
  WHEN xac_nhan_luc IS NOT NULL AND phuong_an_chon_id IS NULL AND van_ban IS NULL THEN 'bo_qua'
  ELSE 'chua_thao_tac'
END;

-- 3.4 ket_qua_cham: luu phien_ban_luu cua cau_tra_loi tai thoi diem cham
ALTER TABLE ket_qua_cham
  ADD COLUMN phien_ban_luu INT UNSIGNED NULL AFTER trang_thai;

UPDATE ket_qua_cham k
JOIN cau_tra_loi a ON a.id = k.cau_tra_loi_id
SET k.phien_ban_luu = a.phien_ban_luu
WHERE k.phien_ban_luu IS NULL;

-- 3.5 nhat_ky_thuong: them luot_lam_id
ALTER TABLE nhat_ky_thuong
  ADD COLUMN luot_lam_id BIGINT UNSIGNED NULL AFTER nguoi_dung_id,
  ADD KEY ix_nkt_luot (luot_lam_id),
  ADD CONSTRAINT fk_nkt_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id);

-- 3.6 goi_y_lo_trinh: them nhom_kien_thuc_id va dang 'dich_cau'
ALTER TABLE goi_y_lo_trinh
  ADD COLUMN nhom_kien_thuc_id INT UNSIGNED NULL AFTER ky_nang,
  MODIFY dang_cau ENUM('chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo','dich_cau') NULL,
  ADD CONSTRAINT fk_goi_y_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id);

-- 3.7 hoi_thoai: moi cau_tra_loi_id chi co toi da mot cuoc hoi thoai xuyen suot (khong xoa tao moi)
ALTER TABLE hoi_thoai
  ADD UNIQUE KEY uq_hoi_thoai_ctl (cau_tra_loi_id);
ALTER TABLE hoi_thoai
  DROP INDEX ix_hoi_thoai_ctl;

-- ---------------------------------------------------------------------
-- 4. Trigger tu dong ha co da_kiem_tra_audio = 0 khi tep_audio trong hoac bi doi
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_cau_hoi_bi_audio;
DROP TRIGGER IF EXISTS trg_cau_hoi_bu_audio;

DELIMITER $$

CREATE TRIGGER trg_cau_hoi_bi_audio
BEFORE INSERT ON cau_hoi
FOR EACH ROW
BEGIN
  IF NEW.tep_audio IS NULL THEN
    SET NEW.da_kiem_tra_audio = 0;
  END IF;
END$$

CREATE TRIGGER trg_cau_hoi_bu_audio
BEFORE UPDATE ON cau_hoi
FOR EACH ROW
BEGIN
  IF NEW.tep_audio IS NULL OR NOT (NEW.tep_audio <=> OLD.tep_audio) THEN
    SET NEW.da_kiem_tra_audio = 0;
  END IF;
END$$

DELIMITER ;

-- ---------------------------------------------------------------------
-- 5. Cap nhat VIEW v_ket_qua_hien_hanh (thay cac cot moi) va tao v_cau_hoi, v_bai_on
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_ket_qua_hien_hanh AS
SELECT k.id,
       k.cau_tra_loi_id,
       k.lan,
       k.nguon,
       k.trang_thai,
       k.phien_ban_luu,
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

CREATE OR REPLACE VIEW v_cau_hoi AS
SELECT q.id,
       q.ma_goc_id,
       q.phien_ban,
       q.dang,
       q.cau_cha_id,
       COALESCE(q.cap_do_id, p.cap_do_id) AS cap_do_id,
       COALESCE(q.ky_nang, p.ky_nang)     AS ky_nang,
       q.nhom_kien_thuc_id,
       COALESCE(p.dung_on_luyen, q.dung_on_luyen) AS dung_on_luyen,
       COALESCE(p.dung_thi_thu, q.dung_thi_thu)   AS dung_thi_thu,
       COALESCE(p.dung_dau_vao, q.dung_dau_vao)   AS dung_dau_vao,
       q.noi_dung,
       COALESCE(q.tep_audio, p.tep_audio) AS tep_audio_hieu_luc,
       q.tep_audio,
       q.da_kiem_tra_audio,
       q.tep_hinh,
       q.mo_ta_hinh,
       q.loi_nghe,
       q.pinyin,
       q.dich_nghia,
       q.goi_y,
       q.goi_y_2,
       q.giai_thich,
       q.dap_an_thu_tu,
       q.tu_bat_buoc,
       q.tieu_chi_mo_ta,
       q.diem_toi_da,
       q.nguong_dat,
       q.tu_vung_id,
       q.nguon_noi_dung,
       q.trang_thai,
       q.nguoi_tao_id,
       q.nguoi_duyet_id,
       q.duyet_luc,
       q.tao_luc
FROM cau_hoi q
LEFT JOIN cau_hoi p ON p.id = q.cau_cha_id;

CREATE OR REPLACE VIEW v_bai_on AS
SELECT b.id,
       b.ma_goc_id,
       b.phien_ban,
       b.loai,
       b.vi_tri,
       b.ten,
       b.muc_tieu,
       b.tai_lieu_id,
       b.trang_thai,
       b.thua_id AS thua_ma_goc_id,
       t.id      AS thua_phien_ban_id,
       t.ten     AS ten_thua,
       t.vi_tri  AS vi_tri_thua,
       t.trang_thai AS trang_thai_thua,
       t.cap_do_id,
       t.ky_nang
FROM bo_de b
JOIN bo_de t ON t.ma_goc_id = b.thua_id
  AND t.loai = 'thua'
  AND t.phien_ban = (SELECT MAX(x.phien_ban) FROM bo_de x WHERE x.ma_goc_id = b.thua_id)
WHERE b.loai IN ('bai', 'cuoi_thua');
