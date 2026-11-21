import { useEffect, useRef, useState } from "react";

import xiangFull from "../../../assets/images/xiang/home/xiang_full.webp";
import Icon from "../../../shared/components/Icon.jsx";

const OFFSETS = [0, -78, 0, 78, 0]; // vị trí ngang của ô 1–5 (đường ruộng uốn lượn)
const STEP = 96;
const TOP = 40;
const STATE_TEXT = {
  chua_hoc: "Chưa học", dang_lam: "Đang làm dở", chua_dat: "Chưa đạt", da_xong: "Đã xong", da_vuot: "Đã vượt", khoa: "Chưa mở",
};

function Sprout() {
  return (
    <svg viewBox="0 0 40 40" className="sp-sprout" aria-hidden="true">
      <path d="M20 36V18" /><path d="M20 22c-8 0-12-5-12-12 8 0 12 5 12 12zM20 18c0-7 4-12 12-12 0 7-4 12-12 12z" />
    </svg>
  );
}

function Reeds({ side }) {
  return (
    <svg viewBox="0 0 50 50" className={`sp-reeds sp-reeds--${side}`} aria-hidden="true">
      <path d="M10 48C12 30 8 18 4 10M22 48c0-16 2-26 4-36M34 48c-1-14 3-24 10-32" />
      <circle cx="4" cy="9" r="3" /><circle cx="26" cy="10" r="3" /><circle cx="44" cy="15" r="3" />
    </svg>
  );
}

function actionLabel(slot) {
  if (slot.trang_thai === "dang_lam") return "Tiếp tục";
  if (slot.trang_thai === "chua_dat") return "Làm lại bài";
  if (slot.trang_thai === "da_xong") return "Ôn lại";
  if (slot.trang_thai === "da_vuot") return "Học bài này";
  return "Bắt đầu";
}

function ruleText(slot) {
  const need = slot.loai === "cuoi_thua" ? "10 câu, đúng cả 10 mới qua thửa." : "5 câu, đúng hết mới qua ô.";
  if (slot.trang_thai === "da_xong") return "Đã xong. Ôn lại không tốn năng lượng và không cộng KN.";
  if (slot.trang_thai === "da_vuot") return "Bạn đã vượt qua bài này bằng kiểm tra. Học lại không tốn năng lượng.";
  if (slot.trang_thai === "dang_lam") return `${need} Bạn đang làm dở, các câu đã kiểm tra được giữ nguyên.`;
  return `${need} Sai hoặc bỏ qua −1 năng lượng.`;
}

export default function PathMap({ lands, currentId, onStart, onSkip, busy, lockText }) {
  const [open, setOpen] = useState(null);
  const boardRef = useRef(null);

  useEffect(() => {
    boardRef.current?.querySelector(".sp-node.is-current")?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [currentId]);
  useEffect(() => {
    const close = (e) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  return (
    <div className="sp-board" ref={boardRef}>
      {lands.map((land, li) => {
        const height = TOP + STEP * 4 + 90;
        const points = OFFSETS.map((x, i) => [160 + x, TOP + 34 + i * STEP]);
        const d = points.reduce((acc, [x, y], i) => {
          if (i === 0) return `M160 0 L${x} ${y}`;
          const [px, py] = points[i - 1];
          return `${acc} C${px} ${py + STEP / 2} ${x} ${y - STEP / 2} ${x} ${y}`;
        }, "") + ` L160 ${height}`;
        return (
          <div key={land.ma_goc_id} className={`sp-land${land.mo ? "" : " is-locked"}`}>
            <div className={`sp-sign${land.mo && land.co_bai ? "" : " is-dim"}${land.thu_hoach ? " is-done" : ""}`}>
              <small>{land.so_thu_tu ? `Thửa ${land.so_thu_tu}` : "Sắp có"}</small>
              <b>{land.ten}</b>
              {land.muc_tieu && <span>{land.muc_tieu}</span>}
              {land.da_vuot && <em className="sp-sign__tag"><Icon name="bolt" size={13} />Đã vượt</em>}
              {onSkip && li > 0 && !land.mo && land.co_bai && (
                <button type="button" className="sp-skip" disabled={busy} onClick={() => onSkip(land)}>
                  <Icon name="bolt" size={15} />Vượt tới thửa này
                </button>
              )}
            </div>
            {!land.co_bai ? (
              <div className="sp-empty"><span className="sp-road" aria-hidden="true" /><p>Chưa có bài · Giảng viên chưa xuất bản</p></div>
            ) : (
              <div className="sp-field" style={{ height }}>
                <svg className="sp-path" viewBox={`0 0 320 ${height}`} width="320" height={height} aria-hidden="true">
                  <path d={d} className="sp-path__edge" /><path d={d} className="sp-path__road" /><path d={d} className="sp-path__dots" />
                </svg>
                {li % 2 === 0 ? <Reeds side="right" /> : <Reeds side="left" />}
                {land.o.map((slot, i) => {
                  const [x, y] = points[i];
                  const big = slot.loai === "cuoi_thua";
                  const isCurrent = slot.ma_goc_id && slot.ma_goc_id === currentId;
                  const key = `${land.ma_goc_id}-${slot.vi_tri}`;
                  if (slot.trang_thai === "chua_xuat_ban") {
                    return (
                      <span key={key} className={`sp-node is-ghost${big ? " is-big" : ""}`} style={{ left: x, top: y - 30 }}
                        title="Chưa xuất bản"><span className="sp-node__top">{big ? <Sprout /> : slot.vi_tri}</span></span>
                    );
                  }
                  return (
                    <span key={key} className={`sp-slot${open === key ? " is-open" : ""}`} style={{ left: x, top: y - 30 }}>
                      <button type="button" className={`sp-node st-${slot.trang_thai}${big ? " is-big" : ""}${isCurrent ? " is-current" : ""}`}
                        aria-label={`${big ? "Kiểm tra cuối thửa" : `Bài ${slot.vi_tri}`}: ${slot.ten} – ${STATE_TEXT[slot.trang_thai]}`}
                        aria-expanded={open === key} onClick={() => setOpen(open === key ? null : key)}>
                        <span className="sp-node__top">{big && slot.trang_thai !== "da_vuot" ? <Sprout /> : slot.trang_thai === "da_xong" ? <Icon name="check" size={26} />
                          : slot.trang_thai === "da_vuot" ? <Icon name="bolt" size={24} /> : slot.vi_tri}</span>
                        {slot.trang_thai === "khoa" && <span className="sp-lock"><Icon name="lock" size={12} /></span>}
                      </button>
                      {isCurrent && <img className="sp-xiang" src={xiangFull} alt="" />}
                      {open === key && (
                        <span className="sp-pop" role="dialog" aria-label={slot.ten}>
                          <button type="button" className="sp-pop__x" aria-label="Đóng" onClick={() => setOpen(null)}><Icon name="x" size={16} /></button>
                          <small>Thửa {land.so_thu_tu ?? li + 1} · {big ? "Kiểm tra cuối thửa" : `Bài ${slot.vi_tri}`}</small>
                          <b>{slot.ten}</b>
                          {slot.muc_tieu && <span>{slot.muc_tieu}</span>}
                          {slot.trang_thai === "khoa" ? (
                            <em>{lockText || "Chưa mở. Hoàn thành ô trước để mở ô này."}</em>
                          ) : (
                            <>
                              <em className={`st-${slot.trang_thai}`}>{STATE_TEXT[slot.trang_thai]} · {ruleText(slot)}</em>
                              <button type="button" className="xc-btn xc-btn--sm xc-btn--block" disabled={busy} onClick={() => onStart(slot)}>
                                {busy ? "Đang mở..." : actionLabel(slot)}
                              </button>
                            </>
                          )}
                        </span>
                      )}
                    </span>
                  );
                })}
              </div>
            )}
            {li < lands.length - 1 && <div className="sp-river" aria-hidden="true"><span className="sp-bridge" /></div>}
          </div>
        );
      })}
    </div>
  );
}
