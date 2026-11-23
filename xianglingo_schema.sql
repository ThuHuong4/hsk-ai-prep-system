-- =====================================================================
-- Xianglingo - CSDL 24 bang (19 bang goc + 5 bang nghiep vu bo sung)
-- Muc chuan hoa: tat ca bang dat toi thieu 3NF; 5 bang moi dat BCNF.
-- Hai diem giu o 3NF / du thua co doi soat co chu dich:
--   1) nguoi_dung.nang_luong: doi soat qua v_doi_soat_nang_luong.
--   2) cau_tra_loi.cap_tham_do_id: de NULL o cac luot khong phai danh gia dau vao
--      thay vi tach bang phu 1-1 lam phuc tap truy van.
-- MySQL 8.0.16+ (CHECK duoc thuc thi tu 8.0.16; chi muc ham tu 8.0.13)
-- Ma hoa: utf8mb4. Gio luu: gio Viet Nam (Asia/Ho_Chi_Minh, +07:00) do may chu ghi.
-- Khong chua tai khoan, mat khau hay thong tin ket noi.
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '+07:00';

CREATE DATABASE IF NOT EXISTS xianglingo
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE xianglingo;

-- ---------------------------------------------------------------------
-- NHOM TAI KHOAN (3 bang)
-- ---------------------------------------------------------------------

-- 1. vai_tro (BCNF)
CREATE TABLE vai_tro (
  id   TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma   VARCHAR(30)  NOT NULL,
  ten  VARCHAR(50)  NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_vai_tro_ma (ma)
) ENGINE=InnoDB;

-- 4. cap_do (BCNF; tao truoc nguoi_dung vi nguoi_dung tham chieu cap_do)
CREATE TABLE cap_do (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma               VARCHAR(10)  NOT NULL,
  ten              VARCHAR(50)  NOT NULL,
  thu_tu           SMALLINT UNSIGNED NOT NULL,
  diem_toi_da_thi  SMALLINT UNSIGNED NOT NULL,
  diem_dat_thi     SMALLINT UNSIGNED NOT NULL,
  trang_thai       ENUM('nhap','da_dang','da_an') NOT NULL DEFAULT 'nhap',
  nguoi_tao_id     BIGINT UNSIGNED NULL,
  tao_luc          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cap_do_ma (ma),
  UNIQUE KEY uq_cap_do_thu_tu (thu_tu),
  CONSTRAINT ck_cap_do_diem CHECK (diem_dat_thi > 0 AND diem_dat_thi <= diem_toi_da_thi),
  CONSTRAINT ck_cap_do_thu_tu CHECK (thu_tu >= 1)
) ENGINE=InnoDB;

-- 2. nguoi_dung
-- Ghi chu: ks_cap_muc_tieu_id duoc dung chung lam cap HSK muc tieu cua hoc vien
-- (chon sau Danh gia dau vao 8 cau hoac cap nhat trong ho so; khong them cot trung nghia).
CREATE TABLE nguoi_dung (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  vai_tro_id          TINYINT UNSIGNED NOT NULL,
  email               VARCHAR(255) NOT NULL,
  ho_ten              VARCHAR(100) NOT NULL,
  mat_khau_bam        VARCHAR(255) NULL,
  google_sub          VARCHAR(64)  NULL,
  trang_thai          ENUM('hoat_dong','khoa') NOT NULL DEFAULT 'hoat_dong',
  email_xac_minh_luc  DATETIME NULL,
  phien_ban_phien     INT UNSIGNED NOT NULL DEFAULT 0,
  -- token xac minh email: chi luu hash; han = xm_gui_luc + 15 phut (tinh, khong luu)
  xm_token_bam        CHAR(64) NULL,
  xm_gui_luc          DATETIME NULL,
  -- token dat lai mat khau: cung quy tac
  dl_token_bam        CHAR(64) NULL,
  dl_gui_luc          DATETIME NULL,
  -- muc tieu hoc tap (giu tuong thich cot ks_* cu; ks_cap_muc_tieu_id la cap HSK muc tieu hien hanh)
  ks_trang_thai       ENUM('chua_lam','bo_qua','da_tra_loi') NOT NULL DEFAULT 'chua_lam',
  ks_da_hoc           ENUM('chua','da_hoc') NULL,
  ks_cap_muc_tieu_id  INT UNSIGNED NULL,
  ks_muc_dich         ENUM('on_luyen','thi_thu','ca_hai') NULL,
  ks_ky_nang          ENUM('nghe','doc','viet','tu_vung') NULL,
  ks_phut_moi_ngay    TINYINT UNSIGNED NULL,
  ks_cap_nhat_luc     DATETIME NULL,
  -- email nhac hoc vien vang 3 ngay
  nhan_email_nhac     BOOLEAN NOT NULL DEFAULT 1,
  nhac_gan_nhat_luc   DATETIME NULL,
  -- so du nang luong (du thua co chu dich o muc 3NF, doi soat bang v_doi_soat_nang_luong)
  nang_luong          TINYINT UNSIGNED NOT NULL DEFAULT 5,
  tao_luc             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_nguoi_dung_email (email),
  UNIQUE KEY uq_nguoi_dung_google (google_sub),
  KEY ix_nguoi_dung_vai_tro (vai_tro_id),
  CONSTRAINT ck_nguoi_dung_nang_luong CHECK (nang_luong BETWEEN 0 AND 5),
  CONSTRAINT ck_nguoi_dung_phut CHECK (ks_phut_moi_ngay IS NULL OR ks_phut_moi_ngay IN (10,15,30,60)),
  CONSTRAINT ck_nguoi_dung_dang_nhap CHECK (mat_khau_bam IS NOT NULL OR google_sub IS NOT NULL)
) ENGINE=InnoDB;

-- 3. nhat_ky_quan_tri (BCNF)
CREATE TABLE nhat_ky_quan_tri (
  id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nguoi_thao_tac_id     BIGINT UNSIGNED NOT NULL,
  nguoi_bi_tac_dong_id  BIGINT UNSIGNED NOT NULL,
  hanh_dong             ENUM('khoa','mo_khoa','doi_vai_tro','tao_tai_khoan') NOT NULL,
  vai_tro_cu_id         TINYINT UNSIGNED NULL,
  vai_tro_moi_id        TINYINT UNSIGNED NULL,
  ly_do                 VARCHAR(255) NULL,
  tao_luc               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_nkqt_bi_tac_dong (nguoi_bi_tac_dong_id, tao_luc),
  CONSTRAINT ck_nkqt_khac_nguoi CHECK (nguoi_thao_tac_id <> nguoi_bi_tac_dong_id),
  CONSTRAINT ck_nkqt_vai_tro CHECK (
    (hanh_dong = 'doi_vai_tro' AND vai_tro_cu_id IS NOT NULL AND vai_tro_moi_id IS NOT NULL)
    OR (hanh_dong <> 'doi_vai_tro' AND vai_tro_cu_id IS NULL AND vai_tro_moi_id IS NULL))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- NHOM NOI DUNG (7 bang: 6 bang goc + 1 bang moi nhom_kien_thuc)
-- Phien ban: (ma_goc_id, phien_ban) la khoa ung vien. Ban dau tien co ma_goc_id = id.
-- ---------------------------------------------------------------------

-- 20. nhom_kien_thuc (BANG MOI #1 - BCNF: danh muc chuan nhom kien thuc xuyen ky nang)
CREATE TABLE nhom_kien_thuc (
  id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma            VARCHAR(50)  NOT NULL,
  ten           VARCHAR(100) NOT NULL,
  mo_ta         TEXT NULL,
  trang_thai    ENUM('hoat_dong','da_an') NOT NULL DEFAULT 'hoat_dong',
  nguoi_tao_id  BIGINT UNSIGNED NULL,
  tao_luc       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_nhom_kien_thuc_ma (ma)
) ENGINE=InnoDB;

-- 9. tai_lieu (BCNF)
CREATE TABLE tai_lieu (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma_goc_id     BIGINT UNSIGNED NOT NULL,
  phien_ban     SMALLINT UNSIGNED NOT NULL,
  ten           VARCHAR(150) NOT NULL,
  mo_ta         TEXT NULL,
  nguon         VARCHAR(255) NULL,
  cap_do_id     INT UNSIGNED NULL,
  ky_nang       ENUM('nghe','doc','viet','tu_vung') NULL,
  loai_tep      ENUM('pdf','png','jpg','mp3','wav') NOT NULL,
  duong_dan     VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  kich_thuoc    INT UNSIGNED NOT NULL,
  trang_thai    ENUM('nhap','da_dang','da_an') NOT NULL DEFAULT 'nhap',
  nguoi_tao_id  BIGINT UNSIGNED NULL,
  tao_luc       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tai_lieu_phien_ban (ma_goc_id, phien_ban),
  UNIQUE KEY uq_tai_lieu_duong_dan (duong_dan),
  CONSTRAINT ck_tai_lieu_phien_ban CHECK (phien_ban >= 1),
  CONSTRAINT ck_tai_lieu_kich_thuoc CHECK (kich_thuoc > 0 AND kich_thuoc <= 20971520)
) ENGINE=InnoDB;

-- 10. tu_vung (BCNF; chu_han, pinyin phan biet dau thanh -> collation phan biet dau)
CREATE TABLE tu_vung (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  chu_han       VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL,
  pinyin        VARCHAR(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs NOT NULL,
  nghia         VARCHAR(255) NOT NULL,
  cap_do_id     INT UNSIGNED NOT NULL,
  vd_cau        TEXT NULL,
  vd_pinyin     TEXT NULL,
  vd_nghia      TEXT NULL,
  vd_audio      VARCHAR(255) NULL,
  trang_thai    ENUM('nhap','xuat_ban','ngung_xuat_ban') NOT NULL DEFAULT 'nhap',
  nguoi_tao_id  BIGINT UNSIGNED NULL,
  tao_luc       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tu_vung (chu_han, pinyin),
  KEY ix_tu_vung_cap (cap_do_id, trang_thai)
) ENGINE=InnoDB;

-- 5. cau_hoi (cau hoi va ngu lieu - cau cha; moi dong la mot phien ban)
-- Bo sung: dang 'dich_cau', nhom_kien_thuc_id, goi_y_2 (muc 2), nguon_noi_dung (NULL cho du lieu cu),
--          da_kiem_tra_audio (trigger + backend tu dat ve 0 moi khi doi tep_audio), nguoi_duyet_id, duyet_luc.
CREATE TABLE cau_hoi (
  id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma_goc_id           BIGINT UNSIGNED NOT NULL,
  phien_ban           SMALLINT UNSIGNED NOT NULL,
  dang                ENUM('ngu_lieu','chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo','dich_cau') NOT NULL,
  cau_cha_id          BIGINT UNSIGNED NULL,
  cap_do_id           INT UNSIGNED NULL,
  ky_nang             ENUM('nghe','doc','viet','tu_vung') NULL,
  nhom_kien_thuc_id   INT UNSIGNED NULL,
  dung_on_luyen       BOOLEAN NOT NULL DEFAULT 0,
  dung_thi_thu        BOOLEAN NOT NULL DEFAULT 0,
  dung_dau_vao        BOOLEAN NOT NULL DEFAULT 0,
  noi_dung            TEXT NULL,
  tep_audio           VARCHAR(255) NULL,
  da_kiem_tra_audio   BOOLEAN NOT NULL DEFAULT 0,
  tep_hinh            VARCHAR(255) NULL,
  mo_ta_hinh          TEXT NULL,
  loi_nghe            TEXT NULL,
  pinyin              TEXT NULL,
  dich_nghia          TEXT NULL,
  goi_y               TEXT NULL,
  goi_y_2             TEXT NULL,
  giai_thich          TEXT NULL,
  dap_an_thu_tu       TINYINT UNSIGNED NULL,
  tu_bat_buoc         VARCHAR(20) NULL,
  tieu_chi_mo_ta      TEXT NULL,
  diem_toi_da         DECIMAL(5,2) NULL,
  nguong_dat          DECIMAL(5,2) NULL,
  tu_vung_id          BIGINT UNSIGNED NULL,
  nguon_noi_dung      ENUM('tu_soan','soan_voi_ai','nguon_duoc_phep') NULL DEFAULT NULL,
  trang_thai          ENUM('nhap','da_dang','da_an') NOT NULL DEFAULT 'nhap',
  nguoi_tao_id        BIGINT UNSIGNED NULL,
  nguoi_duyet_id      BIGINT UNSIGNED NULL,
  duyet_luc           DATETIME NULL,
  tao_luc             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cau_hoi_phien_ban (ma_goc_id, phien_ban),
  KEY ix_cau_hoi_cha (cau_cha_id),
  KEY ix_cau_hoi_loc (cap_do_id, ky_nang, dang, trang_thai),
  KEY ix_cau_hoi_nhom (nhom_kien_thuc_id, trang_thai),
  CONSTRAINT ck_cau_hoi_phien_ban CHECK (phien_ban >= 1),
  CONSTRAINT ck_cau_hoi_ngu_lieu CHECK (dang <> 'ngu_lieu' OR (cau_cha_id IS NULL AND nhom_kien_thuc_id IS NULL)),
  CONSTRAINT ck_cau_hoi_phan_loai CHECK (
    (cau_cha_id IS NULL AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (cau_cha_id IS NOT NULL AND cap_do_id IS NULL AND ky_nang IS NULL)),
  CONSTRAINT ck_cau_hoi_dap_an_bo_chung CHECK (
    (dang = 'chon_bo_chung' AND dap_an_thu_tu IS NOT NULL)
    OR (dang <> 'chon_bo_chung' AND dap_an_thu_tu IS NULL)),
  CONSTRAINT ck_cau_hoi_diem CHECK (
    (dang IN ('viet_mo','dich_cau') AND diem_toi_da IS NOT NULL AND nguong_dat IS NOT NULL
       AND diem_toi_da > 0 AND nguong_dat > 0 AND nguong_dat <= diem_toi_da)
    OR (dang NOT IN ('viet_mo','dich_cau') AND diem_toi_da IS NULL AND nguong_dat IS NULL)),
  CONSTRAINT ck_cau_hoi_audio_duyet CHECK (da_kiem_tra_audio = 0 OR tep_audio IS NOT NULL),
  CONSTRAINT ck_cau_hoi_duyet CHECK (
    (nguoi_duyet_id IS NULL AND duyet_luc IS NULL)
    OR (nguoi_duyet_id IS NOT NULL AND duyet_luc IS NOT NULL))
) ENGINE=InnoDB;

-- 6. phuong_an (BCNF)
CREATE TABLE phuong_an (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cau_hoi_id       BIGINT UNSIGNED NOT NULL,
  vai_tro          ENUM('lua_chon','dap_an_chap_nhan') NOT NULL,
  thu_tu           TINYINT UNSIGNED NOT NULL,
  la_dap_an_dung   BOOLEAN NOT NULL DEFAULT 0,
  noi_dung         TEXT NULL,
  tep_hinh         VARCHAR(255) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_phuong_an (cau_hoi_id, vai_tro, thu_tu),
  CONSTRAINT ck_phuong_an_dung CHECK (vai_tro = 'lua_chon' OR la_dap_an_dung = 0),
  CONSTRAINT ck_phuong_an_noi_dung CHECK (noi_dung IS NOT NULL OR tep_hinh IS NOT NULL)
) ENGINE=InnoDB;
CREATE UNIQUE INDEX uq_phuong_an_mot_dap_an
  ON phuong_an (cau_hoi_id, ((CASE WHEN la_dap_an_dung = 1 THEN 1 END)));

-- 7. bo_de (thua, bai on, kiem tra cuoi thua, de thi thu; moi dong la mot phien ban)
CREATE TABLE bo_de (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ma_goc_id        BIGINT UNSIGNED NOT NULL,
  phien_ban        SMALLINT UNSIGNED NOT NULL,
  loai             ENUM('thua','bai','cuoi_thua','de_thi') NOT NULL,
  thua_id          BIGINT UNSIGNED NULL,
  cap_do_id        INT UNSIGNED NULL,
  ky_nang          ENUM('nghe','doc','viet','tu_vung') NULL,
  ten              VARCHAR(150) NOT NULL,
  muc_tieu         TEXT NULL,
  vi_tri           SMALLINT UNSIGNED NULL,
  ma_de            VARCHAR(30) NULL,
  nguon            VARCHAR(255) NULL,
  thoi_luong_phut  SMALLINT UNSIGNED NULL,
  tep_audio_chung  VARCHAR(255) NULL,
  tep_pdf_goc      VARCHAR(255) NULL,
  tai_lieu_id      BIGINT UNSIGNED NULL,
  trang_thai       ENUM('nhap','da_dang','da_an') NOT NULL DEFAULT 'nhap',
  nguoi_tao_id     BIGINT UNSIGNED NULL,
  tao_luc          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_bo_de_phien_ban (ma_goc_id, phien_ban),
  UNIQUE KEY uq_bo_de_ma_de (ma_de),
  KEY ix_bo_de_thua (thua_id, vi_tri),
  KEY ix_bo_de_loc (loai, cap_do_id, ky_nang, trang_thai),
  CONSTRAINT ck_bo_de_phien_ban CHECK (phien_ban >= 1),
  CONSTRAINT ck_bo_de_vi_tri CHECK (
    vi_tri IS NULL
    OR (loai = 'bai' AND vi_tri BETWEEN 1 AND 4)
    OR (loai = 'cuoi_thua' AND vi_tri = 5)
    OR (loai = 'thua' AND vi_tri >= 1)),
  CONSTRAINT ck_bo_de_cau_truc CHECK (
    (loai = 'thua'   AND thua_id IS NULL     AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (loai IN ('bai','cuoi_thua') AND thua_id IS NOT NULL AND cap_do_id IS NULL AND ky_nang IS NULL)
    OR (loai = 'de_thi' AND thua_id IS NULL  AND cap_do_id IS NOT NULL AND ky_nang IS NULL)),
  CONSTRAINT ck_bo_de_de_thi CHECK (
    (loai = 'de_thi' AND vi_tri IS NULL AND (thoi_luong_phut IS NULL OR thoi_luong_phut > 0))
    OR (loai <> 'de_thi' AND ma_de IS NULL AND nguon IS NULL AND thoi_luong_phut IS NULL
        AND tep_audio_chung IS NULL AND tep_pdf_goc IS NULL))
) ENGINE=InnoDB;

-- 8. bo_de_cau_hoi (BCNF)
CREATE TABLE bo_de_cau_hoi (
  bo_de_id      BIGINT UNSIGNED NOT NULL,
  cau_hoi_id    BIGINT UNSIGNED NOT NULL,
  thu_tu        SMALLINT UNSIGNED NOT NULL,
  phan          TINYINT UNSIGNED NULL,
  la_cau_vi_du  BOOLEAN NOT NULL DEFAULT 0,
  PRIMARY KEY (bo_de_id, cau_hoi_id),
  UNIQUE KEY uq_bo_de_cau_hoi_thu_tu (bo_de_id, thu_tu),
  KEY ix_bdch_cau_hoi (cau_hoi_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- NHOM HOC TAP & DANH GIA (10 bang: 6 bang goc + 4 bang moi)
-- ---------------------------------------------------------------------

-- 11. luot_lam
-- Luu y: danh_gia_dau_vao la bai 8 cau da ky nang va da cap do nen cap_do_id IS NULL, ky_nang IS NULL.
CREATE TABLE luot_lam (
  id                     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nguoi_dung_id          BIGINT UNSIGNED NOT NULL,
  bo_de_id               BIGINT UNSIGNED NULL,
  muc_dich               ENUM('hoc_moi','lam_lai','on_lai') NULL,
  loai_boc_cau           ENUM('vuot_thua','bat_dau_cap','vuot_chang','danh_gia_dau_vao','so_tay','on_ho_tro') NULL,
  thua_dich_id           BIGINT UNSIGNED NULL,
  cap_do_id              INT UNSIGNED NULL,
  ky_nang                ENUM('nghe','doc','viet','tu_vung') NULL,
  trang_thai             ENUM('dang_lam','da_nop','da_bo','tam_dung') NOT NULL DEFAULT 'dang_lam',
  bat_dau_luc            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  nop_luc                DATETIME NULL,
  ly_do_nop              ENUM('nop_tay','het_gio') NULL,
  vi_tri_hien_tai        SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  vi_tri_audio_chung_ms  INT UNSIGNED NULL,
  ap_dung_luc            DATETIME NULL,
  goi_y_luc              DATETIME NULL,
  PRIMARY KEY (id),
  KEY ix_luot_lam_nguoi (nguoi_dung_id, bat_dau_luc),
  KEY ix_luot_lam_bo_de (bo_de_id),
  CONSTRAINT ck_luot_lam_kieu CHECK (
    (bo_de_id IS NOT NULL AND loai_boc_cau IS NULL)
    OR (bo_de_id IS NULL AND loai_boc_cau IS NOT NULL)),
  CONSTRAINT ck_luot_lam_muc_dich CHECK (muc_dich IS NULL OR bo_de_id IS NOT NULL),
  CONSTRAINT ck_luot_lam_thua_dich CHECK (
    (COALESCE(loai_boc_cau, '') = 'vuot_thua' AND thua_dich_id IS NOT NULL)
    OR (COALESCE(loai_boc_cau, '') <> 'vuot_thua' AND thua_dich_id IS NULL)),
  CONSTRAINT ck_luot_lam_pham_vi CHECK (
    (COALESCE(loai_boc_cau, '') IN ('bat_dau_cap','vuot_chang','on_ho_tro')
       AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (COALESCE(loai_boc_cau, '') NOT IN ('bat_dau_cap','vuot_chang','on_ho_tro')
       AND cap_do_id IS NULL AND ky_nang IS NULL)),
  CONSTRAINT ck_luot_lam_nop CHECK ((nop_luc IS NULL AND ly_do_nop IS NULL) OR (nop_luc IS NOT NULL AND ly_do_nop IS NOT NULL)),
  CONSTRAINT ck_luot_lam_da_nop CHECK (trang_thai <> 'da_nop' OR nop_luc IS NOT NULL)
) ENGINE=InnoDB;
CREATE UNIQUE INDEX uq_luot_lam_dang_lam
  ON luot_lam (nguoi_dung_id, bo_de_id, ((CASE WHEN trang_thai = 'dang_lam' THEN 1 END)));

-- 12. cau_tra_loi (3NF; cap_tham_do_id chi dung cho danh_gia_dau_vao, de NULL o cac luot khac)
-- Ghi chu Phu luc A:
--   * trang_thai_thao_tac: chua_thao_tac | da_tra_loi | bo_qua | loi_ky_thuat
--   * muc_goi_y: 0 (khong mo goi y), 1 (mo muc 1), 2 (mo muc 2) truoc khi xac nhan.
--   * Viec Hoi Xiang truoc hay sau khi xac nhan suy ra tu hoi_thoai(cau_tra_loi_id) + tin_nhan.tao_luc < xac_nhan_luc.
--   * Viec xem loi giai sau khi cham ghi o xem_loi_giai_luc (khong lam doi muc_goi_y).
CREATE TABLE cau_tra_loi (
  id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  luot_lam_id          BIGINT UNSIGNED NOT NULL,
  cau_hoi_id           BIGINT UNSIGNED NOT NULL,
  thu_tu               SMALLINT UNSIGNED NOT NULL,
  cap_tham_do_id       INT UNSIGNED NULL,
  seed_xao             INT UNSIGNED NULL,
  trang_thai_thao_tac  ENUM('chua_thao_tac','da_tra_loi','bo_qua','loi_ky_thuat') NOT NULL DEFAULT 'chua_thao_tac',
  muc_goi_y            TINYINT UNSIGNED NOT NULL DEFAULT 0,
  phuong_an_chon_id    BIGINT UNSIGNED NULL,
  van_ban              TEXT NULL,
  thoi_gian_lam_giay   SMALLINT UNSIGNED NULL,
  xac_nhan_luc         DATETIME NULL,
  xem_loi_giai_luc     DATETIME NULL,
  phien_ban_luu        INT UNSIGNED NOT NULL DEFAULT 0,
  vi_tri_audio_ms      INT UNSIGNED NULL,
  da_nghe_xong         BOOLEAN NOT NULL DEFAULT 0,
  nang_luong_tru       TINYINT UNSIGNED NOT NULL DEFAULT 0,
  nang_luong_hoan      TINYINT UNSIGNED NOT NULL DEFAULT 0,
  hoan_luc             DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ctl_cau (luot_lam_id, cau_hoi_id),
  UNIQUE KEY uq_ctl_thu_tu (luot_lam_id, thu_tu),
  KEY ix_ctl_cau_hoi (cau_hoi_id),
  CONSTRAINT ck_ctl_mot_kieu CHECK (phuong_an_chon_id IS NULL OR van_ban IS NULL),
  CONSTRAINT ck_ctl_muc_goi_y CHECK (muc_goi_y IN (0, 1, 2)),
  CONSTRAINT ck_ctl_thao_tac CHECK (
    trang_thai_thao_tac NOT IN ('bo_qua','loi_ky_thuat')
    OR (phuong_an_chon_id IS NULL AND van_ban IS NULL)),
  CONSTRAINT ck_ctl_tru CHECK (nang_luong_tru IN (0, 1)),
  CONSTRAINT ck_ctl_hoan CHECK (nang_luong_hoan <= nang_luong_tru),
  CONSTRAINT ck_ctl_hoan_luc CHECK ((nang_luong_hoan = 0 AND hoan_luc IS NULL) OR (nang_luong_hoan > 0 AND hoan_luc IS NOT NULL))
) ENGINE=InnoDB;

-- 13. ket_qua_cham (BCNF; moi lan cham/sua la mot dong; hien hanh = lan lon nhat hoan_tat)
-- phien_ban_luu: ghi lai cau_tra_loi.phien_ban_luu tai thoi diem cham de tai su dung diem AI khi thu lai (AT36).
CREATE TABLE ket_qua_cham (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cau_tra_loi_id  BIGINT UNSIGNED NOT NULL,
  lan             SMALLINT UNSIGNED NOT NULL,
  nguon           ENUM('code','ai','giang_vien') NOT NULL,
  trang_thai      ENUM('dang_xu_ly','loi','hoan_tat') NOT NULL,
  phien_ban_luu   INT UNSIGNED NULL,
  diem            DECIMAL(5,2) NULL,
  nhan_xet        TEXT NULL,
  cau_sua         TEXT NULL,
  ly_do_sua       TEXT NULL,
  nguoi_cham_id   BIGINT UNSIGNED NULL,
  mo_hinh         VARCHAR(50) NULL,
  tao_luc         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_kqc_lan (cau_tra_loi_id, lan),
  CONSTRAINT ck_kqc_lan CHECK (lan >= 1),
  CONSTRAINT ck_kqc_nguoi_cham CHECK (
    (nguon = 'giang_vien' AND nguoi_cham_id IS NOT NULL)
    OR (nguon <> 'giang_vien' AND nguoi_cham_id IS NULL)),
  CONSTRAINT ck_kqc_diem CHECK (
    (trang_thai = 'hoan_tat' AND diem IS NOT NULL AND diem >= 0)
    OR (trang_thai <> 'hoan_tat' AND diem IS NULL))
) ENGINE=InnoDB;

-- 21. ket_qua_dau_vao (BANG MOI #2 - BCNF: trang thai phan tich AI va ket luan tong quan phien 8 cau)
-- Ghi chu: bai on cu the duoc de xuat luu trong bang goi_y_lo_trinh theo luot_lam_id (khong luu trung o day);
--          viec gioi han du lieu suy ra tu so cau bo_qua / loi_ky_thuat / cap du phong.
CREATE TABLE ket_qua_dau_vao (
  luot_lam_id             BIGINT UNSIGNED NOT NULL,
  trang_thai_phan_tich    ENUM('chua','dang','xong','loi') NOT NULL DEFAULT 'chua',
  bat_dau_phan_tich_luc   DATETIME NULL,
  hoan_tat_phan_tich_luc  DATETIME NULL,
  cap_de_xuat_id          INT UNSIGNED NULL,
  ghi_chu_gioi_han        TEXT NULL,
  PRIMARY KEY (luot_lam_id),
  CONSTRAINT ck_kqdv_thoi_gian CHECK (
    hoan_tat_phan_tich_luc IS NULL OR bat_dau_phan_tich_luc IS NOT NULL)
) ENGINE=InnoDB;

-- 22. nhan_dinh_dau_vao (BANG MOI #3 - BCNF: nhan dinh diem manh / diem yeu theo ky nang va nhom kien thuc)
-- ky_nang de NULL cho nhan xet tong quan khong gan rieng mot ky nang cu the.
CREATE TABLE nhan_dinh_dau_vao (
  luot_lam_id        BIGINT UNSIGNED NOT NULL,
  thu_tu             TINYINT UNSIGNED NOT NULL,
  ky_nang            ENUM('nghe','doc','viet','tu_vung') NULL DEFAULT NULL,
  nhom_kien_thuc_id  INT UNSIGNED NULL,
  loai               ENUM('diem_manh','diem_yeu','nhan_xet') NOT NULL,
  noi_dung           TEXT NOT NULL,
  PRIMARY KEY (luot_lam_id, thu_tu),
  CONSTRAINT ck_nddv_thu_tu CHECK (thu_tu >= 1)
) ENGINE=InnoDB;

-- 23. nhan_dinh_bang_chung (BANG MOI #4 - BCNF: lien ket N-N giua nhan dinh va cau bang chung cung luot)
-- Khoa ngoai kep bao dam 100% o cap CSDL rang cau bang chung phai thuoc dung luot_lam_id cua nhan dinh (AT37, AT52).
CREATE TABLE nhan_dinh_bang_chung (
  luot_lam_id       BIGINT UNSIGNED NOT NULL,
  thu_tu_nhan_dinh  TINYINT UNSIGNED NOT NULL,
  thu_tu_cau        SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (luot_lam_id, thu_tu_nhan_dinh, thu_tu_cau)
) ENGINE=InnoDB;

-- 24. lich_su_thay_cau (BANG MOI #5 - BCNF: luu vet doi cau tai cho khi loi ky thuat o AT06, AT33)
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
  CONSTRAINT ck_lstc_khac_cau CHECK (cau_hoi_cu_id <> cau_hoi_moi_id)
) ENGINE=InnoDB;

-- 14. so_tay (BCNF)
CREATE TABLE so_tay (
  nguoi_dung_id   BIGINT UNSIGNED NOT NULL,
  cau_hoi_goc_id  BIGINT UNSIGNED NOT NULL,
  trang_thai      ENUM('can_on','cho_on_lai','da_cung_co','da_loai') NOT NULL DEFAULT 'can_on',
  han_on          DATE NULL,
  cap_nhat_luc    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (nguoi_dung_id, cau_hoi_goc_id),
  KEY ix_so_tay_han (nguoi_dung_id, trang_thai, han_on)
) ENGINE=InnoDB;

-- 15. nhat_ky_thuong (bien dong cap nguoi dung; luot_lam_id lien ket chat diem thuong KN ve luot lam)
CREATE TABLE nhat_ky_thuong (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nguoi_dung_id   BIGINT UNSIGNED NOT NULL,
  luot_lam_id     BIGINT UNSIGNED NULL,
  ly_do           ENUM('khoi_tao','nv_so_tay','nv_on_luyen','nv_thi_thu',
                       'kn_bai','kn_cuoi_thua','kn_vuot_thua','kn_bat_dau_cap','kn_vuot_chang','kn_cung_co') NOT NULL,
  so_luong        SMALLINT UNSIGNED NOT NULL,
  tao_luc         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  bo_de_goc_id    BIGINT UNSIGNED NULL,
  cau_hoi_goc_id  BIGINT UNSIGNED NULL,
  cap_do_id       INT UNSIGNED NULL,
  ky_nang         ENUM('nghe','doc','viet','tu_vung') NULL,
  PRIMARY KEY (id),
  KEY ix_nkt_nguoi (nguoi_dung_id, tao_luc),
  KEY ix_nkt_luot (luot_lam_id),
  UNIQUE KEY uq_nkt_kn_bo_de (nguoi_dung_id, ly_do, bo_de_goc_id),
  UNIQUE KEY uq_nkt_kn_cung_co (nguoi_dung_id, cau_hoi_goc_id),
  UNIQUE KEY uq_nkt_kn_cap (nguoi_dung_id, ly_do, cap_do_id, ky_nang),
  CONSTRAINT ck_nkt_bo_de CHECK (
    (ly_do IN ('kn_bai','kn_cuoi_thua','kn_vuot_thua') AND bo_de_goc_id IS NOT NULL)
    OR (ly_do NOT IN ('kn_bai','kn_cuoi_thua','kn_vuot_thua') AND bo_de_goc_id IS NULL)),
  CONSTRAINT ck_nkt_cau_hoi CHECK (
    (ly_do = 'kn_cung_co' AND cau_hoi_goc_id IS NOT NULL)
    OR (ly_do <> 'kn_cung_co' AND cau_hoi_goc_id IS NULL)),
  CONSTRAINT ck_nkt_cap CHECK (
    (ly_do IN ('kn_bat_dau_cap','kn_vuot_chang') AND cap_do_id IS NOT NULL AND ky_nang IS NOT NULL)
    OR (ly_do NOT IN ('kn_bat_dau_cap','kn_vuot_chang') AND cap_do_id IS NULL AND ky_nang IS NULL))
) ENGINE=InnoDB;
CREATE UNIQUE INDEX uq_nkt_nhiem_vu_ngay
  ON nhat_ky_thuong (nguoi_dung_id, ly_do,
     ((CASE WHEN ly_do IN ('nv_so_tay','nv_on_luyen','nv_thi_thu') THEN DATE(tao_luc) END)));
CREATE UNIQUE INDEX uq_nkt_khoi_tao
  ON nhat_ky_thuong (nguoi_dung_id, ((CASE WHEN ly_do = 'khoi_tao' THEN 1 END)));

-- 16. goi_y_lo_trinh (BCNF; dung chung cho de xuat sau Danh gia dau vao va sau Thi thu)
CREATE TABLE goi_y_lo_trinh (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  luot_lam_id        BIGINT UNSIGNED NOT NULL,
  thu_tu             TINYINT UNSIGNED NOT NULL,
  ky_nang            ENUM('nghe','doc','viet','tu_vung') NOT NULL,
  nhom_kien_thuc_id  INT UNSIGNED NULL,
  dang_cau           ENUM('chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo','dich_cau') NULL,
  ly_do              TEXT NOT NULL,
  bo_de_id           BIGINT UNSIGNED NULL,
  tai_lieu_id        BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_goi_y_thu_tu (luot_lam_id, thu_tu),
  CONSTRAINT ck_goi_y_mot_dich CHECK (
    (bo_de_id IS NOT NULL AND tai_lieu_id IS NULL)
    OR (bo_de_id IS NULL AND tai_lieu_id IS NOT NULL))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- NHOM TUONG TAC (3 bang)
-- ---------------------------------------------------------------------

-- 17. hoi_thoai (BCNF; chat chung luu nguoi_dung_id; chat theo cau luu cau_tra_loi_id)
-- Quy tac: moi cau_tra_loi_id chi co TOI DA MOT cuoc hoi_thoai xuyen suot truoc va sau khi kiem tra
--          (noi tiep tin nhan vao cuoc hoi thoai hien co, khong xoa de tao cuoc moi).
CREATE TABLE hoi_thoai (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nguoi_dung_id   BIGINT UNSIGNED NULL,
  cau_tra_loi_id  BIGINT UNSIGNED NULL,
  xoa_luc         DATETIME NULL,
  tao_luc         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_hoi_thoai_ctl (cau_tra_loi_id),
  KEY ix_hoi_thoai_nguoi (nguoi_dung_id),
  CONSTRAINT ck_hoi_thoai_mot_chu CHECK (
    (nguoi_dung_id IS NOT NULL AND cau_tra_loi_id IS NULL)
    OR (nguoi_dung_id IS NULL AND cau_tra_loi_id IS NOT NULL))
) ENGINE=InnoDB;

-- 18. tin_nhan (BCNF)
CREATE TABLE tin_nhan (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  hoi_thoai_id    BIGINT UNSIGNED NOT NULL,
  vai             ENUM('hoc_vien','xiang') NOT NULL,
  noi_dung        TEXT NOT NULL,
  trang_thai      ENUM('dang_xu_ly','xong','loi') NOT NULL,
  khoa_chong_lap  VARCHAR(64) NULL,
  tao_luc         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_tin_nhan_hoi_thoai (hoi_thoai_id, tao_luc),
  UNIQUE KEY uq_tin_nhan_chong_lap (hoi_thoai_id, khoa_chong_lap)
) ENGINE=InnoDB;
CREATE UNIQUE INDEX uq_tin_nhan_dang_xu_ly
  ON tin_nhan (hoi_thoai_id, ((CASE WHEN trang_thai = 'dang_xu_ly' THEN 1 END)));

-- 19. bao_loi
CREATE TABLE bao_loi (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cau_tra_loi_id     BIGINT UNSIGNED NOT NULL,
  loai               ENUM('noi_dung','cham_sai') NOT NULL,
  ly_do              TEXT NOT NULL,
  lan_bi_bao         SMALLINT UNSIGNED NULL,
  nguoi_xu_ly_id     BIGINT UNSIGNED NULL,
  nhan_luc           DATETIME NULL,
  xu_ly_luc          DATETIME NULL,
  ket_luan           ENUM('da_sua','khong_phai_loi','giu_nguyen','sua_diem') NULL,
  phan_hoi           TEXT NULL,
  lan_ket_qua        SMALLINT UNSIGNED NULL,
  bs_ly_do           TEXT NULL,
  bs_gui_luc         DATETIME NULL,
  bs_nguoi_xu_ly_id  BIGINT UNSIGNED NULL,
  bs_nhan_luc        DATETIME NULL,
  bs_xu_ly_luc       DATETIME NULL,
  bs_ket_luan        ENUM('giu_nguyen','sua_diem') NULL,
  bs_phan_hoi        TEXT NULL,
  bs_lan_ket_qua     SMALLINT UNSIGNED NULL,
  tao_luc            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_bao_loi_xu_ly (xu_ly_luc, loai),
  CONSTRAINT ck_bao_loi_lan_bi_bao CHECK (
    (loai = 'cham_sai' AND lan_bi_bao IS NOT NULL) OR (loai = 'noi_dung' AND lan_bi_bao IS NULL)),
  CONSTRAINT ck_bao_loi_ket_luan CHECK (
    ket_luan IS NULL
    OR (loai = 'noi_dung' AND ket_luan IN ('da_sua','khong_phai_loi'))
    OR (loai = 'cham_sai' AND ket_luan IN ('giu_nguyen','sua_diem'))),
  CONSTRAINT ck_bao_loi_nhan CHECK (nhan_luc IS NULL OR nguoi_xu_ly_id IS NOT NULL),
  CONSTRAINT ck_bao_loi_xu_ly CHECK (
    xu_ly_luc IS NULL OR (nhan_luc IS NOT NULL AND ket_luan IS NOT NULL AND phan_hoi IS NOT NULL)),
  CONSTRAINT ck_bao_loi_lan_ket_qua CHECK (lan_ket_qua IS NULL OR loai = 'cham_sai'),
  CONSTRAINT ck_bao_loi_bo_sung CHECK (
    bs_gui_luc IS NULL OR (loai = 'cham_sai' AND xu_ly_luc IS NOT NULL AND bs_ly_do IS NOT NULL)),
  CONSTRAINT ck_bao_loi_bs_xu_ly CHECK (
    bs_xu_ly_luc IS NULL OR (bs_gui_luc IS NOT NULL AND bs_ket_luan IS NOT NULL AND bs_phan_hoi IS NOT NULL))
) ENGINE=InnoDB;
CREATE UNIQUE INDEX uq_bao_loi_dang_mo
  ON bao_loi (cau_tra_loi_id, loai, ((CASE WHEN xu_ly_luc IS NULL THEN 1 END)));

-- ---------------------------------------------------------------------
-- KHOA NGOAI (lien ket chat che giua cac bang; mac dinh RESTRICT)
-- ---------------------------------------------------------------------

ALTER TABLE cap_do
  ADD CONSTRAINT fk_cap_do_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id);

ALTER TABLE nguoi_dung
  ADD CONSTRAINT fk_nguoi_dung_vai_tro FOREIGN KEY (vai_tro_id) REFERENCES vai_tro (id),
  ADD CONSTRAINT fk_nguoi_dung_cap_muc_tieu FOREIGN KEY (ks_cap_muc_tieu_id) REFERENCES cap_do (id);

ALTER TABLE nhat_ky_quan_tri
  ADD CONSTRAINT fk_nkqt_thao_tac FOREIGN KEY (nguoi_thao_tac_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_nkqt_bi_tac_dong FOREIGN KEY (nguoi_bi_tac_dong_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_nkqt_vai_tro_cu FOREIGN KEY (vai_tro_cu_id) REFERENCES vai_tro (id),
  ADD CONSTRAINT fk_nkqt_vai_tro_moi FOREIGN KEY (vai_tro_moi_id) REFERENCES vai_tro (id);

ALTER TABLE nhom_kien_thuc
  ADD CONSTRAINT fk_nkt_dm_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id);

ALTER TABLE tai_lieu
  ADD CONSTRAINT fk_tai_lieu_goc FOREIGN KEY (ma_goc_id) REFERENCES tai_lieu (id),
  ADD CONSTRAINT fk_tai_lieu_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT fk_tai_lieu_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id);

ALTER TABLE tu_vung
  ADD CONSTRAINT fk_tu_vung_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT fk_tu_vung_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id);

ALTER TABLE cau_hoi
  ADD CONSTRAINT fk_cau_hoi_goc FOREIGN KEY (ma_goc_id) REFERENCES cau_hoi (id),
  ADD CONSTRAINT fk_cau_hoi_cha FOREIGN KEY (cau_cha_id) REFERENCES cau_hoi (id),
  ADD CONSTRAINT fk_cau_hoi_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT fk_cau_hoi_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id),
  ADD CONSTRAINT fk_cau_hoi_tu_vung FOREIGN KEY (tu_vung_id) REFERENCES tu_vung (id),
  ADD CONSTRAINT fk_cau_hoi_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_cau_hoi_nguoi_duyet FOREIGN KEY (nguoi_duyet_id) REFERENCES nguoi_dung (id);

ALTER TABLE phuong_an
  ADD CONSTRAINT fk_phuong_an_cau_hoi FOREIGN KEY (cau_hoi_id) REFERENCES cau_hoi (id);

ALTER TABLE bo_de
  ADD CONSTRAINT fk_bo_de_goc FOREIGN KEY (ma_goc_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_bo_de_thua FOREIGN KEY (thua_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_bo_de_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT fk_bo_de_tai_lieu FOREIGN KEY (tai_lieu_id) REFERENCES tai_lieu (id),
  ADD CONSTRAINT fk_bo_de_nguoi_tao FOREIGN KEY (nguoi_tao_id) REFERENCES nguoi_dung (id);

ALTER TABLE bo_de_cau_hoi
  ADD CONSTRAINT fk_bdch_bo_de FOREIGN KEY (bo_de_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_bdch_cau_hoi FOREIGN KEY (cau_hoi_id) REFERENCES cau_hoi (id);

ALTER TABLE luot_lam
  ADD CONSTRAINT fk_luot_lam_nguoi FOREIGN KEY (nguoi_dung_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_luot_lam_bo_de FOREIGN KEY (bo_de_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_luot_lam_thua_dich FOREIGN KEY (thua_dich_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_luot_lam_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id);

ALTER TABLE cau_tra_loi
  ADD CONSTRAINT fk_ctl_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  ADD CONSTRAINT fk_ctl_cau_hoi FOREIGN KEY (cau_hoi_id) REFERENCES cau_hoi (id),
  ADD CONSTRAINT fk_ctl_cap_tham_do FOREIGN KEY (cap_tham_do_id) REFERENCES cap_do (id),
  ADD CONSTRAINT fk_ctl_phuong_an FOREIGN KEY (phuong_an_chon_id) REFERENCES phuong_an (id);

ALTER TABLE ket_qua_cham
  ADD CONSTRAINT fk_kqc_ctl FOREIGN KEY (cau_tra_loi_id) REFERENCES cau_tra_loi (id),
  ADD CONSTRAINT fk_kqc_nguoi_cham FOREIGN KEY (nguoi_cham_id) REFERENCES nguoi_dung (id);

ALTER TABLE ket_qua_dau_vao
  ADD CONSTRAINT fk_kqdv_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  ADD CONSTRAINT fk_kqdv_cap_de_xuat FOREIGN KEY (cap_de_xuat_id) REFERENCES cap_do (id);

ALTER TABLE nhan_dinh_dau_vao
  ADD CONSTRAINT fk_nddv_kqdv FOREIGN KEY (luot_lam_id) REFERENCES ket_qua_dau_vao (luot_lam_id),
  ADD CONSTRAINT fk_nddv_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id);

ALTER TABLE nhan_dinh_bang_chung
  ADD CONSTRAINT fk_ndbc_nhan_dinh FOREIGN KEY (luot_lam_id, thu_tu_nhan_dinh)
      REFERENCES nhan_dinh_dau_vao (luot_lam_id, thu_tu),
  ADD CONSTRAINT fk_ndbc_cau_tra_loi FOREIGN KEY (luot_lam_id, thu_tu_cau)
      REFERENCES cau_tra_loi (luot_lam_id, thu_tu);

ALTER TABLE lich_su_thay_cau
  ADD CONSTRAINT fk_lstc_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  ADD CONSTRAINT fk_lstc_cau_cu FOREIGN KEY (cau_hoi_cu_id) REFERENCES cau_hoi (id),
  ADD CONSTRAINT fk_lstc_cau_moi FOREIGN KEY (cau_hoi_moi_id) REFERENCES cau_hoi (id);

ALTER TABLE so_tay
  ADD CONSTRAINT fk_so_tay_nguoi FOREIGN KEY (nguoi_dung_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_so_tay_cau_goc FOREIGN KEY (cau_hoi_goc_id) REFERENCES cau_hoi (id);

ALTER TABLE nhat_ky_thuong
  ADD CONSTRAINT fk_nkt_nguoi FOREIGN KEY (nguoi_dung_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_nkt_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  ADD CONSTRAINT fk_nkt_bo_de_goc FOREIGN KEY (bo_de_goc_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_nkt_cau_hoi_goc FOREIGN KEY (cau_hoi_goc_id) REFERENCES cau_hoi (id),
  ADD CONSTRAINT fk_nkt_cap FOREIGN KEY (cap_do_id) REFERENCES cap_do (id);

ALTER TABLE goi_y_lo_trinh
  ADD CONSTRAINT fk_goi_y_luot FOREIGN KEY (luot_lam_id) REFERENCES luot_lam (id),
  ADD CONSTRAINT fk_goi_y_nhom FOREIGN KEY (nhom_kien_thuc_id) REFERENCES nhom_kien_thuc (id),
  ADD CONSTRAINT fk_goi_y_bo_de FOREIGN KEY (bo_de_id) REFERENCES bo_de (id),
  ADD CONSTRAINT fk_goi_y_tai_lieu FOREIGN KEY (tai_lieu_id) REFERENCES tai_lieu (id);

ALTER TABLE hoi_thoai
  ADD CONSTRAINT fk_hoi_thoai_nguoi FOREIGN KEY (nguoi_dung_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_hoi_thoai_ctl FOREIGN KEY (cau_tra_loi_id) REFERENCES cau_tra_loi (id);

ALTER TABLE tin_nhan
  ADD CONSTRAINT fk_tin_nhan_hoi_thoai FOREIGN KEY (hoi_thoai_id) REFERENCES hoi_thoai (id);

ALTER TABLE bao_loi
  ADD CONSTRAINT fk_bao_loi_ctl FOREIGN KEY (cau_tra_loi_id) REFERENCES cau_tra_loi (id),
  ADD CONSTRAINT fk_bao_loi_xu_ly FOREIGN KEY (nguoi_xu_ly_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_bao_loi_bs_xu_ly FOREIGN KEY (bs_nguoi_xu_ly_id) REFERENCES nguoi_dung (id),
  ADD CONSTRAINT fk_bao_loi_lan_bi_bao FOREIGN KEY (cau_tra_loi_id, lan_bi_bao)
      REFERENCES ket_qua_cham (cau_tra_loi_id, lan),
  ADD CONSTRAINT fk_bao_loi_lan_ket_qua FOREIGN KEY (cau_tra_loi_id, lan_ket_qua)
      REFERENCES ket_qua_cham (cau_tra_loi_id, lan),
  ADD CONSTRAINT fk_bao_loi_bs_lan_ket_qua FOREIGN KEY (cau_tra_loi_id, bs_lan_ket_qua)
      REFERENCES ket_qua_cham (cau_tra_loi_id, lan);

-- ---------------------------------------------------------------------
-- TRIGGER (bao dam da_kiem_tra_audio luon = 0 khi tep_audio trong hoac bi doi)
-- ---------------------------------------------------------------------

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
-- VIEW (giup code truy van sach ma khong phai luu trung cot tren bang goc)
-- ---------------------------------------------------------------------

-- 1. ket qua cham hien hanh cua moi cau tra loi (liet ke tuong minh cot kem phien_ban_luu)
CREATE VIEW v_ket_qua_hien_hanh AS
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

-- 2. cau hoi kem cap_do_id va ky_nang ke thua tu ngu lieu cha (code SELECT thang, khong can COALESCE lap lai)
CREATE VIEW v_cau_hoi AS
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

-- 3. bai on va kiem tra cuoi thua kem thong tin thua va cap do
CREATE VIEW v_bai_on AS
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

-- 4. doi soat so du nang luong: so_du_luu phai bang so_du_tinh
CREATE VIEW v_doi_soat_nang_luong AS
SELECT n.id AS nguoi_dung_id,
       n.nang_luong AS so_du_luu,
       COALESCE(t.cong, 0) - COALESCE(c.tru, 0) + COALESCE(c.hoan, 0) AS so_du_tinh
FROM nguoi_dung n
LEFT JOIN (SELECT nguoi_dung_id, SUM(so_luong) AS cong
           FROM nhat_ky_thuong
           WHERE ly_do IN ('khoi_tao','nv_so_tay','nv_on_luyen','nv_thi_thu')
           GROUP BY nguoi_dung_id) t ON t.nguoi_dung_id = n.id
LEFT JOIN (SELECT l.nguoi_dung_id,
                  SUM(a.nang_luong_tru) AS tru,
                  SUM(a.nang_luong_hoan) AS hoan
           FROM cau_tra_loi a
           JOIN luot_lam l ON l.id = a.luot_lam_id
           GROUP BY l.nguoi_dung_id) c ON c.nguoi_dung_id = n.id;

-- ---------------------------------------------------------------------
-- DU LIEU DANH MUC BAN DAU
-- ---------------------------------------------------------------------

INSERT INTO vai_tro (id, ma, ten) VALUES
  (1, 'hoc_vien',   'Học viên'),
  (2, 'quan_tri',   'Quản trị viên'),
  (3, 'giang_vien', 'Giảng viên');

INSERT INTO cap_do (ma, ten, thu_tu, diem_toi_da_thi, diem_dat_thi, trang_thai) VALUES
  ('HSK1', 'HSK 1', 1, 200, 120, 'da_dang'),
  ('HSK2', 'HSK 2', 2, 200, 120, 'da_dang'),
  ('HSK3', 'HSK 3', 3, 300, 180, 'da_dang'),
  ('HSK4', 'HSK 4', 4, 300, 180, 'da_dang');

INSERT INTO nhom_kien_thuc (ma, ten, mo_ta) VALUES
  ('chao_hoi_giao_tiep', 'Chào hỏi và giao tiếp cơ bản', 'Lời chào, cảm ơn, xin lỗi, giới thiệu tên và quốc tịch'),
  ('gia_dinh_nghe_nghiep', 'Gia đình và nghề nghiệp', 'Đại từ nhân xưng, thành viên gia đình, nghề nghiệp cơ bản'),
  ('so_dem_luong_tu', 'Số đếm và lượng từ', 'Số đếm, lượng từ phổ biến (个, 本, 杯, 件, 张, 条...)'),
  ('thoi_gian_lich_hen', 'Thời gian và lịch hẹn', 'Giờ giấc, thứ ngày tháng năm, mốc thời gian và đổi lịch hẹn'),
  ('vi_tri_phuong_huong', 'Vị trí và phương hướng', 'Từ chỉ vị trí (上, 下, 里, 前, 后), động từ 在, đi lại'),
  ('phu_dinh_nghi_van', 'Phủ định và câu hỏi', 'Phân biệt 不 / 没 / 别, đại từ nghi vấn (什么, 谁, 哪儿, 怎么, 多少, 几)'),
  ('tro_tu_dong_thai', 'Trợ từ động thái 了 / 过 / 着', 'Biểu thị hành động hoàn thành, kinh nghiệm đã từng, trạng thái tiếp diễn'),
  ('bo_ngu', 'Bổ ngữ kết quả, xu hướng, khả năng', 'Bổ ngữ kết quả (完, 懂, 见), bổ ngữ xu hướng, bổ ngữ mức độ 得'),
  ('cau_so_sanh_nhan_manh', 'Câu so sánh và câu chữ 把 / 被', 'So sánh với 比 / 没有 / 一样, cấu trúc câu chữ 把 và câu bị động 被'),
  ('lien_tu_quan_he', 'Liên từ đối lập, nhân quả, giả thiết', '虽然…但是, 因为…所以, 如果…就, 不仅…而且, 无论…都');
