# Báo cáo rà soát nghiệp vụ `NV.docx` & đối chiếu Code / Schema SQL

> [!NOTE]
> Báo cáo này thực hiện ở chế độ **chỉ đọc**: chưa chỉnh sửa bất kỳ tệp mã nguồn nào trong `d:\HSK_AI` và chưa chạy câu lệnh SQL nào lên cơ sở dữ liệu. Mọi phát hiện bám sát nội dung hiện có, không tự suy đoán hay tự thêm quy tắc nghiệp vụ mới.

---

## 0. Tình trạng đọc tài liệu và tệp trong dự án

1. **Tài liệu `NV.docx`**:
   - Không có bản lưu `NV.docx` bên trong thư mục `d:\HSK_AI`; tài liệu được đọc trực tiếp từ tệp đính kèm của yêu cầu (`word/document.xml`, gồm 189 khối đoạn văn và bảng; 0 hình ảnh/sơ đồ nhúng, 0 bình luận ẩn, 0 vết xóa/sửa Track Changes).
   - **Kết quả**: Đọc được đầy đủ **100%** nội dung chữ và bảng của `NV.docx`.
2. **Các tệp trống (0 byte) trong `d:\HSK_AI` không có nội dung để đọc**:
   - Tài liệu nội bộ trong `docs/`: [business_rules.md](file:///d:/HSK_AI/docs/business_rules.md), [database.md](file:///d:/HSK_AI/docs/database.md), [development_steps.md](file:///d:/HSK_AI/docs/development_steps.md), [scope.md](file:///d:/HSK_AI/docs/scope.md).
   - Các module/tệp khung 0 byte ở backend và frontend: `backend/app/integrations/openai/*`, `backend/app/modules/grading/*`, `backend/app/modules/results/*`, `backend/app/modules/ai_explanations/*`, `backend/app/models/*`, [env.py](file:///d:/HSK_AI/backend/migrations/env.py), `frontend/src/features/exam_session/*`.

---

## 1. Rà soát độc lập tài liệu nghiệp vụ `NV.docx`

### 1.1. Mâu thuẫn nội tại

| Mã | Mức độ | Phát hiện | Bằng chứng trong `NV.docx` |
|---|---|---|---|
| **NV-MT01** | **Bắt buộc sửa** | **Mâu thuẫn trong quy tắc tính cấp câu 7–8 và kiểm thử tổ hợp rẽ nhánh (`AT46`)**:<br>1) *Phụ lục C* và *AT46* yêu cầu chạy tự động toàn bộ `4⁶ = 4.096` tổ hợp 4 trạng thái (`đúng, sai, bỏ qua, lỗi kỹ thuật`) của câu 1–6 *"Theo quy tắc đã chốt"*, nhưng chính mục *Điểm còn cần chốt* lại ghi trường hợp câu 2 hoặc 4 bị lỗi kỹ thuật **chưa chốt** cách tính cấp câu 7–8.<br>2) Nếu **câu 1 (HSK 2) và câu 3 (HSK 2)** bị `Lỗi kỹ thuật`, theo *Mục 1 – Trường hợp đặc biệt* (*"câu kế của cặp giữ ở cấp đang thăm dò"*), câu 2 và câu 4 sẽ giữ ở **HSK 2**. Khi đó dù học viên làm đúng hết câu 2 và câu 4, trong câu 1–4 không có câu HSK 3 nào nên công thức câu 7–8 không bao giờ lên được HSK 3/4 (trường hợp này cũng bị sót trong *Điểm còn cần chốt*).<br>3) Khi thiếu câu phải dùng **cấp dự phòng** (*Mục 1 – Hệ thống làm gì*): nếu câu 1 dự phòng lên HSK 3 thì trong câu 1–4 có thể xuất hiện **3 câu HSK 3 đúng** (công thức chỉ viết *"đúng cả hai câu HSK 3 → HSK 4; đúng một → HSK 3"*); ngược lại nếu câu 2 dự phòng lùi về HSK 2 thì làm đúng cả 2 câu vẫn bị đếm là `0` câu HSK 3 đúng. | *Mục 1 (Hệ thống làm gì; Trường hợp đặc biệt)*, *Phụ lục C (Nhóm 2)*, *Phụ lục D (AT46)* đối chiếu *Điểm còn cần chốt* |
| **NV-MT02** | **Bắt buộc sửa** | **Mâu thuẫn điều kiện được nộp bài đánh giá đầu vào khi có câu `Lỗi kỹ thuật`**:<br>*AT04* ghi *"Cả 8 câu đã trả lời hoặc bỏ qua → Được nộp đánh giá"*. Tuy nhiên khi câu Nghe không phát được âm thanh và không thay được câu, trạng thái thao tác lưu là `Lỗi kỹ thuật` (*Phụ lục A*), không được gộp vào `Chủ động bỏ qua` (*AT06*), nhưng *Mục 1* và *AT44* vẫn cho phép nộp kết quả giới hạn. Điều kiện ở *AT04* đang thiếu trạng thái `Lỗi kỹ thuật`. | *Phụ lục D (AT04)* đối chiếu *Mục 1 (Trường hợp đặc biệt)*, *Phụ lục A*, *Phụ lục D (AT06, AT44)* |
| **NV-MT03** | **Bắt buộc sửa** | **Mâu thuẫn giữa nút "Làm bài Bắt đầu cấp X" sau đánh giá đầu vào với tiến độ mở khóa riêng theo từng kỹ năng**:<br>*Mục 1* quy định nếu cấp đề xuất còn khóa thì hiện nút *"Làm bài Bắt đầu cấp X"* để vào thẳng bài mở cấp (như một bài chung của cấp X). Nhưng *Mục 6* quy định mỗi kỹ năng có tiến độ riêng và *"Đạt bài Bắt đầu cấp thì mở đúng cấp và kỹ năng tương ứng"*. Chưa khớp được 1 nút chung ở *Mục 1* sẽ mở bài Bắt đầu cấp của kỹ năng nào. | *Mục 1 (Kết quả tách rõ 4 phần)* đối chiếu *Mục 6 (Hệ thống làm gì)* |
| **NV-MT04** | **Bắt buộc sửa** | **Mâu thuẫn giữa việc hiện lời giải ngay sau khi kiểm tra và việc tách trạng thái "Đã xem lời giải"**:<br>Bảng *Mục 3* mô tả *"Sau khi kiểm tra → Đáp án, lời giải, phân tích lỗi"* (hiển thị ngay khi chấm câu). Ngược lại, *AT45* (*"Tự làm đúng, sau khi chấm mới xem lời giải"*) và *Mục 5* (*"Làm đúng ngay sau khi xem lời giải thì chưa tính là đã vững"*) lại giả định học viên có thể chấm xong mà **chưa** xem lời giải (phải có thao tác bấm mở lời giải riêng). | *Mục 3 (Người học thấy gì)* đối chiếu *Mục 5 (Hệ thống làm gì)*, *Phụ lục A*, *Phụ lục D (AT45)* |
| **NV-MT05** | **Bắt buộc sửa** | **Đưa giới hạn điều hướng giữa các phần Thi thử vào nghiệm thu (`AT43`) khi chưa đặc tả quy tắc trong tài liệu**:<br>*AT43* đòi nghiệm thu *"Phím mũi tên ở phần thi có giới hạn điều hướng → Không chuyển sang phần không được phép"*, nhưng *Mục 7 – Trường hợp đặc biệt* lại ghi *"Quy trình thi HSK trên máy sẽ tra từ nguồn chính thức (chinesetest.cn) trước khi sửa cách chuyển câu giữa các phần"* (quy tắc cụ thể chưa được chốt trong văn bản). | *Mục 7 (Người học thấy gì; Trường hợp đặc biệt)* đối chiếu *Phụ lục D (AT43)* |

---

### 1.2. Thiếu điều kiện

| Mã | Mức độ | Điều kiện còn thiếu | Bằng chứng trong `NV.docx` |
|---|---|---|---|
| **NV-TD01** | **Bắt buộc sửa** | **Thiếu toàn bộ công thức và ngưỡng định lượng cho hàm chọn bài thuần (Pure function)**:<br>Tài liệu yêu cầu xếp 5 mức ưu tiên `(1) kiến thức nền còn thiếu → (2) lỗi lặp lại → (3) đúng nhưng cần nhiều gợi ý → (4) cần ôn lại → (5) nội dung mới` và nêu *"Một câu sai chưa đủ kết luận yếu cả nhóm"* (*AT39*), nhưng chưa định nghĩa:<br>- Ngưỡng số câu sai / tỷ lệ sai để vào mức `(1)`, `(2)` và điều kiện thoát khỏi *"điểm yếu chưa khắc phục"* (*AT50*).<br>- Ngưỡng *"cần nhiều gợi ý"* ở mức `(3)` (tính Gợi ý mức 1 hay mức 2, bao nhiêu lần).<br>- Khoảng thời gian / điều kiện để bài đã đạt chuyển sang mức `(4) cần ôn lại`.<br>- Quy tắc ánh xạ từ `nhóm kiến thức` (gắn trên từng câu hỏi) sang `bài ôn` (chứa nhiều câu thuộc nhiều nhóm khác nhau) và quy tắc phá hòa (tie-break) khi nhiều bài cùng mức ưu tiên. | *Mục 2 (Hệ thống làm gì)*, *Mục 4 (Trường hợp đặc biệt)*, *Phụ lục C (Nhóm 2; Cách tổ chức kiểm thử)*, *Phụ lục D (AT39, AT48, AT50)* |
| **NV-TD02** | **Bắt buộc sửa** | **Thiếu quy tắc ghi nhận `Mức hỗ trợ` khi học viên dùng "Hỏi Xiang" trước khi kiểm tra**:<br>*Mục 3* cho phép chat `Hỏi Xiang` trước khi xác nhận đáp án, nhưng chiều `Mức hỗ trợ` ở *Phụ lục A* chỉ có `Không dùng · Gợi ý mức 1 · Gợi ý mức 2 · Đã xem lời giải`. Nếu học viên hỏi Xiang (không bấm nút Gợi ý 1/2) rồi làm đúng mà ghi `Không dùng` thì sẽ bị tính nhầm là "Tự làm đúng". | *Mục 3 (Hệ thống làm gì)*, *Phụ lục A (Ba chiều ghi nhận)* |
| **NV-TD03** | **Bắt buộc sửa** | **Thiếu định nghĩa "ngay sau khi xem lời giải" và quy tắc tính củng cố khi dùng gợi ý trong Sổ tay**:<br>1) *Mục 5* nêu *"Làm đúng ngay sau khi xem lời giải thì chưa tính là đã vững"*, chưa rõ "ngay sau" tính trong cùng phiên, cùng ngày, trong `X` phút sau khi vừa xem lời giải ở Ôn luyện, hay ở lần gặp lại kế tiếp.<br>2) *Thứ tự triển khai (bước 4)* yêu cầu *"Sổ tay phân biệt câu làm đúng nhờ hỗ trợ"*, nhưng *Mục 5* chưa quy định làm đúng nhờ Gợi ý mức 1/2 trong Sổ tay thì trạng thái câu giữ nguyên hay chuyển thế nào. | *Mục 5 (Hệ thống làm gì)*, *Phụ lục A*, *Thứ tự triển khai (bước 4)* |
| **NV-TD04** | **Bắt buộc sửa** | **Thiếu thang điểm và ngưỡng quy đổi `Đúng / Sai` cho câu dịch do AI chấm**:<br>*Phụ lục A* quy định `Kết quả chấm` chỉ gồm `Đúng · Sai · Chưa chấm`, trong khi *AT36* nêu *"Điểm AI"* và *"tiêu chí chấm"*. Chưa quy định thang điểm chấm câu dịch (Câu 7 đầu vào) và ngưỡng điểm tối thiểu để ghi nhận là `Đúng`. | *Mục 1 (Hệ thống làm gì)*, *Phụ lục A*, *Phụ lục D (AT07, AT36)* |
| **NV-TD05** | **Bắt buộc sửa** | **Thiếu điều kiện chi tiết trong luồng Đánh giá đầu vào 8 câu**:<br>1) Ưu tiên 1: chưa định nghĩa *"tiến độ học hợp lệ"* (cần đạt ≥ 1 bài Ôn luyện, hay tính cả lượt chưa đạt / Thi thử / Sổ tay).<br>2) Ưu tiên 2: *"Tới kết quả hoặc trang Ôn luyện"* — chưa có điều kiện phân nhánh khi nào vào Kết quả, khi nào vào Ôn luyện.<br>3) Đánh giá tự nguyện từ trang Ôn luyện: có giới hạn số lần làm lại không, có thoát/hủy giữa chừng được không, và kết quả mới cập nhật vào đâu.<br>4) Rẽ nhánh khi dùng cấp dự phòng: nếu câu 1 (lẽ ra HSK 2) phải dùng câu dự phòng HSK 1 và học viên trả lời đúng, câu 2 nhảy lên HSK 3 hay HSK 2? Nếu cả cấp liền dưới và liền trên (±1) đều thiếu câu nhưng cách 2 cấp vẫn còn câu thì có chọn tiếp không? | *Mục 1 (Ai được đưa vào đánh giá; Hệ thống làm gì)*, *Phụ lục D (AT31, AT47)* |
| **NV-TD06** | **Bắt buộc sửa** | **Thiếu điều kiện biên ở Chuỗi ngày học, phạm vi chạy Phân tích AI, chọn đề Thi thử và AI soạn đề**:<br>1) *Mục 8 (Chuỗi ngày)*: Hoàn thành **Đánh giá đầu vào 8 câu** có tính chuỗi ngày không? Bài Ôn luyện thường làm hết câu nhưng **không đạt** có tính chuỗi không? Lượt Sổ tay bỏ qua hết các câu có tính không?<br>2) *Mục 4 & Phụ lục A*: Phân tích AI bất đồng bộ (lưu trạng thái `chưa/đang/xong/lỗi`, liên kết nhận định – câu bằng chứng) chỉ áp dụng cho Đánh giá đầu vào / Thi thử hay chạy sau **mọi bài Ôn luyện 5 câu và lượt Sổ tay**?<br>3) *Mục 7 (Thi thử)*: Khi cấp có `≥ 2` đề hợp lệ và học viên **đã làm qua tất cả các đề**, hệ thống bốc ngẫu nhiên lại trong toàn bộ đề của cấp đó hay theo quy tắc nào? Và "đề chưa làm" xét theo lượt `da_nop` hay tính cả lượt bỏ dở?<br>4) *Mục 9 (Giảng viên soạn đề với AI)*: Chưa rõ AI tạo **câu hỏi ngân hàng** hay tạo nguyên **bộ đề/bài ôn**; chưa rõ Giảng viên tạo nháp có tự duyệt & xuất bản luôn hay cần quyền tách biệt. | *Mục 4*, *Mục 7*, *Mục 8*, *Mục 9*, *Phụ lục A* |
| **NV-TD07** | **Cải tiến tùy chọn** | **Chưa liệt kê bảng tổ hợp hợp lệ giữa 3 chiều ở Phụ lục A và quy tắc vào Sổ tay của câu bỏ qua / câu đầu vào**:<br>Cần làm rõ `Chủ động bỏ qua` đi với `Kết quả chấm = Chưa chấm` hay `Sai`; câu `Chủ động bỏ qua` và câu sai trong `Đánh giá đầu vào` có tự động đưa vào `Sổ tay` (*Mục 5*) hay không. | *Mục 5*, *Phụ lục A (Ba chiều ghi nhận)* |

---

### 1.3. Thiếu ngoại lệ

| Mã | Mức độ | Ngoại lệ còn thiếu | Bằng chứng trong `NV.docx` |
|---|---|---|---|
| **NV-NL01** | **Bắt buộc sửa** | **Thiếu ngoại lệ tắt Gợi ý / Hỏi Xiang trong các bài Kiểm tra mở khóa**:<br>*Mục 3 – Trường hợp đặc biệt* chỉ ghi *"Không có gợi ý trong bài đánh giá đầu vào và trong Thi thử"*, bỏ sót các bài kiểm tra mở khóa ở *Mục 6* (`Kiểm tra cuối thửa`, `Vượt thửa`, `Bắt đầu cấp`, `Vượt chặng`). Nếu cho dùng Gợi ý 2 mức và Hỏi Xiang trong các bài này sẽ làm sai lệch điều kiện mở khóa 10/10, 15/15. | *Mục 3 (Trường hợp đặc biệt)*, *Mục 6 (Bảng mở khóa)* |
| **NV-NL02** | **Bắt buộc sửa** | **Thiếu ngoại lệ khi lỗi phát âm thanh trong phòng Thi thử**:<br>Trong Thi thử không đổi đề/thay câu nhưng *AT19* chặn nộp tay khi còn câu trống. Nếu tệp audio bị lỗi tải mạng hoặc hỏng tệp, học viên không có lối thoát hợp lệ ngoài việc phải chọn bừa đáp án giả để nộp bài. | *Mục 7 (Hệ thống làm gì)*, *Phụ lục D (AT19)* đối chiếu *Mục 1 (Trường hợp đặc biệt)* |
| **NV-NL03** | **Bắt buộc sửa** | **Thiếu ngoại lệ khi mục tiêu HSK thấp hơn/bằng trình độ hiện tại, hoặc đã học xong 100% bài đang mở**:<br>*Mục 2* yêu cầu bám khoảng cách giữa trình độ hiện tại và mục tiêu, nhưng chưa có nhánh xử lý khi mục tiêu `≤` cấp đã mở, hoặc khi học viên đã đạt mọi bài trong phạm vi mở mà không có lỗi lặp lại lẫn không dùng gợi ý. | *Mục 1 (Kết quả)*, *Mục 2 (Hệ thống làm gì)* |
| **NV-NL04** | **Cải tiến tùy chọn** | **Chưa làm rõ tình huống phát sinh `Lỗi kỹ thuật` ở các câu không có audio (câu 1–4, 7–8)**:<br>*Mục 1* chỉ mô tả lỗi kỹ thuật cho audio (câu 5–6), trong khi *Phụ lục C* sinh tổ hợp trạng thái `Lỗi kỹ thuật` cho toàn bộ câu 1–8. Nên ghi rõ trên thực tế câu 1–4, 7–8 có thể nhận trạng thái `Lỗi kỹ thuật` khi nào (ví dụ lỗi tải hình hoặc lỗi chấm AI câu 7). | *Mục 1 (Trường hợp đặc biệt)*, *Phụ lục C (Nhóm 2)* |

---

### 1.4. Yêu cầu khó kiểm thử

| Mã | Mức độ | Yêu cầu & Lý do khó kiểm thử | Bằng chứng trong `NV.docx` |
|---|---|---|---|
| **NV-KT01** | **Bắt buộc sửa tiêu chí** | **AI gợi ý và Hỏi Xiang trước khi kiểm tra "không bao giờ nói ra đáp án / không giải hộ" (`AT14`, `AT15`)**:<br>Phản hồi tự do của LLM không tất định; kiểm tra khớp chuỗi đáp án không bắt được diễn giải đồng nghĩa, dịch toạc câu hỏi, hoặc loại trừ 3 đáp án sai. Cần quy định rõ cơ chế kỹ thuật có thể kiểm thử tất định: (1) backend không truyền đáp án đúng/lời giải vào prompt trước khi chấm, (2) bộ quy tắc hậu kiểm đầu ra cụ thể. | *Mục 3 (Hệ thống làm gì)*, *Phụ lục D (AT14, AT15)* |
| **NV-KT02** | **Bắt buộc sửa tiêu chí** | **AI chấm câu dịch "theo ý chính, không so chuỗi cứng" (`AT07`)**:<br>Kết quả gọi LLM thật có thể dao động giữa các lần chạy. Cần tách kiểm thử đơn vị (mock đầu ra AI để kiểm tra logic lưu/quy đổi điểm) và bộ câu chuẩn (golden test) với `temperature = 0` khi nghiệm thu thật. | *Mục 1 (Hệ thống làm gì)*, *Phụ lục D (AT07)* |
| **NV-KT03** | **Bắt buộc sửa tiêu chí** | **"Bài Nghe chỉ xuất bản khi có file âm thanh thật đã kiểm tra khớp lời thoại" (*Mục 9*)**:<br>Backend kiểm tra được sự tồn tại và tính hợp lệ của tệp âm thanh vật lý, nhưng không thể tự biết âm thanh *"khớp lời thoại"* nếu không có cờ xác nhận của Giảng viên hoặc mô-đun nhận dạng giọng nói. Cần chốt rõ đây là bước xác nhận có lưu vết của Giảng viên trước khi xuất bản. | *Mục 9 (đoạn 125)* |
| **NV-KT04** | **Cải tiến tùy chọn** | **Độ chính xác thời gian thực của màn "đang phân tích" (`AT09`) & quy mô tổ hợp `AT46`**:<br>- Cần quy định độ trễ cho phép của cơ chế polling giữa frontend và backend ở *AT09*.<br>- Ở *Phụ lục C*, câu *"4⁶ = 4.096 trường hợp... cộng trạng thái của câu 7–8 cho phần kết quả"* nên ghi rõ là kiểm độc lập (`4.096 + 16`) hay nhân tổ hợp (`4⁸ = 65.536`). | *Phụ lục A*, *Phụ lục C (Nhóm 2)*, *Phụ lục D (AT09, AT46)* |

---

## 2. Đối chiếu với Schema SQL và Mã nguồn hiện hành

> [!IMPORTANT]
> Dưới đây là các điểm xung đột trực tiếp giữa `NV.docx` với [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql) và mã nguồn trong `backend/` + `frontend/`, kèm đường dẫn tệp và dòng lệnh làm bằng chứng.

### 2.1. Đối chiếu Schema SQL ([xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql))

1. **[SQL-01] [Bắt buộc sửa] Ràng buộc `ck_luot_lam_pham_vi` chặn cấu trúc bài Đánh giá đầu vào 8 câu**
   - **Bằng chứng**: [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L283-L309) đối chiếu `NV.docx` *Mục 1*.
   - **Chi tiết**: Ràng buộc `ck_luot_lam_pham_vi` hiện ép `loai_boc_cau = 'danh_gia_dau_vao'` phải có `cap_do_id IS NOT NULL AND ky_nang IS NOT NULL`. Trong khi bài đánh giá đầu vào 8 câu là một lượt tổng hợp nhiều kỹ năng và thích ứng qua nhiều cấp HSK 1–4, không gắn cố định với 1 cấp hay 1 kỹ năng.

2. **[SQL-02] [Bắt buộc sửa] Bảng `cau_tra_loi` chưa lưu được 3 chiều dữ liệu học, cấp thực tế của câu và lịch sử thay câu lỗi audio**
   - **Bằng chứng**: [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L319-L342) đối chiếu `NV.docx` *Mục 1*, *Phụ lục A*, *Phụ lục B (CSDL)*, *AT02–AT03, AT33, AT45*.
   - **Chi tiết**:
     - Thiếu cột trạng thái thao tác (`chua_thao_tac`, `da_tra_loi`, `bo_qua`, `loi_ky_thuat`), cột `muc_ho_tro` (`khong_dung`, `goi_y_1`, `goi_y_2`, `da_xem_loi_giai`), cột lưu cấp thực tế đã dùng (khi trượt sang cấp dự phòng) và dấu vết xem lời giải sau khi chấm.
     - Ràng buộc `UNIQUE KEY uq_ctl_thu_tu (luot_lam_id, thu_tu)` ([xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L336)) chỉ cho phép đúng 1 bản ghi tại mỗi vị trí `1..8`. Nếu thay câu tại chỗ do lỗi audio (*AT33*) bằng cách ghi đè `cau_hoi_id` thì mất danh sách các câu đã từng phát lỗi trong lượt đó (không đảm bảo điều kiện *"không trùng câu đã dùng"* nếu thay nhiều lần); nếu giữ dòng cũ thì cần cơ chế lưu câu đã thay riêng hoặc nới khóa duy nhất theo câu đang hiệu lực.

3. **[SQL-03] [Bắt buộc sửa] Bảng `cau_hoi` và `bo_de` thiếu trường cho Gợi ý 2 mức, Nhóm kiến thức, Nguồn nội dung và phân loại câu Dịch**
   - **Bằng chứng**: [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L152-L197), [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L256-L258) đối chiếu `NV.docx` *Mục 1 (Câu 7)*, *Mục 2*, *Mục 3*, *Mục 9*, *Phụ lục B*.
   - **Chi tiết**:
     - `cau_hoi.dang` hiện gồm `('ngu_lieu','chon_mot','dung_sai','chon_bo_chung','sap_xep','dien_chu','viet_mo')`, chưa tách riêng dạng `dich_cau` (nếu dùng chung `viet_mo` sẽ trộn lẫn câu dịch Trung → Việt của Câu 7 với câu viết đoạn chữ Hán theo tranh/từ bắt buộc của đề thi HSK 3–4).
     - `cau_hoi` mới có 1 cột `goi_y` đơn lẻ ([xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L170)), chưa có Gợi ý mức 1 & mức 2.
     - Chưa có bảng danh mục `nhom_kien_thuc` và khóa ngoại từ `cau_hoi` (lưu ý `ck_cau_hoi_phan_loai` ở dòng 187–189 đang ép câu con `cau_cha_id IS NOT NULL` để trống `cap_do_id, ky_nang`, trong khi mỗi câu con lại cần gắn nhóm kiến thức riêng).
     - `cau_hoi` chưa có cột nguồn nội dung (*Mục 9*: soạn với AI, tự soạn, nguồn được phép dùng); còn trên `bo_de`, ràng buộc `ck_bo_de_de_thi` (dòng 256–258) đang cấm `loai <> 'de_thi'` có giá trị ở cột `nguon`.

4. **[SQL-04] [Bắt buộc sửa] Chưa có cấu trúc lưu trạng thái Phân tích AI của phiên, nhận định năng lực và liên kết câu bằng chứng**
   - **Bằng chứng**: [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L278-L312), [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L416-L430) đối chiếu `NV.docx` *Mục 1*, *Phụ lục A (Phân tích AI)*, *Phụ lục B*, *AT09, AT35–AT37, AT52*.
   - **Chi tiết**: Chưa có cột lưu trạng thái xử lý phân tích (`chua`, `dang`, `xong`, `loi`) và mốc bắt đầu phân tích để xét timeout (*AT35*); chưa có bảng lưu kết quả đánh giá đầu vào, mục tiêu ôn thi HSK của học viên (tách khỏi khảo sát cũ `ks_*`), nhận định theo kỹ năng và bảng nối nhận định – `cau_tra_loi_id` làm bằng chứng (*AT37*), cũng như thông tin phiên bản tiêu chí chấm để tái sử dụng điểm AI khi thử lại (*AT36*).

5. **[SQL-05] [Cải tiến tùy chọn] Script SQL cập nhật lẻ chưa đồng bộ vào `xianglingo_schema.sql`**
   - **Bằng chứng**: [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L90) đối chiếu [2026_11_18_nhat_ky_tao_tai_khoan.sql](file:///d:/HSK_AI/backend/scripts/2026_11_18_nhat_ky_tao_tai_khoan.sql#L3-L4).
   - **Chi tiết**: Giá trị `'tao_tai_khoan'` của `nhat_ky_quan_tri.hanh_dong` nằm ở script rời; nếu khởi tạo CSDL kiểm thử độc lập từ `xianglingo_schema.sql` (*Phụ lục C*) sẽ thiếu giá trị ENUM này.

---

### 2.2. Đối chiếu Mã nguồn Backend & Frontend

1. **[CODE-01] [Bắt buộc sửa] Xung đột quy tắc kỹ năng Viết (chỉ mở từ HSK 3) với câu 7–8 Đánh giá đầu vào (cần cả HSK 1–2) và chưa hỗ trợ AI chấm câu tự luận**
   - **Bằng chứng**: [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L16), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L263-L265), [lesson_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/lesson_service.py#L68-L69), [attempt_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/attempt_service.py#L258-L264) đối chiếu `NV.docx` *Mục 1 (Hệ thống làm gì)*, *AT07*.
   - **Chi tiết**:
     - `START_ORDER = {"nghe": 1, "doc": 1, "tu_vung": 1, "viet": 3}` quy định kỹ năng Viết chỉ có từ HSK 3 trở lên, nên ngân hàng hiện tại không có câu Dịch và Sắp xếp từ ở HSK 1–2 cho nhánh HSK 1 / HSK 2 của câu 7–8.
     - `lesson_service.start_lesson` đang chặn hoàn toàn bài có câu `viet_mo`; `attempt_service._submit_locked` ghi cứng `trang_thai = 'loi'` chờ Giảng viên chấm tay; thư mục `backend/app/integrations/openai/` và `backend/app/modules/grading/` đang trống 0 byte.

2. **[CODE-02] [Bắt buộc sửa] Chưa có Đánh giá đầu vào 8 câu; luồng Khảo sát 5 câu cũ đang lỗi gắn router và kiểm tra thiếu tuyến đường**
   - **Bằng chứng**: [router.py](file:///d:/HSK_AI/backend/app/api/router.py#L24-L44), [survey_service.py](file:///d:/HSK_AI/backend/app/modules/survey/services/survey_service.py#L1-L76), [StudentHomePage.jsx](file:///d:/HSK_AI/frontend/src/features/home/pages/StudentHomePage.jsx#L33-L38), [App.jsx](file:///d:/HSK_AI/frontend/src/app/App.jsx#L85-L91), [App.jsx](file:///d:/HSK_AI/frontend/src/app/App.jsx#L214) đối chiếu `NV.docx` *Mục 1*, *AT01, AT31, AT32*.
   - **Chi tiết**:
     - Dự án vẫn đang giữ trang `/khao-sat` (5 câu), chưa có module đánh giá đầu vào 8 câu; mặt khác `survey_router` chưa được đăng ký trong `router.py` nên `getSurvey` ở `StudentHomePage.jsx` hiện lỗi 404.
     - Logic chuyển hướng đầu vào chỉ đặt tại `StudentHomePage.jsx` (`/hoc-vien`). Nếu học viên mới đăng nhập từ `/on-luyen` hoặc `/thi-thu`, hàm `returnPathFor` trong `App.jsx` điều hướng thẳng tới `/on-luyen` hoặc `/thi-thu`, bỏ qua hoàn toàn bước phân luồng ưu tiên 1–4 của *Mục 1*.

3. **[CODE-03] [Bắt buộc sửa] Lỗ hổng vượt khóa bài học và lộ đáp án qua API học thử công khai (`/api/cong-khai/...`)**
   - **Bằng chứng**: [guest_practice.py](file:///d:/HSK_AI/backend/app/modules/practice/endpoints/guest_practice.py#L46-L54), [guest_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/guest_service.py#L59-L68), [guest_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/guest_service.py#L109-L126) đối chiếu `NV.docx` *Mục 3 (Trường hợp đặc biệt)*, *Mục 6 (Trường hợp đặc biệt)*, *Phụ lục C (Nhóm 1)*, *AT13*.
   - **Chi tiết**: `guest_service._scope` chỉ kiểm tra cấp mở mặc định (`HSK 1` với Nghe/Đọc/Từ vựng, `HSK 3` với Viết) mà không chặn các ô/thửa phía sau. Học viên có thể gọi trực tiếp `GET /api/cong-khai/on-luyen/bai/{ma_goc_id}` để mở mọi bài đang bị khóa trong cấp mở sẵn, và gọi `POST /api/cong-khai/on-luyen/bai/{ma_goc_id}/kiem-tra` để lấy trước `dap_an_id`, `dap_an_chap_nhan`, `giai_thich` ngay khi đang làm bài thật hoặc làm kiểm tra vượt.

4. **[CODE-04] [Bắt buộc sửa] Tự động lộ gợi ý xuống trình duyệt, chặn Hỏi Xiang trước kiểm tra, nhúng đáp án đúng vào prompt AI và giữ giao dịch CSDL mở khi gọi AI**
   - **Bằng chứng**: [lesson_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/lesson_service.py#L180-L182), [notebook_service.py](file:///d:/HSK_AI/backend/app/modules/mistake_notebook/services/notebook_service.py#L174-L175), [LessonPage.jsx](file:///d:/HSK_AI/frontend/src/features/practice/pages/LessonPage.jsx#L325), [question_context.py](file:///d:/HSK_AI/backend/app/modules/ai_tutor/services/question_context.py#L54-L58), [question_context.py](file:///d:/HSK_AI/backend/app/modules/ai_tutor/services/question_context.py#L90-L104), [xiang_chat.py](file:///d:/HSK_AI/backend/app/modules/ai_tutor/services/xiang_chat.py#L27-L34), [xiang_chat.py](file:///d:/HSK_AI/backend/app/modules/ai_tutor/services/xiang_chat.py#L102-L120) đối chiếu `NV.docx` *Mục 3*, *Phụ lục A*, *AT14–AT16*.
   - **Chi tiết**:
     - `lesson_service` và `notebook_service` gửi sẵn trường `goi_y` khi tải lượt làm và `LessonPage.jsx` hiển thị ngay trên giao diện trước khi học viên bấm.
     - `question_context.py` đang chặn `Hỏi Xiang` khi `xac_nhan_luc is None` (trái với *Mục 3* & *AT15*), đồng thời đưa sẵn `Đáp án đúng`, `Đáp án chấp nhận` và `Giải thích` vào prompt của LLM.
     - `xiang_chat.ask_xiang` mở giao dịch đọc trên `db` qua `build_context(db, ...)` nhưng **không gọi `db.rollback()` / `db.close()`** trước khi chờ gọi mạng tới OpenAI, vi phạm trực tiếp *Phụ lục A* (*"Không giữ giao dịch CSDL mở trong lúc chờ AI trả kết quả"*).

5. **[CODE-05] [Bắt buộc sửa] Đánh dấu sai toàn bộ cấp dưới thành "Đã vượt" khi đạt bài `Bắt đầu cấp`**
   - **Bằng chứng**: [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L114-L126), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L150-L151), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L168-L169) đối chiếu `NV.docx` *Mục 6 (Bảng mở khóa – Cấp kế tiếp)*.
   - **Chi tiết**: Hàm `level_passed_over` trong `path_view.py` xét `any(order.get(c, 0) > here for c in passed["bat_dau_cap"])` rồi gán `skip_until = len(lands)`, làm mọi thửa và từng bài chưa học ở các cấp dưới bị đổi trạng thái sang `"da_vuot"` ("Đã vượt"), trái trực tiếp với quy định ở *Mục 6* (*"không tự tạo kết quả hoàn thành hoặc đánh dấu từng bài/thửa là 'Đã vượt' nếu chưa có quy tắc tương ứng"*).

6. **[CODE-06] [Bắt buộc sửa] Giao diện khóa nội dung ẩn thông tin tiến độ còn thiếu & `path_view.py` gán cứng số câu bài ôn**
   - **Bằng chứng**: [PathMap.jsx](file:///d:/HSK_AI/frontend/src/features/practice/components/PathMap.jsx#L38-L40), [PathMap.jsx](file:///d:/HSK_AI/frontend/src/features/practice/components/PathMap.jsx#L117-L118), [LevelTestCard.jsx](file:///d:/HSK_AI/frontend/src/features/practice/components/LevelTestCard.jsx#L36-L51), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L17), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L140), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L180), [path_service.py](file:///d:/HSK_AI/backend/app/modules/practice_authoring/services/path_service.py#L329-L331) đối chiếu `NV.docx` *Mục 6*, *AT13*.
   - **Chi tiết**:
     - Ở cuối cấp đang mở, khi chưa xong hết các thửa (`!canStart`), `LevelTestCard.jsx`#L51 trả `null` làm ẩn hoàn toàn điều kiện mở và số thửa còn thiếu (`test.ly_do`); ở cấp đang khóa, lý do bị giấu trong thuộc tính `title`; ở ô bị khóa chỉ hiện câu tĩnh chung chung.
     - `path_service.py` cho phép Giảng viên xuất bản bài có `≥ 5` câu và cuối thửa `≥ 10` câu, nhưng `path_view.py`#L180 bỏ qua cột `so_cau` vừa đếm ở dòng 140 để trả cứng `5` hoặc `10`.

7. **[CODE-07] [Bắt buộc sửa] Thi thử lộ danh sách đề, còn mở các API chọn đề trực tiếp, chưa khóa lượt theo cấp, cho nộp câu trống và thiếu phím tắt**
   - **Bằng chứng**: [student_mock_tests.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/endpoints/student_mock_tests.py#L25-L39), [attempt_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/attempt_service.py#L58-L140), [attempt_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/attempt_service.py#L281-L289), [router.py](file:///d:/HSK_AI/backend/app/api/router.py#L27-L29), [exams/router.py](file:///d:/HSK_AI/backend/app/modules/exams/router.py#L1-L8), [attempts/router.py](file:///d:/HSK_AI/backend/app/modules/attempts/router.py#L1-L6), [App.jsx](file:///d:/HSK_AI/frontend/src/app/App.jsx#L158-L163), [ExamSessionPage.jsx](file:///d:/HSK_AI/frontend/src/features/mock_test/pages/ExamSessionPage.jsx#L187-L206) đối chiếu `NV.docx` *Mục 7*, *AT17–AT22, AT41–AT43*.
   - **Chi tiết**:
     - Vẫn đang mở công khai `GET /api/thi-thu/de`, `GET /api/thi-thu/de/{ma_goc_id}`, `POST /api/thi-thu/de/{ma_goc_id}/bat-dau` cùng 2 router thế hệ cũ `exams_router` và `attempts_router` (truy vấn schema cũ không còn tồn tại).
     - `attempt_service.start_attempt` chỉ kiểm tra lượt `dang_lam` trên cùng một `ma_goc_id`, chưa chặn mở song song nhiều đề trong cùng cấp (sẽ vi phạm *AT18* khi đổi sang bốc đề ngẫu nhiên theo cấp).
     - `submit_attempt` và `ExamSessionPage.jsx` cho phép nộp tay khi còn câu trống (trái *AT19*). Lưu ý cạnh biên: khi hết giờ, nếu đồng hồ client nhanh hơn server ~1 giây khiến `con_lai_giay > 0` lúc gọi `/nop`, backend nếu không xử lý đồng bộ thời gian sẽ chặn nhầm theo *AT19* thay vì tự nộp theo *AT20*.
     - `ExamSessionPage.jsx` chưa cài đặt điều hướng phím mũi tên, phím chọn đáp án và bảo vệ ô nhập chữ (*AT22, AT43*).

8. **[CODE-08] [Bắt buộc sửa] Sai lệch ngày tính Chuỗi ngày học (khi hết giờ muộn, khi bỏ qua hết câu) và chưa cố định múi giờ kết nối MySQL**
   - **Bằng chứng**: [attempt_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/attempt_service.py#L157-L158), [attempt_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/attempt_service.py#L275-L278), [path_view.py](file:///d:/HSK_AI/backend/app/modules/practice/services/path_view.py#L213-L225), [session.py](file:///d:/HSK_AI/backend/app/database/session.py#L12-L23) đối chiếu `NV.docx` *Mục 8*, *Điểm còn cần chốt*, *AT26*.
   - **Chi tiết**:
     - Khi lượt Thi thử quá giờ từ hôm trước nhưng hôm nay học viên mới mở lại trang, `_submit_locked` ghi `nop_luc = NOW()` thay vì thời điểm hết hạn `bat_dau_luc + INTERVAL thoi_luong_phut MINUTE`, làm cộng nhầm chuỗi ngày cho ngày hôm nay.
     - Truy vấn `streak_days` trong `path_view.py` cộng chuỗi cho mọi lượt `b.loai IN ('bai', 'cuoi_thua')` hoặc `l.loai_boc_cau = 'so_tay'` đã nộp kể cả khi học viên bấm **Bỏ qua hết tất cả các câu** (không trả lời câu nào), trái với *Mục 8* & *AT26*.
     - `session.py` chưa cấu hình `SET time_zone = '+07:00'` trên kết nối MySQL, khiến `CURDATE()` và `NOW()` phụ thuộc vào múi giờ hệ điều hành của máy chủ CSDL.

9. **[CODE-09] [Bắt buộc sửa] Khác biệt danh mục mốc KN với `NV.docx`, lỗi hiển thị KN ở lượt vượt trượt và thiếu lý do KN**
   - **Bằng chứng**: [skip_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/skip_service.py#L23-L25), [skip_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/skip_service.py#L197-L208), [skip_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/skip_service.py#L278-L289), [lesson_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/lesson_service.py#L150-L160), [notebook_service.py](file:///d:/HSK_AI/backend/app/modules/mistake_notebook/services/notebook_service.py#L184-L188), [xianglingo_schema.sql](file:///d:/HSK_AI/xianglingo_schema.sql#L384-L405) đối chiếu `NV.docx` *Mục 4*, *Mục 8*, *AT28*.
   - **Chi tiết**:
     - Đối chiếu công thức hiện hành theo yêu cầu của *Mục 8*: Code và CSDL hiện có thêm mốc **`kn_bat_dau_cap` (+20 KN, lần đầu đạt theo từng `cap_do_id × ky_nang`)** bên cạnh `kn_vuot_thua` (+20 KN theo `bo_de_goc_id`) và `kn_vuot_chang` (+20 KN theo từng `cap_do_id × ky_nang`). Bảng đối chiếu ở `NV.docx` *Mục 8* đang thiếu mốc `Bắt đầu cấp` và chưa ghi rõ phạm vi `cấp × kỹ năng` của vượt cấp.
     - **Lỗi bug trong `skip_service.get_skip`** (dòng 197–208): Truy vấn đọc `so_luong` từ `nhat_ky_thuong` không kiểm tra lượt hiện tại có đạt hay không và không lọc thời điểm nhận thưởng, dẫn tới lượt làm lại hoặc lượt trượt vẫn báo nhận `+20 KN` nếu trước đó học viên đã từng đạt mốc đó.
     - Các API tổng kết lượt làm chưa trả đủ 3 thông tin `(kn_nhan, ly_do, tong_kn_moi)` theo *Mục 4* và *AT28*.

10. **[CODE-10] [Bắt buộc sửa] Chưa có hàm chọn "Bài phù hợp hôm nay"; `roadmap_service.py` đang kết luận yếu chỉ từ 1 câu sai**
    - **Bằng chứng**: [roadmap_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/roadmap_service.py#L31), [roadmap_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/roadmap_service.py#L90-L123), [roadmap_service.py](file:///d:/HSK_AI/backend/app/modules/mock_tests/services/roadmap_service.py#L337), [PracticeHomePage.jsx](file:///d:/HSK_AI/frontend/src/features/practice/pages/PracticeHomePage.jsx#L11-L55) đối chiếu `NV.docx` *Mục 2*, *Mục 4*, *AT39, AT48–AT50*.
    - **Chi tiết**:
      - Chưa có hồ sơ năng lực tích lũy theo `kỹ năng × nhóm kiến thức` và chưa có khung *"Bài phù hợp với bạn hôm nay"* trên `PracticeHomePage.jsx`.
      - Trong `roadmap_service.py` (dành cho Thi thử), điều kiện `ty_le < 0.6` kết luận yếu ngay khi một nhóm chỉ có 1 câu và làm sai (`0/1`) hoặc có 2 câu và sai 1 câu (`1/2`), vi phạm *AT39*.

11. **[CODE-11] [Bắt buộc sửa] Cho phép xuất bản câu Nghe không có file âm thanh thật; chưa có luồng Giảng viên soạn nháp với AI**
    - **Bằng chứng**: [question_rules.py](file:///d:/HSK_AI/backend/app/modules/questions/services/question_rules.py#L21-L23), [question_status.py](file:///d:/HSK_AI/backend/app/modules/questions/services/question_status.py#L27-L41), [save_question.py](file:///d:/HSK_AI/backend/app/modules/questions/services/save_question.py#L48-L69) đối chiếu `NV.docx` *Mục 9*, *AT24*.
    - **Chi tiết**:
      - `question_rules._has_content` cho phép câu Nghe chỉ có `loi_nghe` (chữ) mà `tep_audio = None` vẫn hợp lệ và `publish_question` cho xuất bản thẳng mà không kiểm tra tệp âm thanh thật trên đĩa, trái với *Mục 9*.
      - `create_question` hiện gọi `validate_question` chặn cứng ngay khi lưu trạng thái `nhap`, nên nếu bản nháp do AI sinh thiếu đáp án/thành phần (*AT24*) sẽ không lưu được vào bảng `cau_hoi` trừ khi tách mức kiểm tra giữa lưu `nhap` và `publish_question`.

12. **[CODE-12] [Bắt buộc sửa] Giữ state thống kê của tài khoản trước khi chuyển tài khoản không tải lại trang (`AT29`)**
    - **Bằng chứng**: [StudentLayout.jsx](file:///d:/HSK_AI/frontend/src/layouts/StudentLayout.jsx#L15-L30) đối chiếu `NV.docx` *Phụ lục C (Nhóm 1)*, *AT29*.
    - **Chi tiết**: Khi đổi `token` giữa hai Học viên mà không F5, `StudentLayout.jsx` không đặt lại `stats` về `null` ngay lập tức nên vẫn hiển thị tạm KN, năng lượng và chuỗi ngày của Học viên trước trong lúc chờ API trả về.

13. **[CODE-13] [Cải tiến tùy chọn] Các điểm hoàn thiện cấu trúc code và bảo mật phiên hiện có**
    - **Bằng chứng**:
      - [router.py](file:///d:/HSK_AI/backend/app/api/router.py#L21-L22), [router.py](file:///d:/HSK_AI/backend/app/api/router.py#L42-L43): `search_router` bị import và `include_router` lặp 2 lần.
      - [token_issuer.py](file:///d:/HSK_AI/backend/app/security/token_issuer.py#L8-L15), [current_user.py](file:///d:/HSK_AI/backend/app/security/current_user.py#L29-L41), [profile_service.py](file:///d:/HSK_AI/backend/app/modules/account_profile/services/profile_service.py#L94): `profile_service` tăng `phien_ban_phien` khi đổi mật khẩu nhưng JWT chưa nhúng/đối chiếu `phien_ban_phien` để thu hồi phiên cũ.
      - [lesson_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/lesson_service.py#L241-L246), [skip_service.py](file:///d:/HSK_AI/backend/app/modules/practice/services/skip_service.py#L265-L271), [notebook_service.py](file:///d:/HSK_AI/backend/app/modules/mistake_notebook/services/notebook_service.py#L219-L234): Câu bấm `Bỏ qua` hiện bị ghi thẳng vào `so_tay` như câu sai; và trong `notebook_service.py` học viên vừa xem lời giải câu sai ở bài Ôn luyện xong vào ôn Sổ tay ngay lập tức vẫn được nâng từ `can_on` lên `cho_on_lai`.
      - Các module `practice`, `mock_tests`, `mistake_notebook`, `account_profile` hiện viết SQL trực tiếp trong tầng `services/` thay vì tách lớp `endpoints → services → repositories` như định hướng ở `NV.docx` *Phụ lục B (Code)*.
