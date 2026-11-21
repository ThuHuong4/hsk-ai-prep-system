import { useEffect, useRef, useState } from "react";

import { formatDateTime } from "../../lecturer/utils/labels.js";

// Điểm từng lượt (cũ → mới) của một cấp, có vạch mốc đạt. Một trục, đường mảnh, rê chuột/chạm để xem chi tiết.
const H = 230, L = 40, R = 16, T = 14, B = 30;

export default function ScoreChart({ attempts, max, pass }) {
  const [hover, setHover] = useState(null);
  const box = useRef(null);
  const [W, setW] = useState(640); // vẽ theo đúng bề rộng thật để chữ trục không phóng to/thu nhỏ theo khung
  useEffect(() => {
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const n = attempts.length;
  const x = (i) => (n === 1 ? L + (W - L - R) / 2 : L + (i * (W - L - R)) / (n - 1));
  const y = (v) => T + (1 - v / max) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(f * max));
  const step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((W - L - R) / 48)))); // nhãn trục x thưa khi nhiều lượt
  const path = attempts.map((a, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(a.tong_diem).toFixed(1)}`).join(" ");
  const cur = hover != null ? attempts[hover] : null;
  const slot = n === 1 ? W - L - R : (W - L - R) / (n - 1);

  return (
    <div className="st-chart" ref={box} onMouseLeave={() => setHover(null)}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Điểm ${n} lượt gần nhất, mốc đạt ${pass} trên ${max}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="st-grid" x1={L} x2={W - R} y1={y(t)} y2={y(t)} />
            <text className="st-axis" x={L - 8} y={y(t) + 4} textAnchor="end">{t}</text>
          </g>
        ))}
        <line className="st-pass" x1={L} x2={W - R} y1={y(pass)} y2={y(pass)} />
        <text className="st-pass-label" x={W - R} y={y(pass) - 6} textAnchor="end">Mốc đạt {pass}</text>
        {attempts.map((_, i) => (i % step === 0 || i === n - 1) && (
          <text key={i} className="st-axis" x={x(i)} y={H - 8} textAnchor="middle">{i + 1}</text>
        ))}
        {cur && <line className="st-cross" x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} />}
        {n > 1 && <path className="st-line" d={path} />}
        {attempts.map((a, i) => (
          <circle key={a.id} className={`st-dot${a.dat ? " is-pass" : ""}${hover === i ? " is-on" : ""}`} cx={x(i)} cy={y(a.tong_diem)} r={hover === i ? 6 : 4.5} />
        ))}
        {attempts.map((a, i) => (
          <rect key={`h${a.id}`} className="st-hit" x={x(i) - slot / 2} y={T} width={slot} height={H - T - B}
            tabIndex={0} aria-label={`Lượt ${i + 1}: ${a.tong_diem.toFixed(0)} điểm, ${a.dat ? "đạt" : "chưa đạt"}`}
            onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} onTouchStart={() => setHover(i)} onBlur={() => setHover(null)} />
        ))}
      </svg>
      {cur && (
        <div className={`st-tip${hover > n / 2 ? " is-left" : ""}`} style={{ left: x(hover), top: y(cur.tong_diem) }}>
          <strong>Lượt {hover + 1} · {cur.tong_diem.toFixed(0)}/{max}</strong>
          <span>{cur.ten_de}</span>
          <span>{formatDateTime(cur.nop_luc)} · {cur.dat ? "Đạt" : "Chưa đạt"}</span>
        </div>
      )}
      <p className="st-legend"><span className="st-key st-key--pass" /> Lượt đạt <span className="st-key" /> Lượt chưa đạt <span className="st-key st-key--line" /> Mốc đạt</p>
    </div>
  );
}
