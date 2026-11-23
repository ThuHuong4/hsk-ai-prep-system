# 04. Chiến lược & Kịch bản Kiểm thử Nghiệm thu — Xianglingo

*(Tài liệu kiểm thử đối chiếu trực tiếp với code trong `backend/tests/` và ánh xạ sang **Chương 4: Thử nghiệm (4.1–4.3)** của quyển LVTN).*

---

## 1. Tổ chức kiểm thử 3 tầng (Chạy trên CSDL kiểm thử riêng)

1. **Tầng 1 — Kiểm thử đơn vị hàm thuần (`backend/tests/unit/`)**:
   - Không kết nối CSDL, không gọi mạng OpenAI; tốc độ chạy tính bằng mili-giây.
   - Kiểm tra vét cạn **4.096 tổ hợp** trạng thái (`da_tra_loi` đúng, `da_tra_loi` sai, `bo_qua`, `loi_ky_thuat`) của câu 1–6 bài đánh giá đầu vào + rẽ nhánh cấp câu 7–8 + thứ tự chọn cấp dự phòng khi thiếu câu (`AT46, AT47`).
   - Kiểm tra hàm thuần chọn *"Bài phù hợp với bạn hôm nay"* trên hàng chục cấu hình hồ sơ năng lực, ngưỡng `≥ 2 câu sai` (`AT39`), mức dùng gợi ý và phá hòa.
   - Kiểm tra bộ lọc hậu kiểm đầu ra AI (chặn lộ đáp án trước khi chấm, loại nhận định dẫn sai câu bằng chứng – `AT14, AT15, AT52`).
2. **Tầng 2 — Kiểm thử tích hợp API & Dữ liệu mẫu (`backend/tests/integration/`)**:
   - Chạy trên CSDL kiểm thử tách biệt (`xianglingo_test`), nạp dữ liệu mẫu và **4 học viên mẫu A–D** để xuất bảng minh chứng tự động cho báo cáo LVTN (`AT48, AT49`).
   - Kiểm tra phân quyền chéo giữa các tài khoản (`AT29, AT51`), vượt khóa API (`AT13, AT42`), chống nộp trùng / cộng trùng KN & chuỗi ngày (`AT21, AT27`), giả lập AI lỗi / timeout / trả sai định dạng (`AT10, AT30, AT35, AT36`).
3. **Tầng 3 — Kịch bản kiểm thử giao diện & Demo (UI / E2E)**:
   - Kiểm tra F5 giữ trạng thái (`AT05, AT18`), lỗi audio & đổi câu tại chỗ (`AT06, AT33, AT44`), phím tắt phòng thi & bảo vệ ô nhập chữ (`AT22, AT43`), chuyển tài khoản SPA không rò state (`AT29`).

---

## 2. Bộ 4 Học viên mẫu chứng minh cá nhân hóa (`AT48`)

| Học viên mẫu | Hồ sơ dữ liệu khởi tạo trên CSDL kiểm thử | Kết quả đề xuất & Lý do mong đợi |
|---|---|---|
| **Học viên A** | Đã mở HSK 2, sai lặp lại `≥ 3` câu kỹ năng **Nghe** (nhóm `thoi_gian_lich_hen`) | Ưu tiên bài ôn Nghe HSK 2 có nhóm `thoi_gian_lich_hen`; lý do đếm đúng số câu sai của A. |
| **Học viên B** | Đã mở HSK 2, Nghe tốt, sai lặp lại nhóm **`tro_tu_dong_thai` (`了 / 过`)** ở Đọc/Từ vựng | Ưu tiên bài ôn có nhóm `了 / 过`; lý do dẫn đúng số liệu lỗi của B (khác đề xuất của A). |
| **Học viên C** | Đã mở HSK 2, làm đúng nhưng dùng `muc_goi_y` / Hỏi Xiang ở nhiều câu trong nhóm | Ưu tiên củng cố lại bài thuộc nhóm đó (Ưu tiên 3); lý do nêu rõ số câu cần hỗ trợ của C. |
| **Học viên D** | Tài khoản mới chưa có lịch sử câu trả lời (hoặc vừa bỏ qua mục tiêu) | Đề xuất bài mở đầu trong phạm vi đã mở (Ưu tiên 5), kèm thông báo rõ dữ liệu năng lực còn ít. |

---

## 3. Danh mục 53 Tiêu chí Nghiệm thu (`AT01` – `AT53`)

*(Chỉ đánh dấu **Đã đạt** sau khi có kết quả chạy kiểm thử thực tế).*

| Mã | Tình huống kiểm thử | Kết quả mong đợi |
|---|---|---|
| **AT01** | Học viên mới mở ứng dụng lần đầu | Vào thẳng bài đánh giá 8 câu đúng cấu trúc; không qua bước khảo sát tích chọn cũ. |
| **AT02** | Chọn "Không biết / Bỏ qua" trong đánh giá | Lưu `trang_thai_thao_tac = 'bo_qua'`; qua câu tiếp không cần đáp án giả. |
| **AT03** | Còn câu `chua_thao_tac` | Phân biệt với `bo_qua`; chặn nộp phiên đánh giá. |
| **AT04** | Cả 8 vị trí đều thuộc `da_tra_loi`, `bo_qua` hoặc `loi_ky_thuat` | Cho phép nộp bài đánh giá đầu vào. |
| **AT05** | Tải lại trang (F5) khi đang đánh giá | Giữ nguyên câu hiện tại và các câu trả lời đã lưu; không đổi bộ câu. |
| **AT06** | Không phát được audio câu 5 hoặc 6 | Cho thử lại hoặc đổi câu cùng dạng/kỹ năng/cấp; không tính là `bo_qua` hay sai kiến thức. |
| **AT07** | Câu dịch (câu 7) khác câu mẫu nhưng đúng ý chính | AI chấm theo `tieu_chi_mo_ta` và `nguong_dat`, không so khớp chuỗi cứng; lưu nhận xét & câu sửa. |
| **AT08** | Câu sắp xếp từ (câu 8) có nhiều trật tự hợp lệ | Backend chấp nhận mọi trật tự nằm trong `dap_an_chap_nhan`. |
| **AT09** | Vừa nộp bài đánh giá đầu vào | Màn hình "Xiang đang phân tích…" phản ánh đúng `ket_qua_dau_vao.trang_thai_phan_tich` từ backend. |
| **AT10** | AI báo lỗi hoặc gửi 2 yêu cầu phân tích trùng lúc | Giữ nguyên bài làm, chặn chạy trùng, hiện nút Thử lại, không sinh điểm/nhận định giả. |
| **AT11** | Bỏ qua nhiều câu trong bài đánh giá | Ghi rõ giới hạn dữ liệu trong kết quả, không khẳng định đạt cấp. |
| **AT12** | Hai học viên cùng cấp nhưng nhóm lỗi khác nhau | Nhận đề xuất bài và lý do khác nhau tương ứng dữ liệu riêng khi ngân hàng có bài phân biệt. |
| **AT13** | Truy cập nội dung đang bị khóa (UI & gọi thẳng API) | Giao diện hiện rõ điều kiện mở, tiến độ hiện tại, phần còn thiếu; API học viên và API khách đều chặn vượt khóa. |
| **AT14** | Bấm Gợi ý lần 1 và lần 2 trong bài ôn | Mở tuần tự mức 1 rồi mức 2 (`muc_goi_y = 1, 2`), không lộ đáp án hay lời giải trọn vẹn. |
| **AT15** | Xin đáp án trực tiếp qua Hỏi Xiang trước khi kiểm tra | Backend không truyền đáp án vào ngữ cảnh AI; Xiang từ chối giải hộ và chỉ hướng dẫn cách suy nghĩ. |
| **AT16** | Trả lời đúng sau khi mở gợi ý hoặc Hỏi Xiang | Ghi nhận làm đúng nhờ hỗ trợ trong hồ sơ; không trừ điểm câu và không đổi công thức KN. |
| **AT17** | Bắt đầu Thi thử theo cấp HSK | Không hiện danh sách đề trước khi thi; cấp ngẫu nhiên đề hợp lệ đúng cấp, ưu tiên đề chưa làm. |
| **AT18** | F5 hoặc gọi lại bắt đầu thi khi đang có phiên chưa hết giờ | Trả lại đúng đề đang thi và thời gian còn lại thực tế; không đổi đề, không đặt lại giờ. |
| **AT19** | Còn câu tính điểm bỏ trống và bấm Nộp bài tay | Chặn nộp và chỉ rõ danh sách số câu còn thiếu. |
| **AT20** | Hết giờ làm bài Thi thử khi còn câu trống | Tự động nộp phần đã làm (`ly_do_nop = 'het_gio'`), không bị chặn bởi `AT19`. |
| **AT21** | Bấm nộp tay trùng thời điểm hết giờ | Khóa dòng CSDL bảo đảm chỉ ghi nhận 1 lần nộp và tối đa 1 lần tính thưởng hợp lệ. |
| **AT22** | Gõ phím mũi tên / số / chữ trong ô nhập câu Viết | Không bị phím tắt điều hướng chiếm quyền nhập hoặc di chuyển con trỏ chữ. |
| **AT23** | Gợi ý và Hỏi Xiang trong phòng Thi thử (và kiểm tra mở khóa) | Bị khóa hoàn toàn khi đang làm bài; chỉ mở giải thích và Hỏi Xiang sau khi đã nộp. |
| **AT24** | Giảng viên dùng AI sinh câu hỏi nháp thiếu thành phần | Lưu ở trạng thái `nhap` (`nguon_noi_dung = 'soan_voi_ai'`), báo rõ thành phần thiếu, chặn xuất bản. |
| **AT25** | Giảng viên sửa câu hỏi đã đăng / đã có lượt làm | Tạo phiên bản mới (`phien_ban + 1`), lịch sử lượt làm cũ vẫn trỏ đúng phiên bản cũ. |
| **AT26** | Đăng nhập, mở rồi bỏ bài, hoặc nộp bài không trả lời câu nào | Không tăng chuỗi ngày học; chỉ tăng tối đa 1 lần/ngày khi hoàn thành lượt có ít nhất 1 câu trả lời. |
| **AT27** | F5 hoặc gửi lặp yêu cầu hoàn thành bài | Không cộng trùng chuỗi ngày học, năng lượng hoặc điểm KN. |
| **AT28** | Xem kết quả KN sau khi hoàn thành lượt học | Hiển thị đúng số KN nhận được, lý do cộng (hoặc lý do `0 KN`) và tổng KN mới từ backend. |
| **AT29** | Đăng xuất học viên A rồi đăng nhập học viên B trên cùng tab | Xóa sạch state phiên trước; không hiển thị nhầm thống kê, hồ sơ hay đề xuất của người trước. |
| **AT30** | Dịch vụ AI tắt hoặc mất kết nối | Trắc nghiệm, sắp xếp câu, chọn bài hôm nay, mở khóa, chuỗi ngày, KN vẫn hoạt động bình thường. |
| **AT31** | Học viên đã có tiến độ học và có phiên đánh giá tự nguyện dở | Không bị tự động đẩy vào bài đánh giá; chỉ tiếp tục khi học viên tự bấm. |
| **AT32** | Tài khoản Giảng viên hoặc Quản trị viên đăng nhập | Đi thẳng vào phân hệ tương ứng, không bị chuyển hướng sang đánh giá đầu vào. |
| **AT33** | Đổi câu do lỗi audio ở câu 5 hoặc 6 | Câu mới cùng dạng, kỹ năng, cấp, không trùng câu đã dùng (`lich_su_thay_cau`); tổng giữ nguyên 8 vị trí. |
| **AT34** | Câu đầu cặp (1, 3, 5) bị `loi_ky_thuat` | Câu kế giữ nguyên ở cấp đang thăm dò (HSK 2), không rẽ xuống nhánh câu sai (HSK 1). |
| **AT35** | Phân tích AI quá thời hạn xử lý (`> 60s`) | Tự thoát trạng thái `dang` sang `loi` để học viên bấm Thử lại được. |
| **AT36** | Bấm Thử lại phân tích sau khi AI lỗi | Tái sử dụng kết quả chấm câu 7 nếu `ket_qua_cham.phien_ban_luu` khớp `cau_tra_loi.phien_ban_luu`; khác thì chấm lại. |
| **AT37** | Xem nhận định năng lực ở kết quả đánh giá đầu vào | Mỗi nhận định liên kết hợp lệ tới ít nhất 1 câu bằng chứng thuộc chính phiên đó. |
| **AT38** | Câu có `trang_thai_thao_tac = 'loi_ky_thuat'` hoặc chưa chấm | Không tính là câu sai, không đưa vào Sổ tay và không làm giảm tỷ lệ năng lực. |
| **AT39** | Mới chỉ sai 1 câu đơn lẻ trong một nhóm kiến thức | Chưa đủ ngưỡng kết luận yếu cả nhóm kiến thức đó. |
| **AT40** | Học viên chưa chọn mục tiêu HSK hoặc chưa có lịch sử làm bài | Vẫn đề xuất bài hợp lệ trong phạm vi đã mở kèm ghi chú rõ giới hạn dữ liệu. |
| **AT41** | Đồng hồ Thi thử chạm 0 | Tự động nộp ngay, không bật hộp thoại chờ xác nhận. |
| **AT42** | Gọi trực tiếp API xem danh sách đề / bắt đầu theo ID đề cũ | Bị từ chối; học viên không tự chỉ định được mã đề thi thử. |
| **AT43** | Nhấn phím mũi tên ở biên giới hạn điều hướng phần thi | Không chuyển lùi/tiến sang phần thi bị khóa điều hướng. |
| **AT44** | Lỗi audio không còn câu thay thế trong đánh giá đầu vào | Ghi `loi_ky_thuat`, vẫn nộp được kết quả giới hạn và nêu rõ kỹ năng Nghe chưa đánh giá đủ. |
| **AT45** | Tự làm đúng (`muc_goi_y = 0`), chấm xong mới xem lời giải | Ghi `xem_loi_giai_luc` riêng; `muc_goi_y` giữ nguyên `0` và câu đó vẫn tính là tự làm đúng. |
| **AT46** | Chạy tự động 4.096 tổ hợp câu 1–6 + quy tắc câu 7–8 | Mọi tổ hợp đều ra đúng cấp thăm dò của câu 2, 4, 6 và câu 7–8; câu 5–6 không ảnh hưởng cấp câu 7–8. |
| **AT47** | Ngân hàng thiếu câu ở cấp thăm dò mục tiêu | Chọn đúng thứ tự cấp dự phòng, lưu `cap_tham_do_id`, ghi chú mức chưa thăm dò; rỗng hẳn thì báo thiếu học liệu. |
| **AT48** | Chạy kiểm thử tích hợp với bộ Học viên mẫu A–D | Đề xuất, lý do và câu bằng chứng khớp chính xác với dữ liệu riêng của từng học viên A, B, C, D. |
| **AT49** | Đối chiếu số liệu trong câu lý do đề xuất | Mọi con số hiển thị đếm khớp 100% với truy vấn trực tiếp trên CSDL kiểm thử; thiếu số liệu thì ẩn câu đó. |
| **AT50** | Điểm yếu lặp lại chưa đạt ngưỡng khắc phục | Tiếp tục ưu tiên đề xuất ôn tập cho nhóm lỗi đó kèm lý do điểm yếu còn tồn tại. |
| **AT51** | Học viên A gọi API hồ sơ, đề xuất hoặc kết quả lượt làm của B | Backend trả lỗi không tìm thấy / từ chối truy cập, không rò rỉ dữ liệu. |
| **AT52** | AI trả JSON sai định dạng hoặc dẫn câu ngoài phiên | Backend lọc bỏ phần không hợp lệ (cùng khóa ngoại kép `nhan_dinh_bang_chung` chặn ở tầng CSDL). |
| **AT53** | Bài ôn bị khóa hoặc ở trạng thái `nhap` / `da_an` | Không bao giờ xuất hiện trong kết quả đề xuất cho học viên. |
