import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { mediaUrl } from "../../lecturer/utils/labels.js";
import { getAttempt, saveAnswer, submitAttempt } from "../api/mockTestApi.js";
import ExamPaper from "../components/ExamPaper.jsx";
import ExamShell from "../components/ExamShell.jsx";
import QuestionNav from "../components/QuestionNav.jsx";
import { buildPaper, formatClock } from "../utils/paper.js";
import "../styles/examFlags.css";

// Câu đánh dấu xem lại: chỉ lưu trên trình duyệt này (tiện ích cá nhân, không ảnh hưởng chấm điểm)
const flagKey = (id) => `xianglingo-exam-flags-${id}`;
function readFlags(id) {
  try { return new Set(JSON.parse(localStorage.getItem(flagKey(id)) || "[]")); } catch { return new Set(); }
}

export default function ExamSessionPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [items, setItems] = useState([]);
  const [remaining, setRemaining] = useState(null);
  const [saving, setSaving] = useState(0);
  const [error, setError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [flags, setFlags] = useState(() => readFlags(luotId));
  const [current, setCurrent] = useState(null);
  const deadline = useRef(null);
  const submittedRef = useRef(false);

  const goResult = useCallback(() => navigate(`/thi-thu/ket-qua/${luotId}`, { replace: true }), [navigate, luotId]);

  useEffect(() => {
    const controller = new AbortController();
    getAttempt(token, luotId, controller.signal)
      .then((d) => {
        if (d.trang_thai !== "dang_lam") { goResult(); return; }
        setData(d);
        setItems(d.cau_hoi);
        deadline.current = Date.now() + d.con_lai_giay * 1000;
        setRemaining(d.con_lai_giay);
      })
      .catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài thi"));
    return () => controller.abort();
  }, [token, luotId, goResult]);

  const submit = useCallback(async () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    setSubmitting(true);
    try {
      await submitAttempt(token, luotId);
      try { localStorage.removeItem(flagKey(luotId)); } catch { /* bỏ qua */ }
      goResult();
    } catch (err) {
      submittedRef.current = false;
      setSubmitting(false);
      setError(err?.message || "Nộp bài thất bại, hãy thử lại");
    }
  }, [token, luotId, goResult]);

  useEffect(() => {
    if (remaining === null) return undefined;
    const timer = setInterval(() => {
      const left = Math.max(0, Math.round((deadline.current - Date.now()) / 1000));
      setRemaining(left);
      if (left <= 0) { clearInterval(timer); submit(); }
    }, 1000);
    return () => clearInterval(timer);
  }, [remaining === null, submit]); // eslint-disable-line react-hooks/exhaustive-deps

  function toggleFlag(no) {
    setFlags((prev) => {
      const next = new Set(prev);
      if (next.has(no)) next.delete(no); else next.add(no);
      try { localStorage.setItem(flagKey(luotId), JSON.stringify([...next])); } catch { /* bỏ qua */ }
      return next;
    });
  }

  // Câu gần giữa màn hình nhất → nút "Đánh dấu câu N"
  useEffect(() => {
    if (!data) return undefined;
    let frame = 0;
    const pick = () => {
      frame = 0;
      const mid = window.innerHeight / 2;
      let best = null; let dist = Infinity;
      document.querySelectorAll('[id^="q-"]').forEach((n) => {
        const r = n.getBoundingClientRect();
        const d = Math.abs(r.top + r.height / 2 - mid);
        if (d < dist) { dist = d; best = n; }
      });
      if (best) setCurrent(Number(best.id.slice(2)) || null);
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(pick); };
    pick();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); if (frame) cancelAnimationFrame(frame); };
  }, [data]);

  // Rời trang khi còn đang lưu → hỏi lại
  useEffect(() => {
    const handler = (e) => { if (saving > 0) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [saving]);

  async function persist(item, patch) {
    const previous = item.tra_loi;
    setItems((list) => list.map((i) => (i.cau_hoi.id === item.cau_hoi.id ? { ...i, tra_loi: { ...i.tra_loi, ...patch } } : i)));
    setSaving((n) => n + 1);
    setError("");
    try {
      const res = await saveAnswer(token, luotId, { cau_hoi_id: item.cau_hoi.id, ...patch, vi_tri: item.so_cau });
      deadline.current = Date.now() + res.con_lai_giay * 1000;
    } catch (err) {
      setItems((list) => list.map((i) => (i.cau_hoi.id === item.cau_hoi.id ? { ...i, tra_loi: previous } : i)));
      if (err?.status === 409) { goResult(); return; }
      setError(err?.message || "Chưa lưu được câu trả lời, hãy chọn lại");
    } finally {
      setSaving((n) => n - 1);
    }
  }

  const onPick = (item, optionId) => {
    const same = item.tra_loi?.phuong_an_chon_id === optionId;
    persist(item, { phuong_an_chon_id: same ? null : optionId, van_ban: null }); // Bấm lại để bỏ chọn
  };
  const onText = (item, value) => persist(item, { phuong_an_chon_id: null, van_ban: value || null });

  const sections = useMemo(() => buildPaper(items), [items]);
  const scored = items.filter((i) => !i.la_cau_vi_du);
  const answered = scored.filter((i) => i.tra_loi?.phuong_an_chon_id || i.tra_loi?.van_ban).length;
  const flagged = scored.map((i) => i.so_cau).filter((no) => flags.has(no));
  const goTo = (no) => document.getElementById(`q-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });

  if (error && !data) return <ExamShell title="Thi thử"><p role="alert" className="lv-alert">{error}</p></ExamShell>;
  if (!data) return <ExamShell title="Thi thử"><p className="lv-muted">Đang tải bài thi…</p></ExamShell>;

  const low = remaining !== null && remaining <= 300;
  return (
    <ExamShell
      title={data.de.ten}
      right={(
        <>
          <span className={`xt-timer${low ? " is-low" : ""}`} role="timer" aria-live={low ? "polite" : "off"} aria-label="Thời gian còn lại">
            {formatClock(remaining ?? 0)}
          </span>
          <button type="button" className="xbtn xbtn--sm" onClick={() => setConfirmOpen(true)} disabled={submitting}>Nộp bài</button>
        </>
      )}
    >
      <div className="xt-layout">
        <main className="xt-main">
          <div className="xt-cover">
            <span className="xt-cover__kicker">新汉语水平考试 · {data.de.ten_cap_do}</span>
            <h1>{data.de.ten}</h1>
            <p>Mã đề {data.de.ma_de} · {data.de.thoi_luong_phut} phút · {scored.length} câu. Câu trả lời được lưu ngay mỗi khi chọn.</p>
          </div>
          <ExamPaper sections={sections} passages={data.ngu_lieu} mode="do" onPick={onPick} onText={onText}
            disabled={submitting} audioUrl={mediaUrl(data.de.tep_audio_chung)} />
        </main>
        <aside className="xt-side">
          <div className="xt-side__card">
            <p className="xt-side__stat"><strong>{answered}</strong>/{scored.length} câu đã làm</p>
            <p className="xt-save" role="status">{saving > 0 ? "Đang lưu…" : "Đã lưu"}</p>
            <QuestionNav items={items} mode="do" flags={flags} current={current} />
            {current && (
              <button type="button" className={`xt-flagbtn${flags.has(current) ? " is-on" : ""}`} onClick={() => toggleFlag(current)}
                aria-pressed={flags.has(current)}>
                <span aria-hidden="true">⚑</span> {flags.has(current) ? `Bỏ đánh dấu câu ${current}` : `Đánh dấu xem lại câu ${current}`}
              </button>
            )}
            {flagged.length > 0 && <p className="xt-flaglist">Đang đánh dấu: {flagged.join(", ")}</p>}
            <button type="button" className="xbtn" onClick={() => setConfirmOpen(true)} disabled={submitting}>Nộp bài</button>
            {error && <p role="alert" className="lv-alert">{error}</p>}
          </div>
        </aside>
      </div>

      {confirmOpen && (
        <div className="xt-dialog" role="dialog" aria-modal="true" aria-labelledby="xt-confirm-title">
          <div className="xt-dialog__box">
            <h2 id="xt-confirm-title">Nộp bài?</h2>
            <p>Bạn đã làm {answered}/{scored.length} câu.{scored.length - answered > 0 && ` Còn ${scored.length - answered} câu bỏ trống sẽ tính 0 điểm.`}</p>
            {flagged.length > 0 && (
              <div className="xt-flagjump">
                <span>Câu đã đánh dấu xem lại:</span>
                {flagged.map((no) => (
                  <button key={no} type="button" className="xt-nav__btn is-flag" onClick={() => { setConfirmOpen(false); goTo(no); }}>{no}</button>
                ))}
              </div>
            )}
            <div className="lv-actions">
              <button type="button" className="xbtn" onClick={submit} disabled={submitting || saving > 0}>{submitting ? "Đang nộp…" : "Nộp bài"}</button>
              <button type="button" className="xbtn xbtn--ghost" onClick={() => setConfirmOpen(false)} disabled={submitting}>Làm tiếp</button>
            </div>
          </div>
        </div>
      )}
    </ExamShell>
  );
}
