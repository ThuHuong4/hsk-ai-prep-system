import { useState } from "react";

import Icon from "../../../shared/components/Icon.jsx";
import "../styles/levelTest.css";

// Thẻ hướng dẫn rõ chữ & nút mở bài kiểm tra "Bắt đầu cấp" (trên cấp đang khóa) hoặc "Vượt chặng" (cuối bản đồ cấp đang mở).
export default function LevelTestCard({ test, level, skillLabel, busy, onStart }) {
  const [confirm, setConfirm] = useState(false);
  if (!test || !level) return null;
  const isStart = test.loai === "bat_dau_cap";
  const canStart = test.duoc_lam && !(test.da_dat && !test.luot_dang_lam);

  const dialog = (
    <div className="lt-dialog" role="dialog" aria-modal="true" aria-labelledby="lt-dlg">
      <div className="lt-dialog__box">
        <h2 id="lt-dlg">
          {isStart
            ? `Làm bài kiểm tra mở khóa ${level.ten} (${skillLabel})?`
            : test.cap_ke
              ? `Làm bài kiểm tra vượt cấp lên ${test.cap_ke.ten}?`
              : `Hoàn thành lộ trình ${skillLabel}?`}
        </h2>
        <ul>
          <li>
            {isStart && test.cap_kiem_tra
              ? `Gồm ${test.so_cau} câu kiểm tra kiến thức ${test.cap_kiem_tra.ten}`
              : `Gồm ${test.so_cau} câu tổng hợp toàn cấp ${level.ten}`}
            , cần trả lời đúng tất cả các câu trong một lượt.
          </li>
          <li>
            Nếu đạt sẽ mở khóa ngay{" "}
            <b>{isStart ? level.ten : test.cap_ke ? test.cap_ke.ten : "hoàn thành lộ trình"}</b> cho kỹ năng{" "}
            <b>{skillLabel}</b>.
          </li>
          <li>Không tốn năng lượng và không giới hạn thời gian làm bài.</li>
          <li>Đáp án và Trợ giảng Xiang mở sau khi nộp. Nếu chưa đạt vẫn giữ nguyên tiến độ, được làm lại bất cứ lúc nào.</li>
        </ul>
        <div className="lt-dialog__acts">
          <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setConfirm(false)}>
            Để sau
          </button>
          <button
            type="button"
            className="xc-btn xc-btn--sm"
            disabled={busy}
            onClick={() => {
              setConfirm(false);
              onStart(test);
            }}
          >
            Bắt đầu kiểm tra
          </button>
        </div>
      </div>
    </div>
  );

  // 1. Khi người dùng bấm sang tab cấp đang khóa (ví dụ HSK 3 hoặc HSK 4): hiện rõ chữ lý do khóa & cách mở
  if (isStart) {
    return (
      <>
        <div className="lt-card lt-card--start">
          <span className="lt-ico" aria-hidden="true">
            <Icon name="lock" size={20} />
          </span>
          <div className="lt-body">
            <h2>
              {level.ten} · Kỹ năng {skillLabel} hiện đang khóa
            </h2>
            {canStart ? (
              <p>
                Để mở sớm <b>{level.ten}</b> cho riêng kỹ năng {skillLabel}, bạn có thể làm bài kiểm tra gồm{" "}
                <b>
                  {test.so_cau} câu kiến thức {test.cap_kiem_tra?.ten}
                </b>{" "}
                (đúng cả {test.so_cau}/{test.so_cau} câu). Hoặc vào mục <b>Thi thử</b> đạt điểm chuẩn của trình độ hiện
                tại để nâng trình độ và mở khóa đồng loạt cả 4 kỹ năng lên {level.ten}.
              </p>
            ) : (
              <p>{test.ly_do || `Bạn cần hoàn thành mở khóa cấp liền trước mới có thể thi mở ${level.ten}.`}</p>
            )}
          </div>
          {canStart && (
            <button
              type="button"
              className="xc-btn xc-btn--sm"
              disabled={busy}
              onClick={() => (test.luot_dang_lam ? onStart(test) : setConfirm(true))}
            >
              {test.luot_dang_lam ? "Làm tiếp bài vượt cấp" : `Thi mở ${level.ten}`} <Icon name="arrow" size={16} />
            </button>
          )}
        </div>
        {confirm && dialog}
      </>
    );
  }

  // 2. Cuối bản đồ của cấp đang mở (ví dụ cuối HSK 2): LUÔN hiện rõ chữ điều kiện lên cấp tiếp theo (không ẩn đi nữa)
  return (
    <>
      <div className={`lt-card lt-jump--end${test.da_dat ? " is-done" : ""}`}>
        <span className="lt-ico" aria-hidden="true">
          <Icon name={test.da_dat ? "check" : "layers"} size={20} />
        </span>
        <div className="lt-body">
          <h2>
            {test.da_dat
              ? `Đã hoàn thành vượt cấp ${level.ten} (${skillLabel})`
              : test.cap_ke
                ? `Mục tiêu tiếp theo: Mở khóa lên ${test.cap_ke.ten} (${skillLabel})`
                : `Chốt lộ trình ${level.ten} (${skillLabel})`}
          </h2>
          {test.da_dat ? (
            <p>
              Bạn đã vượt qua bài kiểm tra cuối cấp {level.ten}
              {test.cap_ke ? ` và mở khóa ${test.cap_ke.ten} cho kỹ năng ${skillLabel}.` : "."}
            </p>
          ) : canStart ? (
            <p>
              Bạn đã hoàn thành toàn bộ các thửa của {level.ten}. Hãy làm bài kiểm tra tổng hợp{" "}
              <b>{test.so_cau} câu</b> (cần đúng {test.so_cau}/{test.so_cau}) để mở khóa{" "}
              <b>{test.cap_ke ? test.cap_ke.ten : "hoàn thành lộ trình"}</b>!
            </p>
          ) : (
            <p>
              {test.ly_do ? `${test.ly_do} để mở bài kiểm tra vượt cấp (${test.so_cau} câu)` : ""}
              {test.cap_ke
                ? `. Bạn cũng có thể bấm sang tab "${test.cap_ke.ten}" phía trên để thi mở sớm 10 câu, hoặc vào mục "Thi thử" đạt chuẩn ${level.ten} để nâng trình độ lên ${test.cap_ke.ten}.`
                : "."}
            </p>
          )}
        </div>
        {canStart && (
          <button
            type="button"
            className="xc-btn xc-btn--sm"
            disabled={busy}
            onClick={() => (test.luot_dang_lam ? onStart(test) : setConfirm(true))}
          >
            {test.luot_dang_lam
              ? "Làm tiếp bài vượt cấp"
              : test.cap_ke
                ? `Thi lên ${test.cap_ke.ten}`
                : "Hoàn thành lộ trình"}{" "}
            <Icon name="arrow" size={16} />
          </button>
        )}
      </div>
      {confirm && dialog}
    </>
  );
}
