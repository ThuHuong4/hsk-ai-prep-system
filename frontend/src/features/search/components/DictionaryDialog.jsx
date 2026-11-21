import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { ROLE } from "../../auth/utils/roles.js";
import { mediaUrl } from "../../lecturer/utils/labels.js";
import { searchAll } from "../api/searchApi.js";
import "../styles/dictionary.css";

function canSpeakChinese() {
  try {
    return typeof window !== "undefined" && "speechSynthesis" in window
      && window.speechSynthesis.getVoices().some((v) => /^zh/i.test(v.lang));
  } catch { return false; }
}

function speak(text) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-CN";
    u.rate = 0.85;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } catch { /* trình duyệt không hỗ trợ */ }
}

function WordCard({ w, voice }) {
  return (
    <article className="dict-card">
      <header className="dict-card__head">
        <span className="dict-han" lang="zh">{w.chu_han}</span>
        <span className="dict-py">{w.pinyin}</span>
        {voice && (
          <button type="button" className="dict-icon" onClick={() => speak(w.chu_han)} aria-label={`Nghe ${w.chu_han}`} title="Nghe phát âm">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11" /></svg>
          </button>
        )}
      </header>
      <p className="dict-mean">{w.nghia}</p>
      {w.vd_cau && (
        <div className="dict-ex">
          <p className="dict-ex__label">Ví dụ:</p>
          <p className="dict-ex__zh" lang="zh">{w.vd_cau}
            {(w.vd_audio || voice) && (
              <button type="button" className="dict-icon dict-icon--sm" aria-label="Nghe câu ví dụ"
                onClick={() => (w.vd_audio ? new Audio(mediaUrl(w.vd_audio)).play().catch(() => {}) : speak(w.vd_cau))}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16 9a4 4 0 0 1 0 6" /></svg>
              </button>
            )}
          </p>
          {w.vd_pinyin && <p className="dict-ex__py">{w.vd_pinyin}</p>}
          {w.vd_nghia && <p className="dict-ex__vi">{w.vd_nghia}</p>}
        </div>
      )}
    </article>
  );
}

export default function DictionaryDialog({ onClose }) {
  const { user } = useAuth();
  const student = user?.vai_tro === ROLE.HOC_VIEN;
  const [q, setQ] = useState("");
  const [state, setState] = useState({ loading: false, data: null, error: "" });
  const [voice, setVoice] = useState(canSpeakChinese);
  const input = useRef(null);

  useEffect(() => {
    input.current?.focus();
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const update = () => setVoice(canSpeakChinese());
    window.speechSynthesis?.addEventListener?.("voiceschanged", update);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      window.speechSynthesis?.removeEventListener?.("voiceschanged", update);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  // Gõ tới đâu tìm tới đó: chờ 250 ms sau lần gõ cuối, hủy yêu cầu cũ
  useEffect(() => {
    const keyword = q.trim();
    if (!keyword) { setState({ loading: false, data: null, error: "" }); return undefined; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setState((s) => ({ ...s, loading: true, error: "" }));
      searchAll(keyword, controller.signal)
        .then((data) => setState({ loading: false, data, error: "" }))
        .catch((err) => err?.name !== "AbortError" && setState({ loading: false, data: null, error: err?.message || "Không tìm được, thử lại sau" }));
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [q]);

  const { loading, data, error } = state;
  const base = student ? "/hoc-vien" : "";
  const empty = data && !data.tu_vung.length && !data.de_thi.length;

  return createPortal(
    <div className="dict-root" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <section className="dict-modal" role="dialog" aria-modal="true" aria-labelledby="dict-title">
        <button type="button" className="dict-close" onClick={onClose} aria-label="Đóng">×</button>
        <h2 id="dict-title" className="dict-title">
          <span className="dict-title__ico" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M12 6.5C10.5 5.3 8.2 4.8 5 5v13c3.2-.2 5.5.3 7 1.5 1.5-1.2 3.8-1.7 7-1.5V5c-3.2-.2-5.5.3-7 1.5z" /><path d="M12 6.5v13" /></svg>
          </span>
          Tra cứu từ điển
        </h2>
        <p className="dict-sub">Có thể tra theo Hán tự, pinyin hoặc định nghĩa</p>
        <div className="dict-search">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} maxLength={40}
            placeholder="Nhập từ cần tra…" aria-label="Từ khóa tra từ" />
          {q && <button type="button" className="dict-clear" onClick={() => { setQ(""); input.current?.focus(); }} aria-label="Xóa từ khóa">×</button>}
        </div>

        <div className="dict-results" aria-live="polite" aria-busy={loading}>
          {!q.trim() && <p className="dict-hint">Tra trong từ vựng HSK đã có trên Xianglingo và tên đề thi thử.</p>}
          {loading && !data && <p className="dict-hint">Đang tìm…</p>}
          {error && <p className="dict-hint dict-hint--err" role="alert">{error}</p>}
          {empty && <p className="dict-hint">Chưa có “{data.tu_khoa}” trong từ vựng HSK của Xianglingo.</p>}
                    {data?.tu_vung.map((w) => <WordCard key={w.id} w={w} voice={voice} />)}
          {data?.de_thi.length > 0 && (
            <div className="dict-exams">
              <h3>Đề thi thử</h3>
              {data.de_thi.map((e) => (
                <Link key={e.ma_goc_id} className="dict-exam" to={`${base}/thi-thu/de/${e.ma_goc_id}`} onClick={onClose}>
                  <span>{e.ten}</span><span className="dict-tag">{e.cap}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>,
    document.body,
  );
}
