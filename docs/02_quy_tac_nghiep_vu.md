# 02. Quy tắc Nghiệp vụ đã chốt — Xianglingo

*(Tài liệu chuẩn cho code Backend & Frontend; ánh xạ sang **Chương 2: 2.4** và **Chương 3: 3.2** của quyển LVTN. Không tự suy diễn ngoài các quy tắc dưới đây).*

---

## 1. Đánh giá trình độ đầu vào 8 câu (Thay thế khảo sát tự chọn)

### 1.1. Phân luồng vào đánh giá (Chỉ áp dụng vai trò `hoc_vien`, xét từ trên xuống)
1. **Ưu tiên 1 — Đã có tiến độ học hợp lệ** *(đã từng nộp ít nhất 1 bài Ôn luyện `bai`/`cuoi_thua`, kiểm tra vượt `ap_dung_luc IS NOT NULL`, lượt Sổ tay hoặc bài Thi thử có ít nhất 1 câu `da_tra_loi`)*:
   - Không tự động chuyển vào bài đánh giá đầu vào (kể cả khi đang có phiên đánh giá tự nguyện làm dở).
   - Ở trang Ôn luyện có nút chủ động làm/tiếp tục bài đánh giá.
2. **Ưu tiên 2 — Đã nộp đánh giá đầu vào**:
   - Nếu phiên đánh giá gần nhất đang ở trạng thái phân tích (`chua` / `dang` / `loi`) và học viên chưa vào học bài nào: đưa tới màn hình kết quả đánh giá để xem hoặc bấm Thử lại.
   - Nếu đã phân tích `xong` (hoặc học viên chuyển trang): vào bình thường, xem lại được kết quả đánh giá từ trang Ôn luyện.
3. **Ưu tiên 3 — Đang có phiên đánh giá làm dở (`dang_lam`), chưa có tiến độ học**:
   - Tiếp tục đúng phiên đang làm dở (F5 không đổi câu, không mất đáp án đã lưu).
4. **Ưu tiên 4 — Chưa có phiên đánh giá và chưa có tiến độ học**:
   - Đưa thẳng vào bài đánh giá đầu vào 8 câu (không qua trang khảo sát `/khao-sat` cũ).
- *Giảng viên và Quản trị viên đăng nhập không bao giờ bị đưa vào đánh giá đầu vào (`AT32`).*

### 1.2. Cấu trúc 8 câu & Quy tắc rẽ nhánh tất định

| Vị trí câu | Kỹ năng (`ky_nang`) | Hình thức & Dạng câu (`dang`) | Cấp thăm dò mục tiêu (`cap_tham_do_id`) |
|---|---|---|---|
| **Câu 1** | `tu_vung` | Trắc nghiệm (`chon_mot`) | **HSK 2** |
| **Câu 2** | `tu_vung` | Trắc nghiệm (`chon_mot`) | Cặp với câu 1 (xem quy tắc rẽ cặp) |
| **Câu 3** | `doc` | Trắc nghiệm (`chon_mot`) | **HSK 2** |
| **Câu 4** | `doc` | Trắc nghiệm (`chon_mot`) | Cặp với câu 3 (xem quy tắc rẽ cặp) |
| **Câu 5** | `nghe` | Nghe chọn đáp án (`chon_mot` / `dung_sai`, có `tep_audio` riêng) | **HSK 2** |
| **Câu 6** | `nghe` | Nghe chọn đáp án (`chon_mot` / `dung_sai`, có `tep_audio` riêng) | Cặp với câu 5 (xem quy tắc rẽ cặp) |
| **Câu 7** | `viet` | Dịch câu Trung → Việt (`dich_cau`, tự nhập tiếng Việt) | Tính từ kết quả câu 1–4 |
| **Câu 8** | `viet` | Sắp xếp từ thành câu (`sap_xep`, bấm mảnh) | Cùng cấp mục tiêu với câu 7 |

- **Quy tắc rẽ nhánh trong từng cặp `(1→2)`, `(3→4)`, `(5→6)`**:
  - Câu đầu cặp thăm dò mục tiêu **HSK 2**.
  - Nếu câu đầu cặp trả lời **Đúng**: câu kế có cấp thăm dò mục tiêu = **HSK 3**.
  - Nếu câu đầu cặp **Sai** hoặc **Chủ động bỏ qua (`bo_qua`)**: câu kế có cấp thăm dò mục tiêu = **HSK 1**.
  - Nếu câu đầu cặp gặp **Lỗi kỹ thuật (`loi_ky_thuat`)**: không rẽ sang nhánh sai; câu kế giữ nguyên cấp đang thăm dò (**HSK 2**).
- **Quy tắc tính cấp thăm dò mục tiêu cho Câu 7–8 (chỉ phụ thuộc câu 1–4, độc lập với câu 5–6)**:
  - Xét trên các câu có `trang_thai_thao_tac = 'da_tra_loi'` và kết quả **Đúng** trong câu 1–4 (dựa theo **cấp thực tế** `v_cau_hoi.cap_do_id` của câu đã làm):
    1. Có **≥ 2 câu** ở cấp `≥ HSK 3` làm đúng → **HSK 4**.
    2. Có **1 câu** ở cấp `≥ HSK 3` làm đúng → **HSK 3**.
    3. Không có câu `≥ HSK 3` đúng, nhưng có **≥ 1 câu HSK 2** làm đúng → **HSK 2**.
    4. Các trường hợp còn lại → **HSK 1**.
  - Nếu trong câu 1–4 có câu `loi_ky_thuat` hoặc phải dùng cấp dự phòng làm không chạm tới HSK 3, vẫn tính theo công thức trên và ghi nhận vào `ket_qua_dau_vao.ghi_chu_gioi_han`.
- **Quy tắc chọn cấp dự phòng khi thiếu học liệu (`AT47`)**:
  - Chỉ rút các câu `trang_thai = 'da_dang'`, `dung_dau_vao = 1`, `cau_cha_id IS NULL`, đúng `ky_nang` và đúng `dang` của vị trí câu, không trùng câu đã dùng trong phiên (gồm cả `cau_tra_loi` và `lich_su_thay_cau`).
  - Nếu thiếu câu ở cấp mục tiêu $L \in \{1,2,3,4\}$, thử lần lượt theo khoảng cách: $L-1$, $L+1$, $L-2$, $L+2$, $L-3$, $L+3$ (chỉ lấy trong miền `1..4`, ưu tiên cấp thấp hơn trước khi cùng khoảng cách).
  - Lưu `cap_tham_do_id = L` trên `cau_tra_loi`; cấp thực tế đọc từ `v_cau_hoi.cap_do_id`. Khi hai giá trị khác nhau, kết quả ghi rõ *"Chưa thăm dò được mức HSK L ở kỹ năng …"*.
  - Nếu toàn bộ dải HSK 1–4 không còn câu phù hợp cho vị trí đó: dừng tạo/tiếp tục bài đánh giá, báo *"Ngân hàng chưa đủ học liệu đánh giá đầu vào"* và cho phép học viên vào thẳng lộ trình nền tảng mở sẵn (không tự đổi dạng câu, không xuất kết quả đánh giá đầy đủ).

### 1.3. Trải nghiệm làm bài, Xử lý lỗi audio & Nộp bài đầu vào
- Mỗi màn 1 câu (`Câu x/8`), đã qua câu sau thì không quay lại sửa câu trước; không đếm ngược giờ, không có gợi ý, không có Hỏi Xiang.
- **Lỗi phát âm thanh ở câu 5–6 (`AT06, AT33, AT44`)**:
  - Cho phép bấm phát lại; nếu vẫn lỗi, học viên bấm *"Báo lỗi âm thanh / Đổi câu khác"*:
    - Nếu ngân hàng còn câu cùng `ky_nang = 'nghe'`, cùng cấp mục tiêu (hoặc dự phòng cùng cấp thực tế), không trùng câu đã dùng: ghi dòng vào `lich_su_thay_cau` và cập nhật câu mới tại đúng vị trí `thu_tu` đó (tổng vẫn 8 câu).
    - Nếu không còn câu thay thế: đánh dấu `trang_thai_thao_tac = 'loi_ky_thuat'` và cho phép qua câu tiếp theo.
- **Điều kiện nộp bài đầu vào (`AT03, AT04, AT44`)**:
  - Chỉ được nộp khi cả 8 vị trí đều có `trang_thai_thao_tac IN ('da_tra_loi', 'bo_qua', 'loi_ky_thuat')` (không còn câu `chua_thao_tac`).
- **Chấm điểm & Phân tích AI**:
  - Câu 1–6 (trắc nghiệm) và Câu 8 (`sap_xep`, chấp nhận nhiều trật tự trong `phuong_an.vai_tro = 'dap_an_chap_nhan'`) do backend chấm ngay.
  - Câu 7 (`dich_cau`) do AI chấm theo `tieu_chi_mo_ta`: trả `diem` (`0 .. diem_toi_da`), `nhan_xet`, `cau_sua`, `ly_do_sua`; câu được tính là **Đúng** khi `diem >= nguong_dat`.
  - Trạng thái phân tích lưu tại `ket_qua_dau_vao.trang_thai_phan_tich` (`chua → dang → xong | loi`), có thời hạn xử lý (`60 giây` kể từ `bat_dau_phan_tich_luc`; quá hạn tự coi là `loi` để cho bấm **Thử lại** – `AT35`).
  - Không giữ giao dịch CSDL mở trong lúc gọi OpenAI; khóa chống gọi trùng theo `luot_lam_id`. Khi bấm **Thử lại**, câu 7 nếu đã có `ket_qua_cham.trang_thai = 'hoan_tat'` khớp `phien_ban_luu` thì dùng lại điểm, chỉ chạy lại bước còn thiếu (`AT36`).
  - Backend kiểm tra JSON nhận định của AI: loại bỏ mọi nhận định sai định dạng hoặc dẫn `thu_tu_cau` không nằm trong `1..8` hoặc dẫn câu `loi_ky_thuat` làm lỗi kiến thức (`AT38, AT52`).
- **Hiển thị kết quả đầu vào (4 phần rõ ràng)**:
  1. Nhận định năng lực theo từng kỹ năng kèm liên kết tới câu bằng chứng (`AT37`).
  2. Điểm bắt đầu đề xuất (`cap_de_xuat_id`) — ghi rõ là *"bằng chứng ban đầu"*, không khẳng định đạt cấp, **không tự động mở khóa cấp**.
  3. Bài ôn cụ thể nên học (lưu trong `goi_y_lo_trinh`) và nút mở thẳng; nếu cấp đề xuất của kỹ năng tương ứng đang khóa thì hiện nút *"Làm bài Bắt đầu cấp HSK X (kỹ năng …)"* dẫn đúng vào kiểm tra mở cấp của kỹ năng đó.
  4. Danh sách các cấp hiện đã mở sẵn theo từng kỹ năng.
  - Cuối màn kết quả có mục tùy chọn (bỏ qua được): *"Bạn muốn ôn để thi HSK mấy?"* → lưu vào `nguoi_dung.ks_cap_muc_tieu_id`.

---

## 2. Hồ sơ năng lực & "Bài phù hợp với bạn hôm nay"

### 2.1. Dữ liệu đầu vào của Hồ sơ năng lực
- Tính từ mọi câu trả lời đã kết thúc của chính học viên trên các lượt đã nộp (`luot_lam.trang_thai = 'da_nop'`), gom theo ma trận **`ky_nang × nhom_kien_thuc_id`**:
  - Chỉ tính các câu có kết quả chấm hoàn tất hoặc chủ động bỏ qua; **loại trừ hoàn toàn** câu `loi_ky_thuat` và câu chưa chấm xong (`AT38`).
  - Một câu trả lời được phân loại là:
    - **Tự làm đúng**: `diem >= nguong_dung` VÀ `muc_goi_y = 0` VÀ không có tin nhắn Hỏi Xiang nào trước `xac_nhan_luc`, đồng thời không phải làm lại ngay trong cùng ngày vừa xem lời giải (`xem_loi_giai_luc`) của câu gốc đó.
    - **Làm đúng nhờ hỗ trợ**: `diem >= nguong_dung` nhưng có `muc_goi_y IN (1, 2)` hoặc có Hỏi Xiang trước `xac_nhan_luc`.
    - **Làm sai**: `trang_thai_thao_tac = 'da_tra_loi'` và `diem < nguong_dung` *(trong đó `nguong_dung = cau_hoi.nguong_dat` với `viet_mo`/`dich_cau`, và `= 1` với các dạng còn lại)*.

### 2.2. Ngưỡng định lượng & Thứ tự 5 mức ưu tiên chọn bài (Hàm thuần)
Hàm `select_today_lesson(profile, target_level, candidate_lessons)` là **hàm thuần (pure function)** không truy cập CSDL, không gọi AI, chỉ xét trên danh sách bài ôn (`bo_de.loai = 'bai'`) **đã xuất bản (`da_dang`) và đang mở (không khóa)** với học viên (`AT53`):

1. **Ưu tiên 1 — Kiến thức nền còn thiếu**: Nhóm kiến thức ở cấp thấp hơn hoặc bằng mục tiêu (`ks_cap_muc_tieu_id`), nằm trong bài chưa đạt (`chua_dat`) hoặc có từ **≥ 2 câu sai / bỏ qua** trở lên và tỷ lệ tự làm đúng `< 50%`. *(Một câu sai đơn lẻ không bao giờ kết luận yếu nhóm kiến thức – `AT39`).*
2. **Ưu tiên 2 — Lỗi sai lặp lại**: Nhóm kiến thức có **≥ 2 lần làm sai** trong lịch sử gần đây và tỷ lệ tự làm đúng trên tối thiểu 3 câu gần nhất của nhóm đó `< 60%` (chưa được khắc phục – `AT50`).
3. **Ưu tiên 3 — Làm đúng nhưng cần nhiều gợi ý**: Nhóm kiến thức có tỷ lệ đúng `≥ 60%` nhưng có **≥ 2 câu** (hoặc `≥ 50%` số câu làm đúng trong nhóm) thuộc diện *Làm đúng nhờ hỗ trợ*.
4. **Ưu tiên 4 — Nội dung cần ôn lại**: Bài đã đạt (`da_xong`) có câu đến hạn trong Sổ tay hoặc lần hoàn thành gần nhất cách hiện tại **≥ 7 ngày**.
5. **Ưu tiên 5 — Nội dung mới trong phạm vi đã mở**: Bài `chua_hoc` hoặc `dang_lam` gần mục tiêu HSK của học viên nhất theo thứ tự lộ trình chuẩn.

- **Quy tắc khớp bài & phá hòa (Tie-break)**:
  - Trong một mức ưu tiên, chấm điểm khớp bài theo số lượng câu trong bài thuộc `nhom_kien_thuc_id` + `ky_nang` cần ưu tiên; nếu bằng nhau thì ưu tiên: (a) bài đang làm dở (`dang_lam`) → (b) bài chưa đạt (`chua_dat`) → (c) cấp độ gần `ks_cap_muc_tieu_id` nhất (nhưng không vượt quá cấp đã mở) → (d) thứ tự thửa và vị trí bài nhỏ hơn.
  - Nếu học viên chưa chọn mục tiêu hoặc chưa có dữ liệu làm bài: rơi vào Ưu tiên 5 và kèm ghi chú rõ *"Chưa có nhiều dữ liệu làm bài / mục tiêu HSK, hệ thống đề xuất bài mở đầu phù hợp"* (`AT40`).
  - Mẫu câu lý do chỉ hiển thị những con số đếm thật từ dữ liệu của học viên; trường dữ liệu nào trống thì ẩn vế câu đó (`AT49`).

---

## 3. Gợi ý 2 mức, Hỏi Xiang và Chấm chữa câu Viết/Dịch

### 3.1. Phạm vi cho phép hỗ trợ & Lật thẻ từ sau khi chấm
- **Trước khi bấm `Kiểm tra` câu**: Chỉ mở **Gợi ý 2 mức** (`Gợi ý 1/2`, `Gợi ý 2/2`) trên bài Ôn luyện thường (`bo_de.loai = 'bai'`); khóa lật thẻ từ và chưa mở Hỏi Xiang để tránh lộ đáp án.
- **Sau khi bấm `Kiểm tra` câu (đã có kết quả chấm)**: Mở khóa **Hỏi Xiang** theo ngữ cảnh câu vừa làm và mở hiệu ứng **lật thẻ từ 3D** ngay trên câu đó để xem Chữ Hán, Pinyin, Nghĩa và Câu ví dụ song ngữ (không còn màn hình Thẻ từ rời ở đầu bài). Khi học viên bấm **Làm lại bài chưa đạt (`lam_lai`)**, hệ thống tự động ẩn Pinyin hỗ trợ và hiển thị câu ngữ cảnh chữ Hán thực tế để chống học vẹt đáp án.
- **Tắt hoàn toàn Gợi ý & Hỏi Xiang khi đang làm bài**: Đánh giá đầu vào (`danh_gia_dau_vao`), Thi thử (`de_thi`), Kiểm tra cuối thửa (`cuoi_thua`) và các bài Kiểm tra vượt (`vuot_thua`, `bat_dau_cap`, `vuot_chang`). Ở các bài này chỉ được xem giải thích và Hỏi Xiang **sau khi đã nộp bài** (`AT23`).

### 3.2. Bảo mật đáp án & Ghi nhận hỗ trợ
- Trước khi câu được xác nhận (hoặc nộp lượt): API **tuyệt đối không gửi** `dap_an_id`, `dap_an_chap_nhan`, `giai_thich`, `dich_nghia`, `loi_nghe`, cũng không gửi trước nội dung gợi ý xuống trình duyệt.
- Học viên bấm mở gợi ý lần 1 → gọi API mở mức 1 (tăng `cau_tra_loi.muc_goi_y = GREATEST(muc_goi_y, 1)` và trả `goi_y`); sau khi đã mở mức 1 mới được bấm mở mức 2 (`muc_goi_y = 2`, trả `goi_y_2`). Nếu câu chưa có gợi ý do Giảng viên soạn thì trả gợi ý chiến lược an toàn theo dạng câu/kỹ năng (hoặc AI sinh có hậu kiểm không chứa chuỗi đáp án đúng).
- **Hỏi Xiang trước khi xác nhận câu (`AT15`)**:
  - Backend dựng ngữ cảnh **ẩn hoàn toàn đáp án đúng và lời giải**, kèm prompt khóa chặt: từ chối nêu đáp án, không dịch toạc cả câu làm lộ lời giải, không loại trừ hết phương án sai, không viết hộ câu hoàn chỉnh.
  - Lưu cuộc hỏi đáp vào `hoi_thoai (cau_tra_loi_id)` và `tin_nhan`; đóng giao dịch đọc CSDL trước khi gọi mạng tới AI.
  - **Quy tắc 1 cuộc trò chuyện duy nhất mỗi câu**: Mỗi `cau_tra_loi_id` chỉ có tối đa một dòng `hoi_thoai` (`uq_hoi_thoai_ctl`) xuyên suốt cả trước và sau khi bấm Kiểm tra; mọi tin nhắn mới đều nối tiếp vào cuộc hội thoại hiện có, không bao giờ xóa để tạo cuộc hội thoại mới.
- Mở gợi ý hoặc Hỏi Xiang **không trừ điểm câu đó và không đổi công thức cộng KN** (`AT16`).
- Sau khi chấm câu: khi học viên xem lời giải chi tiết, ghi nhận `xem_loi_giai_luc = NOW()` mà **không sửa đổi `muc_goi_y`** đã chốt trước lúc xác nhận (`AT45`).

### 3.3. Chấm & chữa câu Dịch / Viết theo mô hình hướng dẫn (Tham khảo WriteMate AI)
- Với câu `dich_cau` và `viet_mo`: AI chấm dựa trên đề bài, `tu_bat_buoc` (nếu có) và `tieu_chi_mo_ta`, lưu vào `ket_qua_cham` đủ 4 trường: `diem`, `nhan_xet` (đánh giá mức đạt ý), `cau_sua` (câu viết lại tự nhiên bám ý của học viên) và `ly_do_sua` (chỉ rõ điểm ngữ pháp/từ vựng cần sửa).

---

## 4. Sổ tay câu sai, Mở khóa nội dung, Thi thử, Chuỗi ngày & KN, Soạn đề AI

1. **Sổ tay câu sai (Mục 5)**:
   - Câu làm sai ở bài Ôn luyện tự động vào `so_tay` (`trang_thai = 'can_on'`). Câu `bo_qua` hoặc `loi_ky_thuat` không tính là câu làm sai kiến thức.
   - Sắp xếp lượt ôn Sổ tay (tối đa 10 câu): ưu tiên câu đến hạn (`han_on <= CURDATE()`), câu thuộc **nhóm kiến thức có lỗi lặp lại**, rồi đến câu sai nhiều lần.
   - Quy tắc củng cố: `can_on` → (tự làm đúng, không phải vừa xem lời giải của câu đó trong cùng ngày và `muc_goi_y = 0`) → `cho_on_lai` (`han_on = CURDATE() + 1 DAY`) → (tự làm đúng khi đến hạn) → `da_cung_co` (`+1 KN` lần đầu). Nếu làm đúng ngay sau khi vừa xem lời giải trong ngày hoặc phải dùng gợi ý mức 2 thì giữ trạng thái để ôn tiếp lần sau. Sau khi làm đúng câu cũ, gợi ý thêm 1 câu tương tự cùng `nhom_kien_thuc_id` + `cap_do_id` nếu ngân hàng có sẵn.
2. **Mở khóa 3 tầng (Mục 6)**:
   - **Ô kế trong thửa**: mở khi đạt ô trước (đúng hết các câu của bài).
   - **Thửa kế trong cấp**: mở khi đạt `Kiểm tra cuối thửa` (đúng hết các câu trong 1 lượt) hoặc đạt bài `Vượt thửa` tới thửa đó (`Vượt thửa` đánh dấu các thửa trước trong cùng cấp là `"Đã vượt"`).
   - **Cấp kế theo từng kỹ năng**: mở khi xong các thửa của cấp và đạt `Vượt chặng` (15/15), hoặc đạt `Bắt đầu cấp` (10/10 câu cấp liền dưới). **Đạt `Bắt đầu cấp` chỉ mở cấp đó của kỹ năng tương ứng; vẫn cho ôn cấp dưới nhưng không đánh dấu các bài/thửa cấp dưới là `"Đã vượt"`.**
   - Mọi luồng Ôn luyện và Thi thử đều bắt buộc đăng nhập tài khoản Học viên (để xác định trình độ đầu vào trước); các đường dẫn công khai cũ `/api/cong-khai/on-luyen/...` đều bị từ chối `401 Unauthorized` (`AT13`).
3. **Thi thử (Mục 7)**:
   - Học viên chỉ chọn cấp HSK; ẩn danh sách đề và chặn các đường API chọn đề theo ID cũ (`AT17, AT42`).
   - Nếu học viên đang có phiên `de_thi` trạng thái `dang_lam` còn thời gian ở cấp đó: trả lại đúng phiên đang làm (F5 hoặc bấm bắt đầu lại không đổi đề, không đặt lại giờ – `AT18`).
   - Nếu chưa có phiên đang làm: chọn ngẫu nhiên 1 đề hợp lệ (`da_dang`, có `thoi_luong_phut > 0`, đủ câu tính điểm và đủ audio), ưu tiên đề chưa từng nộp (`da_nop`); nếu đã làm hết các đề của cấp thì chọn ngẫu nhiên trong toàn bộ đề hợp lệ của cấp đó; không có đề thì báo *"Chưa có đề phù hợp"*.
   - **Nộp tay**: chặn khi còn câu tính điểm chưa trả lời và trả danh sách số thứ tự câu còn trống (`AT19`); đủ câu thì hiện hộp thoại xác nhận trước khi nộp.
   - **Hết giờ**: tự động nộp ngay phần đã làm, không hiện hộp xác nhận (`AT20, AT41`). Nếu phiên quá hạn từ trước được chốt muộn thì `nop_luc = LEAST(NOW(), bat_dau_luc + INTERVAL thoi_luong_phut MINUTE)`. Khóa dòng `FOR UPDATE` để bấm nộp tay trùng lúc hết giờ chỉ ghi nhận duy nhất 1 kết quả (`AT21`).
   - **Phím tắt**: Mũi tên `Trái / Phải` chuyển câu trong phạm vi phần thi cho phép (theo cấu trúc HSK máy tính: trong khi đang phát phần Nghe hoặc đã qua phần Nghe sang Đọc/Viết thì không dùng phím mũi tên quay ngược về phần đã khóa điều hướng – `AT43`); phím `1–6` hoặc `A–F` chọn phương án; không bắt phím khi con trỏ đang ở `INPUT` / `TEXTAREA` (`AT22`); không có phím tắt nộp bài.
4. **Chuỗi ngày học & Điểm KN (Mục 8)**:
   - Múi giờ chuẩn của toàn bộ kết nối CSDL: `Asia/Ho_Chi_Minh` (`+07:00`).
   - Tăng chuỗi tối đa 1 lần/ngày khi hoàn thành (`da_nop`) ít nhất một hoạt động có **ít nhất 1 câu `da_tra_loi`**: bài Ôn luyện (`bai`, `cuoi_thua`), bài Kiểm tra vượt / Đánh giá đầu vào, lượt Sổ tay, hoặc bài Thi thử (`AT26, AT27`).
   - **Giữ nguyên công thức KN hiện hành** và trả kèm `(kn_nhan, ly_do_kn, tong_kn)` từ backend sau mỗi lượt (`AT28`):
     - Đạt bài ôn thường (`kn_bai`): **+10 KN** (lần đầu mỗi `bo_de_goc_id`).
     - Đạt kiểm tra cuối thửa (`kn_cuoi_thua`): **+20 KN** (lần đầu mỗi `bo_de_goc_id`).
     - Đạt vượt thửa (`kn_vuot_thua`): **+20 KN** (lần đầu mỗi thửa đích `bo_de_goc_id`).
     - Đạt bắt đầu cấp (`kn_bat_dau_cap`): **+20 KN** (lần đầu mỗi `cap_do_id × ky_nang`).
     - Đạt vượt chặng (`kn_vuot_chang`): **+20 KN** (lần đầu mỗi `cap_do_id × ky_nang`).
     - Củng cố câu Sổ tay (`kn_cung_co`): **+1 KN** (lần đầu mỗi `cau_hoi_goc_id`).
   - **Bình năng lượng mở rộng theo Trình độ HSK (`5 → 6 → 8 → 10`)**:
     - Trần năng lượng tối đa theo cấp HSK chính thức: **HSK 1 = 5**, **HSK 2 = 6**, **HSK 3 = 8**, **HSK 4 = 10**; tự động mở rộng khi thăng cấp (`thang_cap_nl`) và tự động hồi đầy bình vào đầu mỗi ngày mới (`hoi_ngay`).
     - Hồi năng lượng trong ngày (đối soát cân bằng qua `v_doi_soat_nang_luong`): Nhiệm vụ ngày (`+1/nhiệm vụ`), hoàn thành 1 lượt Ôn Sổ tay đạt **≥ 80% câu đúng** (`hoi_so_tay`: `+1/lượt`, không giới hạn số lần khi bình chưa đầy), và vượt Kiểm tra cuối thửa 10/10 (`thuong_cuoi_thua`: `+1`).
5. **Giảng viên soạn câu hỏi với AI (Mục 9)**:
   - Giảng viên nhập cấp, kỹ năng, chủ đề/nhóm kiến thức, dạng câu, số lượng → AI sinh bản nháp gắn `nguon_noi_dung = 'soan_voi_ai'`, `trang_thai = 'nhap'` (cho phép lưu nháp để sửa dần, không bao giờ tự xuất bản – `AT24`).
   - Khi bấm **Duyệt & Xuất bản (`publish_question`)**: kiểm tra đầy đủ thành phần bắt buộc theo dạng câu, ghi `nguoi_duyet_id` và `duyet_luc = NOW()`.
   - Với câu Nghe dùng độc lập (bật `dung_on_luyen = 1` hoặc `dung_dau_vao = 1`): bắt buộc có `tep_audio` tồn tại thật trên máy chủ và `da_kiem_tra_audio = 1`. **Mỗi khi `tep_audio` bị thay đổi hoặc xóa trắng, backend tự động đặt lại `da_kiem_tra_audio = 0`.**
   - Câu hỏi đã đăng/đã có người làm khi chỉnh sửa luôn tạo phiên bản mới (`phien_ban + 1`), giữ nguyên lịch sử các lượt làm cũ (`AT25`).
