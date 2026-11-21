-- Đổi tên đề HSK 1 mã H10000 thành "HSK 1 – Đề 1" (mọi phiên bản). Chạy một lần trong phpMyAdmin, CSDL xianglingo.
UPDATE bo_de SET ten = 'HSK 1 – Đề 1'
WHERE loai = 'de_thi' AND ten LIKE '%Đề mẫu H10000%';
