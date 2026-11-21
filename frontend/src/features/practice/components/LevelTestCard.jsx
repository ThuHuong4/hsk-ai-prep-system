import { useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import "../styles/levelTest.css";

// Nút "Vượt cấp" (mục 4.2): trên cấp đang khóa = Bắt đầu cấp; cuối bản đồ cấp đang mở = Vượt chặng (chỉ hiện khi đủ điều kiện).
// Học viên xác nhận trước khi làm; không tốn năng lượng, không đếm ngược, giấu đáp án đến khi nộp.
export default function LevelTestCard({ test, level, skillLabel, busy, onStart }) {
  const [confirm, setConfirm] = useState(false);
  if (!test || !level) return null;
  const isStart = test.loai === "bat_dau_cap";

  const canStart = test.duoc_lam && !(test.da_dat && !test.luot_dang_lam);

  const dialog = (
        <div className="lt-dialog" role="dialog" aria-modal="true" aria-labelledby="lt-dlg">
          <div className="lt-dialog__box">
            <h2 id="lt-dlg">{isStart ? `Vượt cấp vào ${level.ten}?` : test.cap_ke ? `Vượt cấp lên ${test.cap_ke.ten}?` : `Hoàn thành lộ trình ${skillLabel}?`}</h2>
            <ul>
              <li>{isStart && test.cap_kiem_tra ? `${test.so_cau} câu kiến thức ${test.cap_kiem_tra.ten}` : `${test.so_cau} câu tổng hợp ${level.ten}`}, cần đúng tất cả trong một lượt.</li>
              <li>Đạt thì mở {isStart ? level.ten : test.cap_ke ? test.cap_ke.ten : "hoàn thành lộ trình"} cho kỹ năng {skillLabel}.</li>
              <li>Không tốn năng lượng, không giới hạn thời gian.</li>
              <li>Đáp án và Hỏi Xiang mở sau khi nộp. Thoát giữa chừng được giữ câu đã chọn.</li>
              <li>Chưa đạt thì giữ nguyên tiến độ, làm lại lúc nào cũng được.</li>
            </ul>
            <div className="lt-dialog__acts">
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setConfirm(false)}>Để sau</button>
              <button type="button" className="xc-btn xc-btn--sm" disabled={busy} onClick={() => { setConfirm(false); onStart(test); }}>
                Bắt đầu
              </button>
            </div>
          </div>
        </div>
  );

  // Cấp đang khóa: chỉ một nút "Vượt cấp", chi tiết nằm trong hộp xác nhận
  if (isStart) {
    return (
      <div className="lt-jump">
        <button type="button" className="xc-btn lt-jump__btn" disabled={busy || !canStart}
          title={canStart ? `Làm kiểm tra để mở ${level.ten}` : test.ly_do || ""}
          onClick={() => (test.luot_dang_lam ? onStart(test) : setConfirm(true))}>
          {test.luot_dang_lam ? "Làm tiếp vượt cấp" : "Vượt cấp"} <Icon name="arrow" size={18} />
        </button>
        {confirm && dialog}
      </div>
    );
  }

  // Cuối bản đồ cấp đang mở: chỉ hiện khi đủ điều kiện vượt cấp (đã xong/đã vượt hết các thửa)
  if (!canStart) return null;
  return (
    <div className="lt-jump lt-jump--end">
      <button type="button" className="xc-btn lt-jump__btn" disabled={busy}
        onClick={() => (test.luot_dang_lam ? onStart(test) : setConfirm(true))}>
        {test.luot_dang_lam ? "Làm tiếp vượt cấp" : test.cap_ke ? `Vượt cấp lên ${test.cap_ke.ten}` : "Hoàn thành lộ trình"} <Icon name="arrow" size={18} />
      </button>
      {confirm && dialog}
    </div>
  );
}
