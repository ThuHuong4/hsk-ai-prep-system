import xiang from "../../../assets/images/xiang/home/xiang_full.webp";
import "../styles/rank.css";

// Huy hiệu danh hiệu: ảnh Xiang trong khung tròn, khung/màu/hiệu ứng theo bậc (1–7).
// locked: bậc chưa đạt (xám, có ổ khóa); still: tắt hiệu ứng động (dùng cho danh sách nhỏ).
export default function RankBadge({ bac, size = 96, locked = false, still = false, title }) {
  const stars = !locked && bac >= 5 ? [0, 1, 2, 3].slice(0, bac - 3) : [];
  return (
    <span className={`rk rk--${bac}${locked ? " is-locked" : ""}${still ? " is-still" : ""}`} style={{ "--rk": `${size}px` }}
      role="img" aria-label={title || `Huy hiệu bậc ${bac}`} title={title}>
      <span className="rk__ring" aria-hidden="true" />
      <span className="rk__disc" aria-hidden="true">
        <img src={xiang} alt="" draggable="false" />
      </span>
      {stars.map((s) => <span key={s} className={`rk__star rk__star--${s}`} aria-hidden="true">✦</span>)}
      {locked && (
        <span className="rk__lock" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z" /></svg>
        </span>
      )}
    </span>
  );
}
