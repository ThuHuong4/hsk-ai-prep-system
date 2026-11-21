import { useEffect, useState } from "react";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { listWords } from "../api/lecturerApi.js";

// Gắn một từ vựng (cùng cấp) cho câu kỹ năng Từ vựng
export default function WordPicker({ capDoId, value, word, onChange, disabled }) {
  const { token } = useAuth();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open || !capDoId) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      listWords(token, { cap_do_id: capDoId, q: q.trim(), so_dong: 10 }, controller.signal)
        .then((d) => setResults(d.muc)).catch(() => {});
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [q, open, capDoId, token]);

  return (
    <div className="lv-media">
      <span className="lv-media__label">Từ vựng được gắn</span>
      {value && word ? (
        <span><span className="zh lv-word">{word.chu_han}</span> {word.pinyin} – {word.nghia}</span>
      ) : <span className="lv-muted">Chưa gắn từ</span>}
      <div className="lv-media__actions">
        <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={disabled} onClick={() => setOpen((v) => !v)}>{open ? "Đóng" : value ? "Đổi từ" : "Chọn từ"}</button>
        {value && <button type="button" className="xlink xlink--danger" disabled={disabled} onClick={() => onChange(null, null)}>Bỏ gắn</button>}
      </div>
      {open && (
        <div className="lv-wordpick">
          <input type="search" placeholder="Tìm chữ Hán, pinyin, nghĩa" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Tìm từ để gắn" />
          <ul className="lv-picklist">
            {results.map((w) => (
              <li key={w.id} className="lv-pick">
                <span className="lv-cell-text"><span className="zh lv-word">{w.chu_han}</span><span className="lv-cell-sub">{w.pinyin} – {w.nghia}</span></span>
                <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => { onChange(w.id, w); setOpen(false); }}>Chọn</button>
              </li>
            ))}
            {results.length === 0 && <li className="lv-muted">Không có từ phù hợp ở cấp này.</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
