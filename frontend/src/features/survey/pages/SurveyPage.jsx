import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import "../../../layouts/staffShell.css";
import { getSurvey, skipSurvey, submitSurvey } from "../api/surveyApi.js";
import "../styles/survey.css";

const firstName = (name) => (name || "").trim().split(/\s+/).pop() || "bạn";

// 5 câu khảo sát; chỉ làm một lần, không xếp trình độ
function questions(levels) {
  return [
    { key: "da_hoc", title: "Bạn đã học tiếng Trung chưa?",
      options: [{ v: "chua", label: "Chưa học", hint: "Mình mới bắt đầu" }, { v: "da_hoc", label: "Đã học", hint: "Mình đã học một thời gian" }] },
    { key: "cap_muc_tieu_id", title: "Bạn muốn ôn hoặc thi HSK mấy?",
      options: levels.map((l) => ({ v: l.id, label: l.ten })) },
    { key: "muc_dich", title: "Bạn dùng Xianglingo để làm gì?",
      options: [{ v: "on_luyen", label: "Ôn luyện", hint: "Học theo từng thửa" }, { v: "thi_thu", label: "Thi thử", hint: "Làm đề tính giờ" },
        { v: "ca_hai", label: "Cả hai" }] },
    { key: "ky_nang", title: "Bạn muốn cải thiện kỹ năng nào nhất?",
      options: [{ v: "nghe", label: "Nghe", hz: "听" }, { v: "doc", label: "Đọc", hz: "读" }, { v: "viet", label: "Viết", hz: "写" },
        { v: "tu_vung", label: "Từ vựng", hz: "词" }] },
    { key: "phut_moi_ngay", title: "Mỗi ngày bạn học được bao lâu?",
      options: [10, 15, 30, 60].map((m) => ({ v: m, label: `${m} phút` })) },
  ];
}

export default function SurveyPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const { data, error } = useRequest((signal) => getSurvey(token, signal), [token]);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const [fail, setFail] = useState("");
  const [result, setResult] = useState(null);

  if (data && data.trang_thai !== "chua_lam" && !result) return <Navigate to="/hoc-vien" replace />;

  const list = data ? questions(data.cap_do) : [];
  const q = list[step];
  const value = q ? answers[q.key] : undefined;

  async function skip() {
    setBusy(true);
    try { await skipSurvey(token); } catch { /* vẫn về trang chủ */ }
    navigate("/hoc-vien", { replace: true });
  }

  async function next() {
    if (step < list.length - 1) { setStep(step + 1); return; }
    setBusy(true); setFail("");
    try {
      const res = await submitSurvey(token, answers);
      setResult(res.goi_y);
    } catch (err) {
      setFail(err?.message || "Chưa lưu được khảo sát, hãy thử lại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="xg xc sv" data-theme={theme}>
      <div className="sv-wrap">
        {!result && (
          <header className="sv-top">
            <span className="sv-progress" role="progressbar" aria-valuemin={0} aria-valuemax={list.length || 5} aria-valuenow={step + 1}
              aria-label="Tiến độ khảo sát"><i style={{ width: `${list.length ? (100 * (step + 1)) / list.length : 0}%` }} /></span>
            <button type="button" className="sv-skip" disabled={busy} onClick={skip}>Bỏ qua</button>
          </header>
        )}
        {error && <p role="alert">{error}</p>}
        {!data && !error && <p className="xc-muted">Đang tải...</p>}

        {data && !result && q && (
          <main className="sv-main">
            <div className="sv-bubble">
              <img src={xiangFace} alt="" />
              <p>{step === 0 ? `Chào ${firstName(user?.ho_ten)}! Trả lời nhanh 5 câu để Xiang đưa bạn tới đúng chỗ nhé.` : `Câu ${step + 1}/${list.length}`}</p>
            </div>
            <h1>{q.title}</h1>
            <div className={`sv-opts${q.options.length > 3 ? " sv-opts--grid" : ""}`} role="radiogroup" aria-label={q.title}>
              {q.options.map((o) => (
                <button key={o.v} type="button" role="radio" aria-checked={value === o.v}
                  className={`sv-opt${value === o.v ? " is-on" : ""}`} onClick={() => setAnswers({ ...answers, [q.key]: o.v })}>
                  {o.hz && <span className="sv-hz hz" aria-hidden="true">{o.hz}</span>}
                  <span><b>{o.label}</b>{o.hint && <small>{o.hint}</small>}</span>
                </button>
              ))}
            </div>
            {fail && <p role="alert">{fail}</p>}
            <div className="sv-acts">
              <button type="button" className="xc-btn xc-btn--plain" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>Quay lại</button>
              <button type="button" className="xc-btn" disabled={value === undefined || busy} onClick={next}>
                {step === list.length - 1 ? (busy ? "Đang lưu..." : "Hoàn tất") : "Tiếp tục"}
              </button>
            </div>
            <p className="sv-note">Câu trả lời chỉ dùng để đưa bạn tới đúng trang, không dùng để xếp trình độ.</p>
          </main>
        )}

        {result && (
          <main className="sv-main sv-result">
            <div className="sv-card">
              <img className="sv-card__xiang" src={xiangFace} alt="" />
              <span className="xc-eyebrow">Xiang gợi ý</span>
              <h1>{result.tieu_de}</h1>
              <p>{result.ly_do}</p>
              <div className="sv-acts">
                <Link className="xc-btn xc-btn--plain" to="/hoc-vien" replace>Chọn khác</Link>
                <Link className="xc-btn" to={result.duong_dan} replace>Bắt đầu ngay <Icon name="arrow" /></Link>
              </div>
            </div>
          </main>
        )}
      </div>
    </div>
  );
}
