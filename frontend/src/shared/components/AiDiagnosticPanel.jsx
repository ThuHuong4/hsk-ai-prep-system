/**
 * Bảng Chẩn đoán AI chuyên sâu (phong cách WriteMate.io & Cambridge Write & Improve).
 * Hỗ trợ 3 trạng thái:
 *  - `mode="ready"`: Hiển thị trước bộ 3 tiêu chí chấm của câu hiện tại để người học nắm rõ yêu cầu.
 *  - `mode="analyzing"`: Hiệu ứng quét tiêu chí theo thời gian thực trong lúc AI suy luận.
 *  - `mode="result"`: Thẻ kết quả đa tầng gồm Điểm độ hiểu, Nhãn chẩn đoán, Hộp đối chiếu Đáp án,
 *                     Thanh điểm 3 tiêu chí (Rubric), Phân tích chuyên sâu và Mẹo ghi nhớ nhanh.
 */
import Icon from "./Icon.jsx";
import "../styles/aiDiagnostic.css";

const PREVIEW_CRITERIA = {
  tu_vung: ["Nhận diện mặt chữ Hán", "Độ chuẩn nghĩa từ vựng", "Phản xạ từ vựng theo cấp"],
  doc: ["Nắm bắt từ khóa câu", "Liên kết ngữ cảnh đọc hiểu", "Độ chính xác thông tin"],
  nghe: ["Nhận diện âm & thanh điệu", "Bắt từ khóa hội thoại", "Khớp ngữ cảnh nghe"],
  viet_sap_xep: ["Trật tự Chủ – Vị – Tân", "Vị trí trạng ngữ & trợ từ", "Ngữ nghĩa toàn câu"],
  dich_cau: ["Độ chính xác ý nghĩa", "Từ vựng & Ngữ cảnh", "Diễn đạt tiếng Việt tự nhiên"],
};

function barTone(score, max = 10) {
  const ratio = max > 0 ? score / max : 0;
  if (ratio >= 0.7) return "high";
  if (ratio >= 0.4) return "mid";
  return "low";
}

export default function AiDiagnosticPanel({
  mode = "ready",
  step = null,
  result = null,
  finishedCap = null,
  autoRedirectSec = null,
  staticCard = false,
}) {
  const wrapperCls = `wm-inspector${staticCard ? " wm-inspector--static" : ""}${
    mode === "result" && result?.muc_danh_gia ? ` wm-inspector--${result.muc_danh_gia}` : ""
  }`;

  if (mode === "analyzing") {
    return (
      <aside className={wrapperCls} role="status" aria-live="polite">
        <div className="wm-inspector__top">
          <span className="wm-ai-badge">
            <span className="wm-pulse wm-pulse--live" />
            XIANG AI · ĐANG CHẨN ĐOÁN
          </span>
          {step?.cap_hien_thi && <span className="wm-pill">{step.cap_hien_thi}</span>}
        </div>

        <div>
          <h3 style={{ fontSize: "18px", marginBottom: "6px" }}>Đang phân tích sâu câu trả lời của bạn…</h3>
          <p className="xc-muted" style={{ fontSize: "13.5px" }}>
            Hệ thống đang đối chiếu đáp án chuẩn, chấm điểm từng tiêu chí và cập nhật hồ sơ điểm yếu cá nhân.
          </p>
        </div>

        <ul className="wm-scan-steps">
          <li className="wm-scan-step">
            <Icon name="spark" size={17} />
            <span>1. Đối chiếu ngữ nghĩa & cấu trúc HSK gốc</span>
          </li>
          <li className="wm-scan-step">
            <Icon name="chart" size={17} />
            <span>2. Chấm điểm 3 tiêu chí thành phần (Rubric)</span>
          </li>
          <li className="wm-scan-step">
            <Icon name="route" size={17} />
            <span>3. Đánh dấu lỗ hổng để ưu tiên bài ôn tương ứng</span>
          </li>
        </ul>

        <div style={{ display: "grid", gap: "8px" }} aria-hidden="true">
          <div className="wm-shimmer" style={{ width: "92%" }} />
          <div className="wm-shimmer" style={{ width: "76%" }} />
          <div className="wm-shimmer" style={{ width: "64%" }} />
        </div>
      </aside>
    );
  }

  if (mode === "ready") {
    const dang = step?.cau_hoi?.dang;
    const key = dang === "dich_cau" || dang === "viet_mo"
      ? "dich_cau"
      : dang === "sap_xep"
        ? "viet_sap_xep"
        : (step?.ky_nang || "tu_vung");
    const previewList = PREVIEW_CRITERIA[key] || PREVIEW_CRITERIA.tu_vung;

    return (
      <aside className={wrapperCls}>
        <div className="wm-inspector__top">
          <span className="wm-ai-badge">
            <span className="wm-pulse" />
            XIANG AI · GIÁM KHẢO TRỰC TIẾP
          </span>
          {step?.cap_hien_thi && <span className="wm-pill">Mốc thăm dò {step.cap_hien_thi}</span>}
        </div>

        <div>
          <h3 style={{ fontSize: "18px", marginBottom: "6px" }}>Tiêu chí đánh giá ở câu {step?.thu_tu || 1}</h3>
          <p className="xc-muted" style={{ fontSize: "13.5px", lineHeight: 1.5 }}>
            Ngay khi bạn xác nhận câu trả lời hoặc bấm <b>Bỏ qua</b>, AI sẽ phân tích chi tiết mức độ hiểu bài theo 3 tiêu chí dưới đây:
          </p>
        </div>

        <div className="wm-rubric">
          <span className="wm-rubric__title">Thang tiêu chí chẩn đoán (0 – 10)</span>
          {previewList.map((name) => (
            <div key={name} className="wm-rubric__row">
              <div className="wm-rubric__meta">
                <span>{name}</span>
                <span className="xc-muted">Chờ chấm</span>
              </div>
              <div className="wm-rubric__bar wm-rubric__bar--idle">
                <i style={{ width: "18%" }} />
              </div>
            </div>
          ))}
        </div>

        <div className="wm-note-block">
          <strong>Quy tắc khảo sát trung thực</strong>
          Biết câu nào bạn trả lời câu đó để AI đo độ hiểu thực tế. Nếu chưa từng gặp từ hoặc cấu trúc này, hãy bấm{" "}
          <b>Bỏ qua</b> — AI sẽ ghi nhận đúng là <b>Chưa biết</b> để mở khóa đúng trình độ và ưu tiên bài bù lỗ hổng cho bạn.
        </div>
      </aside>
    );
  }

  if (!result) return null;

  const isSkip = result.trang_thai_thao_tac === "bo_qua";
  const isTech = result.trang_thai_thao_tac === "loi_ky_thuat";
  const isTranslation = result.dang === "dich_cau" || result.dang === "viet_mo";
  const verdictTone = result.muc_danh_gia || (isSkip ? "chua_biet" : result.dung ? "vung" : "can_cung_co");

  const ringPrimary = isTech
    ? "—"
    : isTranslation && !isSkip && result.diem != null
      ? `${result.diem}/${result.diem_toi_da || 10}`
      : result.diem_do_hieu != null
        ? `${result.diem_do_hieu}%`
        : result.dung
          ? "100%"
          : "0%";

  const ringLabel = isTech
    ? "Loại trừ"
    : isSkip
      ? "Chưa biết"
      : result.dung
        ? "Đạt chuẩn"
        : "Cần bù";

  const headline = isTech
    ? "Sự cố kỹ thuật âm thanh / hiển thị"
    : isSkip
      ? "Ghi nhận lỗ hổng chưa học"
      : result.dung
        ? "Làm chủ vững điểm kiến thức này"
        : "Phát hiện điểm yếu cần ưu tiên bù";

  const criteria = Array.isArray(result.tieu_chi) ? result.tieu_chi : [];
  const explanationText = result.phan_tich_ai || result.nhan_xet || "";

  return (
    <aside className={wrapperCls} aria-live="polite">
      <div className="wm-inspector__top">
        <span className="wm-ai-badge">
          <Icon name="spark" size={14} />
          KẾT QUẢ CHẨN ĐOÁN AI
        </span>
        <span className="wm-pill">
          {result.cap || "HSK"}
          {result.nhom_kien_thuc ? ` · ${result.nhom_kien_thuc}` : ""}
        </span>
      </div>

      {/* Tầng 1: Điểm độ hiểu & Nhãn phân loại kiểu WriteMate */}
      <div className="wm-verdict">
        <div className={`wm-score-ring wm-score-ring--${verdictTone}`}>
          <strong>{ringPrimary}</strong>
          <small>{ringLabel}</small>
        </div>
        <div className="wm-verdict__body">
          {result.nhan_chan_doan && <span className="wm-verdict__tag">{result.nhan_chan_doan}</span>}
          <h3>{headline}</h3>
          <p>
            Câu {result.thu_tu}/8 · Kỹ năng {result.ten_ky_nang || result.ky_nang}
          </p>
        </div>
      </div>

      {/* Tầng 2: Hộp đối chiếu trực quan Bài làm vs Đáp án chuẩn */}
      {!isTech && (
        <div className="wm-diff">
          <div
            className={`wm-diff__box${
              isSkip ? " wm-diff__box--skip" : !result.dung ? " wm-diff__box--wrong" : ""
            }`}
          >
            <span className="wm-diff__label">Bài làm của bạn</span>
            <span className="wm-diff__val">
              {isSkip ? "Bỏ qua (Chưa biết)" : result.tra_loi || "—"}
            </span>
          </div>

          <div className="wm-diff__box wm-diff__box--model">
            <span className="wm-diff__label">Đáp án chuẩn</span>
            <span className="wm-diff__val">{result.cau_sua || result.dap_an_dung || "—"}</span>
            {result.dich_nghia && !isTranslation && (
              <span className="wm-diff__sub">Nghĩa: {result.dich_nghia}</span>
            )}
            {result.loi_nghe && (
              <span className="wm-diff__sub">
                Lời nghe: <b className="hz">{result.loi_nghe}</b>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Tầng 3: Thanh điểm 3 tiêu chí thành phần (Rubric Breakdown) */}
      {criteria.length > 0 && (
        <div className="wm-rubric">
          <span className="wm-rubric__title">Chi tiết tiêu chí đánh giá</span>
          {criteria.map((c) => {
            const maxVal = c.toi_da || 10;
            const pct = Math.max(4, Math.round((100 * c.diem) / maxVal));
            return (
              <div key={c.ten} className="wm-rubric__row">
                <div className="wm-rubric__meta">
                  <span>{c.ten}</span>
                  <span>
                    {c.diem}/{maxVal}
                  </span>
                </div>
                <div className={`wm-rubric__bar wm-rubric__bar--${barTone(c.diem, maxVal)}`}>
                  <i style={{ width: `${c.diem === 0 ? 0 : pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Tầng 4: Nhận xét chẩn đoán sâu & Mẹo ghi nhớ */}
      <div className="wm-notes">
        {explanationText && (
          <div className="wm-note-block">
            <strong>Phân tích chuyên sâu</strong>
            {explanationText}
          </div>
        )}
        {(result.meo_ghi_nho || result.ly_do_sua) && (
          <div className="wm-note-block wm-note-block--tip">
            <strong>Gợi ý cải thiện & Ghi nhớ</strong>
            {result.meo_ghi_nho || result.ly_do_sua}
          </div>
        )}
      </div>

      {/* Thông báo tự động vào Trang chủ khi hoàn tất câu 8/8 */}
      {finishedCap && (
        <div className="wm-finish-banner">
          <strong>✓ Đã xác định trình độ: {finishedCap.ten}</strong>
          <span style={{ fontSize: "13.5px" }}>
            Hệ thống đã mở khóa lộ trình phù hợp và xếp ưu tiên các bài ôn theo đúng điểm yếu của bạn.
            {autoRedirectSec != null ? ` Tự động vào Trang chủ sau ${autoRedirectSec} giây…` : ""}
          </span>
        </div>
      )}
    </aside>
  );
}
