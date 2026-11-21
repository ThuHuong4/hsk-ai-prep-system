import { useEffect } from "react";
import { createPortal } from "react-dom";

import RankBadge from "./RankBadge.jsx";
import "../styles/rank.css";

const COLORS = ["#2ab3a6", "#f2795b", "#f6c344", "#5b8def", "#9b6ee8"];

// Chúc mừng lên bậc: huy hiệu phóng to, pháo giấy rơi. Esc hoặc bấm nền để đóng.
// Gắn vào khung .xg (giữ biến màu) thay vì trong thanh trên: thanh trên có backdrop-filter làm position: fixed bị giới hạn.
export default function LevelUpDialog({ rank, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const pieces = Array.from({ length: 44 }, (_, i) => i);
  const host = document.querySelector(".xg") || document.body;
  return createPortal(
    <div className="lvup" role="dialog" aria-modal="true" aria-label={`Lên bậc ${rank.ten}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="lvup__confetti" aria-hidden="true">
        {pieces.map((i) => (
          <i key={i} style={{ left: `${(i * 37) % 100}%`, background: COLORS[i % COLORS.length],
            animationDelay: `${(i % 11) * 0.12}s`, animationDuration: `${2.4 + (i % 5) * 0.35}s` }} />
        ))}
      </div>
      <div className="lvup__box">
        <div className="lvup__badge"><RankBadge bac={rank.bac} size={150} /></div>
        <p className="lvup__eyebrow">Lên bậc mới!</p>
        <p className="lvup__zh">{rank.zh}</p>
        <h2>Chúc mừng! Bạn đã đạt bậc <span>{rank.ten}</span></h2>
        <p className="lvup__sub">{rank.next ? `Tiếp theo: ${rank.next.ten} (còn ${rank.con_thieu} KN)` : "Bạn đã đạt danh hiệu cao nhất của Xianglingo."}</p>
        <button type="button" className="lvup__btn" onClick={onClose} autoFocus>Tiếp tục</button>
      </div>
    </div>,
    host,
  );
}
