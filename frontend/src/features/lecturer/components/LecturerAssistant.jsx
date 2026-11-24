import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { askLecturerAssistant } from "../api/lecturerApi.js";
import "../styles/assistant.css";

/**
 * Trợ lý AI của Giảng viên: nút tròn góc phải, mở khung trò chuyện ở mọi trang.
 * Hỏi chuyên môn (vì sao câu sai, ngữ pháp…), cùng lên kế hoạch đề; AI chỉ đề xuất hành động để Giảng viên tự bấm.
 * Cuộc trò chuyện chỉ giữ trong tab trình duyệt (sessionStorage), không lưu ở máy chủ.
 */
const STORE_KEY = "xianglingo-tro-ly-gv";
const QUICK = [
  "Giúp tôi lên kế hoạch một đề thi thử HSK 2",
  "Ngân hàng câu hỏi đang thiếu gì nhiều nhất?",
  "Vì sao câu này sai: 我没是学生。",
];

function load() {
  try {
    const data = JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]");
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export default function LecturerAssistant() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [chat, setChat] = useState(load);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify(chat.slice(-40)));
    } catch {
      // trình duyệt chặn lưu trữ: chỉ giữ trong trang
    }
    endRef.current?.scrollIntoView({ block: "end" });
  }, [chat, open]);

  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  async function send(message) {
    const content = message.trim();
    if (!content || busy) return;
    const history = chat.map(({ vai_tro, noi_dung }) => ({ vai_tro, noi_dung }));
    const next = [...chat, { vai_tro: "gv", noi_dung: content }];
    setChat(next);
    setText("");
    setBusy(true);
    setError("");
    try {
      const data = await askLecturerAssistant(token, { tin_nhan: content, lich_su: history.slice(-12), trang: location.pathname });
      setChat([...next, { vai_tro: "ai", noi_dung: data.tra_loi, hanh_dong: data.hanh_dong || [] }]);
    } catch (err) {
      setChat(chat);
      setText(content);
      setError(err?.message || "Trợ lý AI chưa trả lời được, vui lòng thử lại");
    } finally {
      setBusy(false);
    }
  }

  function runAction(a) {
    if (a.loai === "ghep_de") navigate("/giang-vien/bo-de/ai", { state: { cap_do_id: a.cap_do_id } });
    else navigate("/giang-vien/cau-hoi/ai", { state: { plan: a } });
    setOpen(false);
  }

  return (
    <>
      <button type="button" className="gva-fab" onClick={() => setOpen((v) => !v)} aria-expanded={open}
        aria-controls="gva-panel" aria-label={open ? "Đóng trợ lý AI" : "Mở trợ lý AI"}>
        {open ? "×" : "AI"}
      </button>
      {open && (
        <section id="gva-panel" className="gva-panel" role="dialog" aria-label="Trợ lý AI của Giảng viên">
          <header className="gva-head">
            <div>
              <h2>Trợ lý AI</h2>
              <small>Hỏi chuyên môn, lên kế hoạch đề. AI chỉ gợi ý, bạn quyết định.</small>
            </div>
            {chat.length > 0 && (
              <button type="button" className="gva-link" onClick={() => setChat([])} disabled={busy}>Cuộc mới</button>
            )}
            <button type="button" className="gva-x" onClick={() => setOpen(false)} aria-label="Đóng">×</button>
          </header>

          <div className="gva-body" aria-live="polite">
            {chat.length === 0 && (
              <div className="gva-quick">
                <p>Bạn có thể hỏi:</p>
                {QUICK.map((q) => (
                  <button key={q} type="button" onClick={() => send(q)} disabled={busy}>{q}</button>
                ))}
              </div>
            )}
            {chat.map((m, i) => (
              <div key={i} className={m.vai_tro === "ai" ? "gva-msg gva-msg--ai" : "gva-msg gva-msg--me"}>
                <p>{m.noi_dung}</p>
                {m.hanh_dong?.length > 0 && (
                  <div className="gva-actions">
                    {m.hanh_dong.map((a, j) => (
                      <button key={j} type="button" onClick={() => runAction(a)}>{a.nhan}</button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <p className="gva-typing">AI đang suy nghĩ…</p>}
            <div ref={endRef} />
          </div>

          {error && <p role="alert" className="gva-error">{error}</p>}
          <form className="gva-ask" onSubmit={(e) => { e.preventDefault(); send(text); }}>
            <textarea ref={inputRef} rows={2} maxLength={4000} value={text} disabled={busy} aria-label="Nhắn cho trợ lý AI"
              placeholder="Hỏi bất cứ điều gì… (Enter để gửi, Shift+Enter xuống dòng)"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  send(text);
                }
              }} />
            <button type="submit" className="xbtn xbtn--sm" disabled={busy || !text.trim()}>Gửi</button>
          </form>
        </section>
      )}
    </>
  );
}
