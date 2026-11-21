import { useEffect, useRef, useState } from "react";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { askXiang } from "../api/askXiang.js";
import "../styles/xiangChat.css";

const SUGGESTIONS = ["Vì sao mình chọn sai?", "Giải thích ngữ pháp trong câu", "Cho mình thêm 1 ví dụ"];

// Bỏ ký hiệu markdown đơn giản (**đậm**, # tiêu đề) để hiện chữ thuần
function plain(text) {
  return text.replace(/\*\*(.+?)\*\*/g, "$1").replace(/^#+\s*/gm, "");
}

// Khung Hỏi Xiang cho 1 câu hỏi. Không lưu hội thoại: đổi câu (key khác) hoặc rời trang là mất.
export default function XiangChat({ luotId, cauHoiId, defaultOpen = false, onClose, ask }) {
  const { token } = useAuth();
  const [open, setOpen] = useState(defaultOpen);
  const [messages, setMessages] = useState([]);   // [{vai: "hoc_vien"|"xiang", noi_dung}]
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(history) {
    setBusy(true);
    setError("");
    try {
      const res = await askXiang(token, luotId, cauHoiId, history);
      setMessages([...history, { vai: "xiang", noi_dung: res.tra_loi }]);
    } catch (err) {
      setMessages(history); // Giữ câu hỏi để bấm Thử lại
      setError(err?.message || "Xiang chưa trả lời được, bạn thử lại nhé");
    } finally {
      setBusy(false);
    }
  }

  function ask(text) {
    const question = text.trim();
    if (!question || busy) return;
    setDraft("");
    send([...messages, { vai: "hoc_vien", noi_dung: question.slice(0, 500) }]);
  }

  const lastIsQuestion = messages.length > 0 && messages[messages.length - 1].vai === "hoc_vien";

  if (!open) {
    return (
      <button type="button" className="xx-open" onClick={() => setOpen(true)}>
        <img src={xiangFace} alt="" /> Hỏi Xiang
      </button>
    );
  }

  return (
    <section className="xx" aria-label="Hỏi Xiang về câu này">
      <header className="xx-head">
        <img src={xiangFace} alt="" />
        <b>Hỏi Xiang</b>
        <small>AI có thể nhầm, hãy đối chiếu với đáp án.</small>
        <button type="button" className="xx-x" aria-label="Đóng Hỏi Xiang" onClick={() => (onClose ? onClose() : setOpen(false))}>×</button>
      </header>

      <div className="xx-list" ref={listRef} aria-live="polite">
        {messages.length === 0 && <p className="xx-hint">Xiang đã xem câu này và bài làm của bạn. Hỏi gì cũng được nhé!</p>}
        {messages.map((m, i) => (
          <p key={i} className={`xx-msg xx-msg--${m.vai}`}>{m.vai === "xiang" ? plain(m.noi_dung) : m.noi_dung}</p>
        ))}
        {busy && <p className="xx-msg xx-msg--xiang xx-typing">Xiang đang nghĩ…</p>}
      </div>

      {error && (
        <div className="xx-error" role="alert">
          <span>{error}</span>
          {lastIsQuestion && <button type="button" onClick={() => send(messages)} disabled={busy}>Thử lại</button>}
        </div>
      )}

      {messages.length === 0 && (
        <div className="xx-chips">
          {SUGGESTIONS.map((s) => <button key={s} type="button" onClick={() => ask(s)} disabled={busy}>{s}</button>)}
        </div>
      )}

      <form className="xx-form" onSubmit={(e) => { e.preventDefault(); ask(draft); }}>
        <input value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={500}
          placeholder="Hỏi tiếp Xiang…" aria-label="Câu hỏi cho Xiang" disabled={busy} />
        <button type="submit" disabled={busy || !draft.trim()}>Gửi</button>
      </form>
    </section>
  );
}