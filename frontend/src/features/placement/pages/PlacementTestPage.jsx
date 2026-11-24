/**
 * Bài Đánh giá trình độ đầu vào 8 câu thích ứng (chuẩn Cambridge Assessment).
 * - Làm liền mạch Câu 1 → Câu 8 trên một khung tập trung, sạch sẽ:
 *     + Chưa điền / chưa chọn câu trả lời thì khóa nút Tiếp theo.
 *     + Nếu không biết thì bấm "Bỏ qua": hệ thống lưu trạng thái chưa biết và chuyển NGAY sang câu kế tiếp,
 *       TUYỆT ĐỐI KHÔNG tự hiện đáp án hay làm lộ cấp thăm dò.
 * - Ngay khi hoàn thành Câu 8/8: hiện màn hình xoay tiến trình để AI chấm & phân tích toàn bộ 8 câu,
 *   xác định cấp HSK mở khóa và các lỗ hổng kiến thức, sau đó tự động vào thẳng Trang chủ (`/hoc-vien`).
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../../../layouts/staffShell.css";
import HanziText from "../../../shared/components/HanziText.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { CHOICE, LATIN, Option, SKILL, instruction } from "../../../shared/components/LessonParts.jsx";
import SentenceBuilder, { isPieceList } from "../../../shared/components/SentenceBuilder.jsx";
import "../../../shared/styles/aiDiagnostic.css";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { mediaUrl } from "../../../shared/utils/format.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import "../../mock_test/styles/mockTest.css";
import "../../practice/styles/practice.css";
import {
  analyzePlacement,
  getPlacementGate,
  getPlacementSession,
  replaceBrokenQuestion,
  startPlacement,
  submitPlacementStep,
} from "../api/placementApi.js";
import "../styles/placement.css";

const AI_STEPS = [
  "Đang chấm điểm và đo mức độ hiểu thực tế trên 8 câu trả lời…",
  "Đang khoanh vùng lỗ hổng theo 4 kỹ năng (Từ vựng · Nghe · Đọc · Viết)…",
  "Đang thiết lập trình độ HSK mở khóa và xếp bài ôn ưu tiên…",
];

function countWords(str) {
  const trimmed = (str || "").trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export default function PlacementTestPage() {
  const { luotId: paramLuotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();

  const [luotId, setLuotId] = useState(paramLuotId ? Number(paramLuotId) : null);
  const [step, setStep] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [analyzingFinal, setAnalyzingFinal] = useState(false);
  const [scanStage, setScanStage] = useState(0);
  const [analyzeErr, setAnalyzeErr] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pick, setPick] = useState(null);
  const [text, setText] = useState("");
  const stepStartedAt = useRef(Date.now());

  // Hàm chạy bước xoay AI tổng hợp cuối bài -> xong đưa thẳng vào Trang chủ cá nhân hóa (`/hoc-vien`)
  const runFinalAnalysis = useCallback(
    async (targetLuotId) => {
      setAnalyzingFinal(true);
      setAnalyzeErr("");
      setScanStage(0);
      try {
        await analyzePlacement(token, targetLuotId);
        window.dispatchEvent(new Event("xianglingo:stats"));
        navigate("/hoc-vien", { replace: true });
      } catch (err) {
        setAnalyzeErr(err?.message || "Quá trình phân tích tạm thời gián đoạn. Bạn bấm Thử lại nhé.");
      }
    },
    [token, navigate]
  );

  // Hiệu ứng chuyển nhịp các dòng trạng thái trong lúc AI đang xoay phân tích
  useEffect(() => {
    if (!analyzingFinal || analyzeErr) return undefined;
    const timer = setInterval(() => {
      setScanStage((prev) => (prev < AI_STEPS.length - 1 ? prev + 1 : prev));
    }, 1500);
    return () => clearInterval(timer);
  }, [analyzingFinal, analyzeErr]);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setError("");

    async function bootstrap() {
      setLoading(true);
      try {
        if (luotId) {
          const s = await getPlacementSession(token, luotId, controller.signal);
          if (!active) return;
          if (s.trang_thai === "da_nop") {
            const gateCheck = await getPlacementGate(token, controller.signal);
            if (!active) return;
            if (gateCheck.da_danh_gia_xong) {
              navigate("/hoc-vien", { replace: true });
              return;
            }
            setLoading(false);
            runFinalAnalysis(luotId);
            return;
          }
          setStep(s.hien_tai);
          stepStartedAt.current = Date.now();
          return;
        }

        const gate = await getPlacementGate(token, controller.signal);
        if (!active) return;
        if (gate.da_danh_gia_xong) {
          navigate("/hoc-vien", { replace: true });
          return;
        }
        if (gate.ket_qua_gan_nhat?.luot_id) {
          const doneId = gate.ket_qua_gan_nhat.luot_id;
          setLuotId(doneId);
          setLoading(false);
          runFinalAnalysis(doneId);
          return;
        }
        if (gate.luot_dang_lam_id) {
          setLuotId(gate.luot_dang_lam_id);
          navigate(`/danh-gia-dau-vao/lam-bai/${gate.luot_dang_lam_id}`, { replace: true });
          return;
        }

        const created = await startPlacement(token);
        if (!active) return;
        setLuotId(created.luot_id);
        navigate(`/danh-gia-dau-vao/lam-bai/${created.luot_id}`, { replace: true });
      } catch (err) {
        if (active && err?.name !== "AbortError") {
          setError(err?.message || "Không mở được bài đánh giá trình độ");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    bootstrap();
    return () => {
      active = false;
      controller.abort();
    };
  }, [luotId, token, navigate, runFinalAnalysis]);

  async function sendStep(skip = false) {
    if (!step || !luotId || busy || analyzingFinal) return;
    const q = step.cau_hoi;
    const hasAnswer = CHOICE.includes(q.dang) ? pick != null : Boolean(text.trim());
    if (!skip && !hasAnswer) return;

    const elapsed = Math.max(1, Math.round((Date.now() - stepStartedAt.current) / 1000));
    const body = {
      cau_hoi_id: q.id,
      phuong_an_chon_id: !skip && CHOICE.includes(q.dang) ? pick : null,
      van_ban: !skip && !CHOICE.includes(q.dang) ? text.trim() || null : null,
      bo_qua: skip,
      thoi_gian_lam_giay: elapsed,
    };
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await submitPlacementStep(token, luotId, body);
      setPick(null);
      setText("");
      if (res.da_nop) {
        setBusy(false);
        runFinalAnalysis(luotId);
        return;
      }
      setStep(res.hien_tai);
      stepStartedAt.current = Date.now();
    } catch (err) {
      setError(err?.message || "Chưa lưu được thao tác, bạn thử lại nhé");
    } finally {
      setBusy(false);
    }
  }

  async function handleReplaceBroken() {
    if (!step || !luotId || busy || analyzingFinal) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const reason = step.cau_hoi.tep_audio ? "loi_audio" : "loi_hinh_anh";
      const res = await replaceBrokenQuestion(token, luotId, reason);
      setPick(null);
      setText("");
      if (res.da_nop) {
        setBusy(false);
        runFinalAnalysis(luotId);
        return;
      }
      setStep(res.hien_tai);
      stepStartedAt.current = Date.now();
      setNotice(
        res.da_thay_cau
          ? "Đã đổi sang câu hỏi khác cùng kỹ năng cho bạn."
          : "Câu gặp sự cố kỹ thuật đã được bỏ qua mà không tính là lỗi kiến thức."
      );
    } catch (err) {
      setError(err?.message || "Chưa đổi được câu hỏi");
    } finally {
      setBusy(false);
    }
  }

  // Phím tắt 1..4 chọn nhanh phương án trắc nghiệm
  useEffect(() => {
    function onKey(e) {
      if (!step || busy || analyzingFinal || ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      const q = step.cau_hoi;
      const n = Number(e.key);
      if (CHOICE.includes(q.dang) && n >= 1 && n <= step.phuong_an.length) {
        setPick(step.phuong_an[n - 1].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, busy, analyzingFinal]);

  // MÀN HÌNH AI XOAY PHÂN TÍCH TỔNG HỢP SAU KHI XONG CÂU 8/8
  if (analyzingFinal) {
    return (
      <div className="xg xc sl" data-theme={theme}>
        <div className="cb-assess-wrap">
          <section className="cb-spinner-card" role="status" aria-live="polite">
            <div className="cb-spinner-ring" aria-hidden="true">
              <img src={xiangFace} alt="" />
            </div>
            <span className="wm-ai-badge">XIANG AI · ĐANG ĐÁNH GIÁ TRÌNH ĐỘ</span>
            <h1>Đang phân tích kết quả 8 câu của bạn…</h1>
            <p className="xc-muted">
              Hệ thống đang đối chiếu các câu đã trả lời và các câu chưa biết để xác định trình độ HSK cùng lộ trình bài ôn phù hợp nhất.
            </p>

            <ul className="cb-stage-list">
              {AI_STEPS.map((txt, idx) => {
                const done = idx < scanStage;
                const active = idx === scanStage && !analyzeErr;
                return (
                  <li
                    key={txt}
                    className={`cb-stage-item${done ? " is-done" : active ? " is-active" : ""}`}
                  >
                    <span className="cb-stage-dot">{done ? "✓" : idx + 1}</span>
                    <span>{txt}</span>
                  </li>
                );
              })}
            </ul>

            {analyzeErr && (
              <div style={{ marginTop: "14px" }}>
                <p role="alert">{analyzeErr}</p>
                <button
                  type="button"
                  className="xc-btn"
                  style={{ marginTop: "10px" }}
                  onClick={() => runFinalAnalysis(luotId)}
                >
                  Thử phân tích lại
                </button>
              </div>
            )}
          </section>
        </div>
      </div>
    );
  }

  if (loading || !step) {
    return (
      <div className="xg xc sl" data-theme={theme}>
        <div className="cb-assess-wrap">
          <section className="cb-spinner-card">
            <div className="cb-spinner-ring" aria-hidden="true">
              <img src={xiangFace} alt="" />
            </div>
            {error ? (
              <p role="alert">{error}</p>
            ) : (
              <p className="xc-muted">Đang mở bài đánh giá trình độ HSK…</p>
            )}
          </section>
        </div>
      </div>
    );
  }

  const q = step.cau_hoi;
  const total = step.tong_so_cau || 8;
  const pct = Math.round(((step.thu_tu - 1) * 100) / total);
  const hasAnswer = CHOICE.includes(q.dang) ? pick != null : Boolean(text.trim());

  return (
    <div className="xg xc sl" data-theme={theme}>
      <div className="cb-assess-wrap">
        <header className="cb-assess-top">
          <div className="cb-assess-top__meta">
            <strong>Đánh giá trình độ đầu vào</strong>
            <span className="wm-pill wm-pill--skill">
              Câu {step.thu_tu}/{total} · {SKILL[step.ky_nang] || step.ky_nang}
            </span>
          </div>
          <div
            className="cb-progress-bar"
            role="progressbar"
            aria-valuemin={1}
            aria-valuemax={total}
            aria-valuenow={step.thu_tu}
          >
            <i style={{ width: `${Math.max(8, pct)}%` }} />
          </div>
        </header>

        <main className="wm-workspace">
          <h1>
            {q.dang === "dich_cau"
              ? "Dịch câu tiếng Trung sau sang tiếng Việt"
              : instruction(q, step.ky_nang)}
          </h1>

          {notice && <p className="plm-note" role="status">{notice}</p>}
          {error && <p role="alert">{error}</p>}

          {q.tep_audio && (
            <div className="plm-audio-bar">
              <audio key={q.id} className="sl-audio" controls src={mediaUrl(q.tep_audio)} />
              {step.cho_phep_doi_cau && (
                <button type="button" className="plm-link-btn" onClick={handleReplaceBroken} disabled={busy}>
                  Không nghe được âm thanh? Đổi câu khác
                </button>
              )}
            </div>
          )}

          {((q.noi_dung && !isPieceList(q.noi_dung)) || q.tep_hinh) && (
            <div className={`sl-stem${q.noi_dung && !LATIN.test(q.noi_dung) && q.noi_dung.length <= 4 ? " sl-stem--word" : ""}`}>
              {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
              {q.noi_dung && !isPieceList(q.noi_dung) && (
                LATIN.test(q.noi_dung) ? <p>{q.noi_dung}</p> : <HanziText text={q.noi_dung} pinyin={q.pinyin} />
              )}
            </div>
          )}

          {CHOICE.includes(q.dang) ? (
            <div
              className={`sl-opts${step.phuong_an.some((o) => o.tep_hinh) ? " sl-opts--img" : ""}`}
              role="radiogroup"
              aria-label="Phương án trả lời"
            >
              {step.phuong_an.map((o, i) => (
                <button
                  key={o.id}
                  type="button"
                  role="radio"
                  aria-checked={o.id === pick}
                  className={`sl-opt${o.id === pick ? " is-picked" : ""}`}
                  disabled={busy}
                  onClick={() => setPick(o.id)}
                >
                  <kbd>{i + 1}</kbd>
                  <Option option={o} />
                </button>
              ))}
            </div>
          ) : q.dang === "sap_xep" && step.phuong_an?.length ? (
            <SentenceBuilder
              key={q.id}
              pieces={step.phuong_an}
              extra={[]}
              prompt={q.nghia_cau}
              value={text}
              onChange={setText}
              disabled={busy}
              answered={null}
            />
          ) : (
            <div className="wm-editor">
              <div className="wm-editor__bar">
                <span>Bản dịch tiếng Việt của bạn</span>
                <span>Viết theo ý hiểu tự nhiên</span>
              </div>
              <textarea
                placeholder="Nhập nghĩa tiếng Việt của câu trên…"
                value={text}
                disabled={busy}
                maxLength={500}
                onChange={(e) => setText(e.target.value)}
              />
              <div className="wm-editor__foot">
                <span>{countWords(text)} từ</span>
                <span>{text.length}/500 ký tự</span>
              </div>
            </div>
          )}

          <div className="wm-actions">
            <button
              type="button"
              className="xc-btn xc-btn--plain xc-btn--sm"
              onClick={() => sendStep(true)}
              disabled={busy}
            >
              Bỏ qua
            </button>
            <div className="wm-actions__right">
              <button
                type="button"
                className="xc-btn"
                onClick={() => sendStep(false)}
                disabled={busy || !hasAnswer}
              >
                {step.thu_tu === total ? "Hoàn tất đánh giá" : "Câu tiếp theo"} <Icon name="arrow" />
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
