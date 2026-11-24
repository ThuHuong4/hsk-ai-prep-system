import { Link } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import Icon from "../../../shared/components/Icon.jsx";
import ScrollNav from "../../../shared/components/ScrollNav.jsx";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import "../../../layouts/staffShell.css";
import "../../lecturer/styles/lecturer.css";
import "../styles/mockTest.css";

export { readTheme } from "../../../shared/hooks/useTheme.js";

/**
 * Khung Phòng thi & Xem kết quả:
 * - Chế độ thường (`workstation = false`): dùng cho Phiếu kết quả sau khi nộp, có nút `←` góc trên trái + nút cuộn tròn `ScrollNav` đồng bộ toàn hệ thống.
 * - Chế độ Trạm thi HSK iBT (`workstation = true`): toàn màn hình cố định `100dvh`, khóa chuột phải & sao chép đề (`Ctrl+C`),
 *   thanh đỉnh chuẩn máy thi `HSK机考`.
 */
export default function ExamShell({
  title,
  right,
  children,
  onBack = null,
  backLabel = "Quay lại",
  workstation = false,
  candidate = null,
  center = null,
  fontScale = "md",
  onFontScaleChange = null,
  isFullscreen = false,
  onToggleFullscreen = null,
}) {
  const [theme, toggle] = useTheme();

  if (workstation) {
    return (
      <div
        className={`xg xt xt--workstation xt--font-${fontScale}`}
        data-theme={theme}
        onContextMenu={(e) => e.preventDefault()}
        onCopy={(e) => e.preventDefault()}
        onCut={(e) => e.preventDefault()}
      >
        <header className="ibt-ws-top">
          <div className="ibt-ws-candidate">
            <span className="ibt-ws-avatar" aria-hidden="true">
              <img src={xiangFace} alt="" />
            </span>
            <div className="ibt-ws-candidate__meta">
              <strong>{candidate?.name || "Thí sinh"}</strong>
              <span>
                {candidate?.code || "HSK iBT"}
                {candidate?.saveText ? ` · ${candidate.saveText}` : ""}
              </span>
            </div>
          </div>

          <div className="ibt-ws-center">{center || <span className="ibt-ws-title">{title}</span>}</div>

          <div className="ibt-ws-right">
            {onFontScaleChange && (
              <div className="ibt-ws-font" role="group" aria-label="Cỡ chữ đề thi">
                {[
                  ["md", "A"],
                  ["lg", "A+"],
                  ["xl", "A++"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    className={`ibt-ws-font__btn${fontScale === key ? " is-on" : ""}`}
                    onClick={() => onFontScaleChange(key)}
                    title="Đổi cỡ chữ Hán hiển thị"
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
            {right}
            {onToggleFullscreen && (
              <button
                type="button"
                className="ibt-ws-iconbtn"
                onClick={onToggleFullscreen}
                title={isFullscreen ? "Đang ở chế độ Toàn màn hình" : "Bật Toàn màn hình phòng thi"}
                aria-label="Toàn màn hình phòng thi"
              >
                <span style={{ fontSize: "15px", fontWeight: 800, lineHeight: 1 }}>{isFullscreen ? "❐" : "⛶"}</span>
              </button>
            )}
            <button
              type="button"
              className="ibt-ws-iconbtn"
              onClick={toggle}
              aria-label={theme === "dark" ? "Giao diện sáng" : "Giao diện tối"}
              title={theme === "dark" ? "Chuyển nền sáng" : "Chuyển nền tối"}
            >
              <Icon name={theme === "dark" ? "sun" : "moon"} size={17} />
            </button>
          </div>
        </header>
        <div className="ibt-ws-body">{children}</div>
      </div>
    );
  }

  return (
    <div className="xg xt" data-theme={theme}>
      <header className="xt-top">
        {onBack && (
          <button
            type="button"
            className="xg-icon-btn ibt-icon-tip"
            onClick={onBack}
            data-tip={backLabel}
            aria-label={backLabel}
          >
            <Icon name="arrowLeft" size={18} />
          </button>
        )}
        <Link
          to="/hoc-vien"
          replace
          className="xt-brand"
          aria-label="Xianglingo – về trang Học viên"
          title="Về Trang chủ Học viên"
        >
          <span className="xg-brand__face">
            <img src={xiangFace} alt="" />
          </span>
        </Link>
        <span className="xt-top__title">{title}</span>
        <span className="xt-top__right">
          {right}
          <button
            type="button"
            className="xg-icon-btn"
            onClick={toggle}
            aria-label={theme === "dark" ? "Giao diện sáng" : "Giao diện tối"}
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
        </span>
      </header>
      <div className="xt-body">{children}</div>
      <ScrollNav />
    </div>
  );
}
