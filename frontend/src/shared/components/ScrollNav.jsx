import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import "../styles/scrollNav.css";

// Nút nổi kiểu web hiện đại cho trang dài (cao hơn 1,5 màn hình):
// - Nút tròn chính có vòng tiến độ cuộn: ở nửa trên trang trỏ xuống (xuống cuối), cuộn quá nửa thì trỏ lên (lên đầu).
// Nút Quay lại nằm ở góc trên bên trái (BackButton trong thanh trên), không nằm ở đây.
const LONG = 1.5;
const R = 21, C = 2 * Math.PI * R;

export default function ScrollNav({ raised = false }) {
  const { pathname } = useLocation();
  const [s, setS] = useState({ long: false, p: 0 });

  useEffect(() => {
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const h = document.documentElement.scrollHeight, view = window.innerHeight;
        const room = Math.max(1, h - view);
        setS({ long: h > view * LONG, p: Math.min(1, Math.max(0, window.scrollY / room)) });
      });
    };
    measure();
    window.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null; // nội dung tải xong làm trang dài ra
    ro?.observe(document.body);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
      ro?.disconnect();
    };
  }, [pathname]);

  if (!s.long) return null;
  const up = s.p > 0.5;
  const behavior = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
  const jump = () => window.scrollTo({ top: up ? 0 : document.documentElement.scrollHeight, behavior });
  const label = up ? "Lên đầu trang" : "Xuống cuối trang";

  return (
    <nav className={`snav${raised ? " snav--raised" : ""}`} aria-label="Điều hướng trang">
      <button type="button" className="snav__main" onClick={jump} aria-label={label} data-tip={label}>
        <svg className="snav__ring" viewBox="0 0 48 48" aria-hidden="true">
          <circle className="snav__track" cx="24" cy="24" r={R} />
          <circle className="snav__bar" cx="24" cy="24" r={R} strokeDasharray={C} strokeDashoffset={C * (1 - s.p)} />
        </svg>
        <svg className={`snav__arrow${up ? " is-up" : ""}`} viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6" /></svg>
      </button>
    </nav>
  );
}
