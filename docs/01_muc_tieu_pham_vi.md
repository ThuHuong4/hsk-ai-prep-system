# 01. Mục tiêu, Phạm vi và Hệ thống tương tự — Xianglingo

*(Tài liệu nguồn chuẩn phục vụ lập trình và ánh xạ sang **Chương 1: 1.1–1.4**, **Chương 2: 2.1, 2.3** và **Chương 5: 5.1** của quyển LVTN Khoa CNTT – ĐH Công nghệ Sài Gòn).*

---

## 1. Mục tiêu cốt lõi
- **Cá nhân hóa có bằng chứng kiểm chứng được**: Mọi đề xuất bài học, nhận định điểm mạnh/điểm yếu và ưu tiên ôn tập đều phải dẫn ngược về dữ liệu làm bài thật của chính học viên đó (câu trả lời, kết quả chấm, mức gợi ý đã mở, lịch sử hỏi trợ giảng AI) và giải thích rõ lý do.
- **Kết hợp quy tắc tất định với AI có kiểm soát**:
  - Các quyết định về phân quyền, mở khóa nội dung, điểm trắc nghiệm/sắp xếp, rẽ nhánh đánh giá đầu vào, xếp hạng bài đề xuất và cộng điểm kinh nghiệm (KN) do **code backend kiểm soát tất định**.
  - **AI (Xiang)** đảm nhận chấm câu dịch/viết theo tiêu chí ý chính, chữa lỗi câu viết kèm giải thích, sinh gợi ý có kiểm soát (không giải hộ), phân tích năng lực có trích dẫn câu bằng chứng và hỗ trợ Giảng viên tạo bản nháp câu hỏi.

## 2. Phạm vi thực hiện
- **Trình độ**: HSK 1 – HSK 4.
- **Vai trò người dùng (3 vai trò)**:
  1. **Học viên (`hoc_vien`)**: Đánh giá đầu vào 8 câu, Ôn luyện theo thửa/bài, Gợi ý 2 mức & Hỏi Xiang, Sổ tay câu sai, Thi thử tính giờ, Học liệu cẩm nang, Thống kê & Hồ sơ cá nhân. *(Khách chưa đăng nhập chỉ được xem lộ trình mở sẵn và học thử bài đầu tiên, không ghi CSDL).*
  2. **Giảng viên (`giang_vien`)**: Quản lý cấp độ, từ vựng, ngân hàng câu hỏi (tự soạn & soạn nháp với AI), lộ trình bài ôn, đề thi thử, học liệu, chấm phúc khảo bài viết và xử lý báo lỗi nội dung/chấm điểm.
  3. **Quản trị viên (`quan_tri`)**: Quản lý tài khoản, khóa/mở khóa, phân quyền, mời Giảng viên và tra cứu nhật ký quản trị.
- **Giới hạn ngoài phạm vi**: Không triển khai kỹ năng Nói (thu âm chấm phát âm); không giám sát phòng thi bằng webcam.

## 3. Khảo sát hệ thống tương tự (Ánh xạ mục `2.1` LVTN)

| Hệ thống | Điểm mạnh tham khảo | Hạn chế đối với bài toán luyện HSK cá nhân hóa | Cách Xianglingo kế thừa & khắc phục |
|---|---|---|---|
| **Duolingo** | Bản đồ bài học trực quan theo chặng; ghép mảnh câu (`Sentence Builder`); duy trì động lực qua chuỗi ngày và năng lượng. | Ít giải thích ngữ pháp chuyên sâu; đề xuất ôn tập đóng kín, không chỉ rõ nhóm lỗi ngữ pháp HSK hay lý do chọn bài. | Kế thừa bản đồ thửa/ô, câu bấm mảnh, chuỗi ngày & KN; bổ sung hồ sơ năng lực `kỹ năng × nhóm kiến thức` có lý do tường minh. |
| **SuperChinese** | Có kiểm tra xếp lớp đầu vào và lộ trình bám sát HSK. | Phản hồi câu viết/dịch và trợ giảng hỏi đáp tiếng Việt hạn chế; giảng viên không thể tự mở rộng ngân hàng câu hỏi riêng. | Xây dựng bài đánh giá đầu vào 8 câu thích ứng (rẽ nhánh thực tế) và phân hệ để Giảng viên chủ động biên soạn, duyệt học liệu. |
| **WriteMate AI / Cambridge Write & Improve** | Quy trình luyện viết/dịch chủ động: gợi ý khung cấu trúc trước khi viết, chấm theo tiêu chí (rubric), sửa câu giữ nguyên ý người học kèm giải thích lý do sai. | Công cụ viết tiếng Anh/AI chung dễ viết hộ toàn bài nếu người học hỏi thẳng; không khóa từ vựng theo cấp HSK 1–4; không nối lỗi sai vào lộ trình mở khóa. | Kế thừa luồng **Gợi ý 2 mức (không viết hộ) → Chấm theo tiêu chí → Trả `nhan_xet`, `cau_sua`, `ly_do_sua`**, đồng thời gắn nhóm lỗi vào Sổ tay và lộ trình HSK. |

## 4. Công nghệ sử dụng (Ánh xạ mục `2.3` LVTN)
- **Backend**: Python 3, FastAPI, SQLAlchemy Core (`text()` truy vấn tham số hóa, không phụ thuộc ORM ngầm), PyJWT, Google Auth.
- **Cơ sở dữ liệu**: MySQL 8.0+ / 8.4 (`utf8mb4`, `InnoDB`, ràng buộc `CHECK`, khóa ngoại kép, chỉ mục biểu thức và `VIEW`).
- **Tích hợp AI**: OpenAI SDK (tương thích OpenAI / Gemini endpoint qua cấu hình `.env`), kiểm soát timeout và kiểm chứng JSON đầu ra tại backend.
- **Frontend**: React 18, Vite, React Router v6, CSS thuần theo biến thiết kế (`tokens.css`).

## 5. Bảng kết quả cần đạt & Tiêu chí đánh giá (Ánh xạ mục `1.4` và `5.1` LVTN)

| Mã mục tiêu | Nội dung cần đạt | Loại | Tiêu chí đánh giá nghiệm thu |
|---|---|---|---|
| **MT01** | Đánh giá trình độ đầu vào 8 câu thích ứng | Chức năng | Học viên mới vào thẳng bài 8 câu (không qua khảo sát tích chọn); rẽ nhánh đúng 4.096 tổ hợp câu 1–6; xử lý được lỗi audio và thiếu câu dự phòng (`AT01–AT11, AT31–AT38, AT44, AT46–AT47`). |
| **MT02** | Hồ sơ năng lực & "Bài phù hợp với bạn hôm nay" | Chức năng | Tính theo `kỹ năng × nhóm kiến thức` từ dữ liệu thật; hàm chọn bài là hàm thuần kiểm thử được; học viên mẫu A–D nhận lý do và bằng chứng riêng chính xác (`AT12, AT39–AT40, AT48–AT50, AT53`). |
| **MT03** | Gợi ý 2 mức & Hỏi Xiang có kiểm soát | Chức năng | Không gửi đáp án xuống trình duyệt trước khi được xem; không lộ đáp án khi bấm gợi ý hoặc hỏi Xiang trước khi kiểm tra; ghi nhận tách bạch tự làm đúng và làm đúng nhờ hỗ trợ (`AT14–AT16, AT45`). |
| **MT04** | Chấm & chữa câu Dịch / Viết bằng AI | Chức năng | Chấm theo tiêu chí ý chính và ngưỡng đạt (`nguong_dat`), trả về nhận xét, câu sửa gợi ý và lý do sửa; thử lại dùng lại điểm hợp lệ (`AT07, AT10, AT36`). |
| **MT05** | Lộ trình mở khóa 3 tầng & Sổ tay cá nhân hóa | Chức năng | Hiển thị rõ điều kiện mở, tiến độ hiện tại và phần còn thiếu; chặn vượt khóa qua API; Sổ tay ưu tiên nhóm lỗi lặp lại và xét mức hỗ trợ (`AT13, AT25`). |
| **MT06** | Thi thử cấp đề ngẫu nhiên & thao tác phòng thi | Chức năng | Không lộ danh sách đề trước khi thi; chặn API chọn đề cũ; chặn nộp tay khi còn câu trống; hết giờ tự nộp; hỗ trợ phím tắt an toàn (`AT17–AT23, AT41–AT43`). |
| **MT07** | Giảng viên soạn câu hỏi nháp với AI | Chức năng | AI chỉ sinh bản nháp có gắn nguồn `soan_voi_ai`; câu Nghe bắt buộc có file audio thật đã kiểm tra mới xuất bản được (`AT24–AT25`). |
| **MT08** | Minh bạch chuỗi ngày học & điểm KN | Chức năng | Chuỗi ngày tính theo múi giờ máy chủ `+07:00`, chống cộng trùng; hiển thị rõ số KN nhận, lý do và tổng KN mới (`AT26–AT28`). |
| **MT09** | Bảo mật phân quyền, toàn vẹn dữ liệu & chịu lỗi AI | Phi chức năng | Chặn đọc chéo hồ sơ/kết quả giữa các học viên (`AT29, AT51`); không giữ giao dịch CSDL mở khi chờ AI; AI ngừng hoạt động thì các chức năng không cần AI vẫn chạy bình thường (`AT30, AT35, AT52`). |
