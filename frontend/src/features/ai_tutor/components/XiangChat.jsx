import { useEffect, useRef, useState } from "react";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { askXiang } from "../api/askXiang.js";
import "../styles/XiangChat.css";

const SUGGESTIONS_WRONG = [
  "Vì sao câu này mình làm sai?",
  "Giải thích ngữ pháp & từ khóa",
  "Cho mình thêm 1 ví dụ dễ nhớ",
];

const SUGGESTIONS_RIGHT = [
  "Phân tích ngữ pháp trong câu",
  "Mở rộng cách dùng từ này",
  "Cho mình thêm 1 câu ví dụ",
];

// Bỏ ký hiệu markdown đơn giản (**đậm**, # tiêu đề) để hiện chữ thuần
function plain(text) {
  return text.replace(/\*\*(.+?)\*\*/g, "$1").replace(/^#+\s*/gm, "");
}

// Khung Hỏi Xiang cho 1 câu hỏi sau khi đã kiểm tra/nộp bài.
export default function XiangChat({ luotId, cauHoiId, isCorrect = null, defaultOpen = false, onClose, ask: customAsk, sendFn }) {
  const { token } = useAuth();
  const [open, setOpen] = useState(defaultOpen);
  const [messages, setMessages] = useState([]); // [{vai: "hoc_vien"|"xiang", noi_dung}]
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
      const fn = customAsk || sendFn;
      const res = fn ? await fn(token, cauHoiId, history) : await askXiang(token, luotId, cauHoiId, history);
      setMessages([...history, { vai: "xiang", noi_dung: res.tra_loi }]);
    } catch (err) {
      setMessages(history);
      setError(err?.message || "Xiang chưa trả lời được, bạn thử lại nhé");
    } finally {
      setBusy(false);
    }
  }

  function handleAsk(text) {
    const question = text.trim();
    if (!question || busy) return;
    setDraft("");
    send([...messages, { vai: "hoc_vien", noi_dung: question.slice(0, 500) }]);
  }

  const lastIsQuestion = messages.length > 0 && messages[messages.length - 1].vai === "hoc_vien";
  const chips = isCorrect === true ? SUGGESTIONS_RIGHT : SUGGESTIONS_WRONG;

  if (!open) {
    return (
      <button type="button" className="xx-open" onClick={() => setOpen(true)}>
        <img src={xiangFace} alt="" /> Hỏi Xiang giải thích
      </button>
    );
  }

  return (
    <section className="xx" aria-label="Hỏi Xiang về câu này">
      <header className="xx-head">
        <img src={xiangFace} alt="" />
        <div className="xx-head__meta">
          <b>Trợ giảng Xiang</b>
          <small>AI hỗ trợ giải thích sau khi làm câu · Hãy đối chiếu cùng đáp án chuẩn</small>
        </div>
        <button
          type="button"
          className="xx-x"
          aria-label="Đóng Hỏi Xiang"
          onClick={() => (onClose ? onClose() : setOpen(false))}
        >
          ×
        </button>
      </header>

      <div className="xx-list" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <p className="xx-hint">
            Xiang đã xem đề bài và câu trả lời vừa kiểm tra của bạn. Chọn gợi ý bên dưới hoặc đặt câu hỏi bất kỳ nhé!
          </p>
        )}
        {messages.map((m, i) => (
          <p key={i} className={`xx-msg xx-msg--${m.vai}`}>
            {m.vai === "xiang" ? plain(m.noi_dung) : m.noi_dung}
          </p>
        ))}
        {busy && <p className="xx-msg xx-msg--xiang xx-typing">Xiang đang suy nghĩ câu trả lời…</p>}
      </div>

      {error && (
        <div className="xx-error" role="alert">
          <span>{error}</span>
          {lastIsQuestion && (
            <button type="button" onClick={() => send(messages)} disabled={busy}>
              Thử lại
            </button>
          )}
        </div>
      )}

      {messages.length === 0 && (
        <div className="xx-chips">
          {chips.map((s) => (
            <button key={s} type="button" onClick={() => handleAsk(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form
        className="xx-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleAsk(draft);
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={500}
          placeholder="Nhập câu hỏi cho Xiang…"
          aria-label="Câu hỏi cho Xiang"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !draft.trim()}>
          Gửi
        </button>
      </form>
    </section>
  );
}
