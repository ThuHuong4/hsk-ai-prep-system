-- =====================================================================
-- Script DU LIEU TUY CHON (Tach rieng khoi script nang cap cau truc CSDL)
--
-- Khong bat buoc chay khi nang cap schema. Nguoi quan tri / Giang vien xem lai
-- va chi chay khoi nao minh dong y.
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '+07:00';

-- ---------------------------------------------------------------------
-- KHOI A: 10 nhom kien thuc goi y ban dau (Giang vien xem lai / chinh sua truoc khi chay)
-- ---------------------------------------------------------------------
INSERT IGNORE INTO nhom_kien_thuc (ma, ten, mo_ta) VALUES
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

-- ---------------------------------------------------------------------
-- KHOI B (Phan 1 cu - Tuy chon): Bo sung dong khoi_tao nang luong cho tai khoan
--   duoc tao qua chuc nang Moi Giang vien (vd id=6 dang co nang_luong=5 nhung thieu
--   dong khoi_tao trong nhat_ky_thuong lam lech v_doi_soat_nang_luong).
--   Bo dau comment /* ... */ ben duoi neu ban muon chay khoi nay.
-- ---------------------------------------------------------------------
/*
INSERT IGNORE INTO nhat_ky_thuong (nguoi_dung_id, ly_do, so_luong, tao_luc)
SELECT n.id, 'khoi_tao', n.nang_luong, n.tao_luc
FROM nguoi_dung n
WHERE n.nang_luong > 0
  AND NOT EXISTS (
    SELECT 1 FROM nhat_ky_thuong t
    WHERE t.nguoi_dung_id = n.id AND t.ly_do = 'khoi_tao'
  );
*/

-- ---------------------------------------------------------------------
-- KHOI C (Phan 4 cu - Tuy chon): Tat co dung_on_luyen tren cac cau Nghe cua de thi thu
--   khong co tep_audio rieng (tep_audio IS NULL) va khong nam trong bai On luyen nao.
--   Bo dau comment /* ... */ ben duoi neu ban muon chay khoi nay.
-- ---------------------------------------------------------------------
/*
UPDATE cau_hoi q
SET q.dung_on_luyen = 0
WHERE q.ky_nang = 'nghe'
  AND q.tep_audio IS NULL
  AND q.dung_thi_thu = 1
  AND NOT EXISTS (
    SELECT 1
    FROM bo_de_cau_hoi i
    JOIN bo_de b ON b.id = i.bo_de_id
    WHERE i.cau_hoi_id = q.id AND b.loai IN ('bai', 'cuoi_thua')
  );
*/
