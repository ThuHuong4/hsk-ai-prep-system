# 03. Thiết kế Cơ sở dữ liệu (24 bảng & 4 View) — Chuẩn 3NF

*(Tài liệu đặc tả CSDL đối chiếu trực tiếp với [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql) và ánh xạ sang **Chương 3: 3.1 Mô hình dữ liệu** của quyển LVTN).*

---

## 1. Tổng quan kiến trúc & Chuẩn hóa 3NF

- **Hệ quản trị**: MySQL 8.0.16+ / 8.4 (`InnoDB`, bảng mã `utf8mb4`, múi giờ phiên `+07:00`).
- **Quy mô lược đồ**: **24 bảng vật lý** (gồm **19 bảng gốc** và **5 bảng mở rộng**) cùng **4 View** và **2 Trigger**.
- **Mức chuẩn hóa cao nhất của hệ thống — Chuẩn 3 (`3NF` — Third Normal Form)**:
  1. **Đạt chuẩn 1NF**: Toàn bộ 24 bảng đều có khóa chính (`PRIMARY KEY`), mọi cột đều mang giá trị nguyên tố (atomic), không chứa danh sách đa trị hay nhóm cột lặp.
  2. **Đạt chuẩn 2NF**: Ở các bảng dùng khóa chính ghép (`bo_de_cau_hoi`, `so_tay`, `nhan_dinh_dau_vao`, `nhan_dinh_bang_chung`), mọi thuộc tính không khóa đều phụ thuộc hàm đầy đủ vào toàn bộ khóa chính, không phụ thuộc bộ phận vào một phần của khóa.
  3. **Đạt chuẩn 3NF**: Toàn bộ 24 bảng không tồn tại phụ thuộc hàm bắc cầu giữa các thuộc tính không khóa ($PK \to A \not\to B$); không lưu dư thừa các trường tổng hợp như tổng điểm lượt thi, số lần sai trong Sổ tay, chuỗi ngày học hay tổng điểm KN.
  4. **Hai điểm thiết kế thực tế ở mức 3NF có đối soát toàn vẹn**:
     - `nguoi_dung.nang_luong (0..10)`: Lưu số dư hiện hành trên dòng người dùng để khóa dòng nguyên tử (`SELECT ... FOR UPDATE`) và kiểm tra tức thì bằng `CHECK (nang_luong BETWEEN 0 AND 10)` theo trần cấp HSK (`5 → 6 → 8 → 10`), đồng thời đối soát 2 chiều chặt chẽ qua View `v_doi_soat_nang_luong`.
     - `cau_tra_loi.cap_tham_do_id`: Chỉ ghi giá trị ở lượt `danh_gia_dau_vao` và để `NULL` ở các lượt khác thay vì tách bảng phụ `1–1` làm phức tạp truy vấn đọc câu trả lời.
  5. **Năm nguyên tắc chống lưu trùng dữ liệu dẫn xuất đã áp dụng**:
     - Dùng lại `nguoi_dung.ks_cap_muc_tieu_id` làm cấp HSK mục tiêu của học viên (không sinh thêm cột mục tiêu trùng nghĩa).
     - Ghi `cau_tra_loi.muc_goi_y TINYINT (0, 1, 2)` cho mức gợi ý mở trước khi xác nhận; việc Hỏi Xiang suy ra từ `hoi_thoai (cau_tra_loi_id)` + `tin_nhan`; việc xem lời giải sau khi chấm tách riêng ở `xem_loi_giai_luc`.
     - Lưu `ket_qua_cham.phien_ban_luu` (bản chụp `cau_tra_loi.phien_ban_luu` lúc chấm) để xét tái sử dụng điểm AI khi thử lại (`AT36`) mà không cần cột mã băm dẫn xuất.
     - Không thêm `bai_de_xuat_id` trên `ket_qua_dau_vao`; mọi đề xuất bài ôn và tài liệu sau lượt làm lưu thống nhất vào `goi_y_lo_trinh`.
     - Không lưu cờ boolean `gioi_han_du_lieu` dẫn xuất trên `ket_qua_dau_vao` (suy ra từ số câu `bo_qua` / `loi_ky_thuat` và chênh lệch `cap_tham_do_id <> v_cau_hoi.cap_do_id`).

---

## 2. Danh mục 24 bảng theo 4 phân nhóm (Chuẩn 3NF)

### 2.1. Nhóm Tài khoản & Quản trị (4 bảng)
1. **`vai_tro`** *(3NF)*: `id (PK)`, `ma (UQ)`, `ten` — 3 vai trò cố định (`hoc_vien`, `quan_tri`, `giang_vien`).
2. **`cap_do`** *(3NF)*: `id (PK)`, `ma (UQ)`, `ten`, `thu_tu (UQ)`, `diem_toi_da_thi`, `diem_dat_thi`, `trang_thai`, `nguoi_tao_id (FK → nguoi_dung)`.
3. **`nguoi_dung`** *(3NF)*: Thông tin đăng nhập, xác minh email, `phien_ban_phien`, mục tiêu học tập (`ks_cap_muc_tieu_id FK → cap_do`, `ks_phut_moi_ngay`), `nang_luong (0..10, mở rộng trần 5 → 6 → 8 → 10 theo cấp HSK)`.
4. **`nhat_ky_quan_tri`** *(3NF)*: Lịch sử khóa/mở khóa, đổi vai trò và `tao_tai_khoan` Giảng viên.

### 2.2. Nhóm Ngân hàng Nội dung & Học liệu (7 bảng: 6 cũ + 1 mới)
5. **`nhom_kien_thuc`** *(MỚI #1 – 3NF)*: `id (PK)`, `ma (UQ)`, `ten`, `mo_ta`, `trang_thai`, `nguoi_tao_id (FK)`. Độc lập với `ky_nang` để tạo lưới `kỹ năng × nhóm kiến thức` mà không gây phụ thuộc bắc cầu trên `cau_hoi`.
6. **`tai_lieu`** *(3NF)*: Học liệu PDF/hình/âm thanh có quản lý phiên bản `(ma_goc_id, phien_ban)`.
7. **`tu_vung`** *(3NF)*: Từ điển HSK phân biệt thanh điệu (`utf8mb4_0900_as_cs`), gắn `cap_do_id (FK)`.
8. **`cau_hoi`** *(3NF)*: Quản lý câu hỏi và ngữ liệu cha theo phiên bản `(ma_goc_id, phien_ban)`.
   - `dang`: `'ngu_lieu','chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo','dich_cau'`.
   - Liên kết: `cau_cha_id (FK)`, `cap_do_id (FK)`, `nhom_kien_thuc_id (FK → nhom_kien_thuc)`, `tu_vung_id (FK)`.
   - **6 cột mở rộng trên `cau_hoi`**: `nhom_kien_thuc_id`, `da_kiem_tra_audio`, `goi_y_2`, `nguon_noi_dung ('tu_soan','soan_voi_ai','nguon_duoc_phep', NULL cho câu cũ)`, `nguoi_duyet_id (FK)`, `duyet_luc`.
   - Bảo vệ cờ `da_kiem_tra_audio`: ràng buộc `ck_cau_hoi_audio_duyet` kết hợp **2 Trigger MySQL** (`trg_cau_hoi_bi_audio`, `trg_cau_hoi_bu_audio`) tự đặt về `0` khi `tep_audio` trống hoặc bị thay đổi.
   - Ràng buộc `ck_cau_hoi_diem`: áp dụng `diem_toi_da` và `nguong_dat` cho cả `'viet_mo'` và `'dich_cau'`.
9. **`phuong_an`** *(3NF)*: Lựa chọn trắc nghiệm / mảnh câu (`vai_tro = 'lua_chon'`) và danh sách đáp án/trật tự chấp nhận (`vai_tro = 'dap_an_chap_nhan'`).
10. **`bo_de`** *(3NF)*: Thửa (`thua`), Bài ôn (`bai`), Kiểm tra cuối thửa (`cuoi_thua`), Đề thi thử (`de_thi`) có quản lý phiên bản.
11. **`bo_de_cau_hoi`** *(3NF)*: Bảng nối bộ đề – phiên bản câu hỏi theo `thu_tu`, `phan`, `la_cau_vi_du`.

### 2.3. Nhóm Học tập, Đánh giá & Cá nhân hóa (10 bảng: 6 cũ + 4 mới)
12. **`luot_lam`** *(3NF)*: Phiên học/thi/đánh giá của học viên (`bo_de_id` hoặc `loai_boc_cau`). Ràng buộc `ck_luot_lam_pham_vi` cho phép `danh_gia_dau_vao` để `cap_do_id = NULL, ky_nang = NULL`.
13. **`cau_tra_loi`** *(3NF)*: Từng vị trí câu trong lượt làm (`uq_ctl_cau`, `uq_ctl_thu_tu`).
    - Lưu đủ 3 chiều dữ liệu học: `trang_thai_thao_tac ('chua_thao_tac','da_tra_loi','bo_qua','loi_ky_thuat')`, `muc_goi_y (0,1,2)`, `xem_loi_giai_luc`, `thoi_gian_lam_giay`, `cap_tham_do_id (FK → cap_do)`.
14. **`ket_qua_cham`** *(3NF)*: Lịch sử các lần chấm (`code`, `ai`, `giang_vien`), lưu `phien_ban_luu`, `diem`, `nhan_xet`, `cau_sua`, `ly_do_sua`.
15. **`ket_qua_dau_vao`** *(MỚI #2 – 3NF)*: Quan hệ `1–1` với `luot_lam` (`luot_lam_id PK, FK`), lưu `trang_thai_phan_tich ('chua','dang','xong','loi')`, `bat_dau_phan_tich_luc`, `hoan_tat_phan_tich_luc`, `cap_de_xuat_id (FK → cap_do)`, `ghi_chu_gioi_han`.
16. **`nhan_dinh_dau_vao`** *(MỚI #3 – 3NF)*: `PRIMARY KEY (luot_lam_id, thu_tu)`, lưu `ky_nang (ENUM, NULL cho nhận xét tổng quan)`, `nhom_kien_thuc_id (FK → nhom_kien_thuc, NULL)`, `loai ('diem_manh','diem_yeu','nhan_xet')`, `noi_dung`.
17. **`nhan_dinh_bang_chung`** *(MỚI #4 – 3NF)*: `PRIMARY KEY (luot_lam_id, thu_tu_nhan_dinh, thu_tu_cau)` với **2 khóa ngoại kép**:
    - `(luot_lam_id, thu_tu_nhan_dinh) → nhan_dinh_dau_vao (luot_lam_id, thu_tu)`
    - `(luot_lam_id, thu_tu_cau) → cau_tra_loi (luot_lam_id, thu_tu)`
    - Khóa cứng ở tầng vật lý: câu bằng chứng bắt buộc thuộc đúng phiên đánh giá đó (`AT37, AT52`).
18. **`lich_su_thay_cau`** *(MỚI #5 – 3NF)*: Lưu vết đổi câu tại chỗ khi gặp lỗi kỹ thuật (`luot_lam_id`, `thu_tu_vi_tri`, `cau_hoi_cu_id`, `cau_hoi_moi_id`, `ly_do ENUM('loi_audio','loi_hinh_anh','loi_hien_thi','loi_noi_dung')`).
19. **`so_tay`** *(3NF)*: Trạng thái củng cố theo câu gốc `(nguoi_dung_id, cau_hoi_goc_id)`.
20. **`nhat_ky_thuong`** *(3NF)*: Sổ cái biến động năng lượng (`khoi_tao`, `nv_so_tay`, `nv_on_luyen`, `nv_thi_thu`, `hoi_ngay`, `thang_cap_nl`, `hoi_so_tay`, `thuong_cuoi_thua`) và điểm KN (`kn_*`), gắn `luot_lam_id (FK → luot_lam)`.
21. **`goi_y_lo_trinh`** *(3NF)*: Các bài ôn / tài liệu đề xuất gắn với `luot_lam_id` (dùng chung cho Đánh giá đầu vào và Thi thử), có `nhom_kien_thuc_id (FK)` và `dang_cau`.

### 2.4. Nhóm Tương tác & Phản hồi (3 bảng)
22. **`hoi_thoai`** *(3NF)*: Hội thoại Hỏi Xiang chung (`nguoi_dung_id`) hoặc gắn 1–1 với câu trả lời (`cau_tra_loi_id UQ, FK`).
23. **`tin_nhan`** *(3NF)*: Tin nhắn của `hoc_vien` và `xiang`, có `khoa_chong_lap` và chỉ mục chặn xử lý song song.
24. **`bao_loi`** *(3NF)*: Báo lỗi nội dung câu hỏi hoặc khiếu nại chấm sai (kèm phúc khảo bổ sung `bs_*`).

---

## 3. Danh sách 4 View hỗ trợ truy vấn sạch & đối soát 3NF

1. **`v_ket_qua_hien_hanh`**: Trả về lần chấm `hoan_tat` mới nhất (`MAX(lan)`) của mỗi `cau_tra_loi_id`.
2. **`v_cau_hoi`**: Kế thừa sẵn `cap_do_id`, `ky_nang`, `tep_audio_hieu_luc` và các cờ mục đích từ câu ngữ liệu cha cho câu con — giữ bảng `cau_hoi` đạt chuẩn 3NF nhưng giúp tầng dịch vụ `SELECT` phẳng gọn gàng.
3. **`v_bai_on`**: Kết hợp bài ôn / kiểm tra cuối thửa với thông tin thửa, `cap_do_id`, `ky_nang`.
4. **`v_doi_soat_nang_luong`**: Đối soát `nguoi_dung.nang_luong` với tổng phát sinh thực tế trên `nhat_ky_thuong` và `cau_tra_loi` (`so_du_luu = so_du_tinh`).
