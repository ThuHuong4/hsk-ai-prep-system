-- Chạy MỘT lần trong phpMyAdmin (chọn CSDL xianglingo) TRƯỚC khi dùng nút "Thêm giảng viên".
-- Chỉ thêm giá trị 'tao_tai_khoan' vào ENUM; không thêm bảng/cột, dữ liệu cũ giữ nguyên.
ALTER TABLE nhat_ky_quan_tri
  MODIFY hanh_dong ENUM('khoa','mo_khoa','doi_vai_tro','tao_tai_khoan') NOT NULL;
