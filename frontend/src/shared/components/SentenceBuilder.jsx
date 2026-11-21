import { useEffect, useMemo, useState } from "react";

import xiangFace from "../../assets/images/xiang/home/xiang_face.webp";
import "../styles/sentenceBuilder.css";

// Câu "Sắp xếp câu" kiểu Duolingo: bấm mảnh để ghép câu, bấm lại mảnh đã ghép để trả về. Không cần gõ chữ Hán.
// pieces: [{id, noi_dung}] máy chủ trả về; extra: các mảnh nhiễu (chuỗi) không thuộc câu, để học viên phải chọn lọc.
// prompt: nghĩa tiếng Việt của câu cần ghép (đề bài kiểu Duolingo); value: câu đang ghép; onChange(chuỗi) mỗi lần thay đổi; answered: câu đã nộp để hiện lại khi xem (disabled).

// Đề cũ ghi sẵn các mảnh trong nội dung dạng "A ／ B ／ C": dùng để ẩn phần trùng khi đã có ô mảnh
export const isPieceList = (text) => typeof text === "string" && text.includes("／");

function seeded(seed) {
  let s = Math.abs(Number(seed) || 1) % 2147483647 || 1;
  return () => (s = (s * 16807) % 2147483647) / 2147483647;
}

// Mảnh nhiễu lấy từ các câu Sắp xếp khác trong cùng lượt (không trùng chữ với mảnh của câu đang làm).
// Không thêm hư từ chung (了, 很, 都…) vì dễ ghép ra câu vẫn đúng ngữ pháp mà bị chấm sai.
export function pickDistractors(items, current, max = 2) {
  if (!current || current.cau_hoi?.dang !== "sap_xep") return [];
  const own = new Set((current.phuong_an || []).map((p) => p.noi_dung));
  const pool = [];
  for (const it of items || []) {
    if (it === current || it.cau_hoi?.dang !== "sap_xep") continue;
    for (const p of it.phuong_an || []) {
      if (p.noi_dung && !own.has(p.noi_dung) && !pool.includes(p.noi_dung)) pool.push(p.noi_dung);
    }
  }
  const rnd = seeded(current.cau_hoi.id);
  pool.sort(() => rnd() - 0.5);
  const n = Math.min(max, (current.phuong_an || []).length >= 4 ? 2 : 1);
  return pool.slice(0, n);
}

function restore(all, value) {
  // Dựng lại thứ tự đã chọn từ chuỗi đã lưu (ghép tham lam theo mảnh dài trước)
  if (!value) return [];
  const left = [...all].sort((a, b) => (b.noi_dung || "").length - (a.noi_dung || "").length);
  const out = [];
  let rest = value.replace(/[\s。？！，.?!,]/g, "");
  while (rest) {
    const hit = left.find((p) => p.noi_dung && !out.includes(p.id) && rest.startsWith(p.noi_dung));
    if (!hit) return null;
    out.push(hit.id);
    rest = rest.slice(hit.noi_dung.length);
  }
  return out;
}

export default function SentenceBuilder({ pieces, extra = [], prompt = null, value = "", onChange, disabled = false, answered = null }) {
  const all = useMemo(() => {
    const list = [...pieces, ...extra.map((t, i) => ({ id: `x${i}`, noi_dung: t }))];
    if (!extra.length) return list;
    const rnd = seeded(pieces.length * 31 + extra.join("").length);
    return list.map((p) => [rnd(), p]).sort((a, b) => a[0] - b[0]).map(([, p]) => p);
  }, [pieces, extra.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps
  const byId = useMemo(() => Object.fromEntries(all.map((p) => [p.id, p])), [all]);
  const [order, setOrder] = useState(() => restore(all, answered ?? value) || []);
  useEffect(() => { setOrder(restore(all, answered ?? value) || []); }, [all]); // eslint-disable-line react-hooks/exhaustive-deps

  function update(next) {
    setOrder(next);
    onChange?.(next.map((id) => byId[id].noi_dung).join(""));
  }

  const shownText = disabled && answered && order.length === 0 ? answered : null; // câu đã nộp không dựng lại được từ mảnh
  return (
    <div className={`sb${disabled ? " is-off" : ""}`}>
      {prompt && (
        <div className="sb-prompt">
          <img src={xiangFace} alt="" className="sb-prompt__face" />
          <p className="sb-prompt__bubble">{prompt}</p>
        </div>
      )}
      <div className="sb-line" aria-label="Câu đang ghép" aria-live="polite">
        {shownText && <span className="sb-chip hz">{shownText}</span>}
        {order.map((id, i) => (
          <button key={id} type="button" className="sb-chip hz" disabled={disabled}
            onClick={() => update(order.filter((x) => x !== id))} aria-label={`Bỏ mảnh ${byId[id].noi_dung}, vị trí ${i + 1}`}>
            {byId[id].noi_dung}
          </button>
        ))}
      </div>
      <div className="sb-pool" aria-label="Các mảnh">
        {all.map((p) => (order.includes(p.id) || disabled
          ? <span key={p.id} className="sb-chip sb-chip--used hz" aria-hidden="true">{p.noi_dung}</span>
          : (
            <button key={p.id} type="button" className="sb-chip hz" onClick={() => update([...order, p.id])}>
              {p.noi_dung}
            </button>
          )))}
      </div>
    </div>
  );
}
