import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { createExamJob, deleteExamJob, getExamBlueprint, listExamJobs } from "../api/lecturerApi.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useLevels } from "../hooks/useLevels.js";
import "../styles/lecturer.css";
import "../styles/aiExam.css";

/**
 * Tạo đề hoàn chỉnh với AI theo khung cấu trúc chuẩn HSK 2.0 cố định:
 * Giảng viên chọn cấp -> xem ngay Khung cấu trúc chuẩn HSK (Nghe liên tiếp 1 băng + Đọc + Viết) -> bấm Tạo 1 chạm
 * -> AI soạn nội dung mới, tạo đủ hình ảnh, tạo giọng đọc đa vai và ghép 1 băng Nghe liên tiếp -> Giảng viên duyệt & đăng.
 */
const STATUS = {
  dang_chay: ["AI đang soạn", "ae-st--run"],
  gian_doan: ["Bị gián đoạn", "ae-st--bad"],
  loi: ["Cần chạy tiếp", "ae-st--bad"],
  cho_duyet: ["Chờ duyệt", "ae-st--wait"],
  da_duyet: ["Đã duyệt & đăng", "ae-st--ok"],
};

const LAYERS = [
  ["ai", "AI soạn câu hỏi", "OPENAI_API_KEY + OPENAI_MODEL"],
  ["tao_hinh", "Tạo hình minh họa miễn phí", "Pollinations Flux + Kho ảnh thực tế"],
  ["giong_doc", "Băng Nghe tiếng Trung liên tiếp", "Edge Neural TTS (Nam / Nữ / Phát thanh viên)"],
  ["nhin_anh", "AI kiểm tra tranh", "Gemini Vision"],
  ["nghe_lai", "AI kiểm tra âm thanh", "Gemini Audio / Whisper"],
];

const SKILL_SECTION_TITLE = {
  nghe: "一、听力 · Phần Nghe (phát liên tiếp 1 băng MP3 duy nhất, không ngắt từng câu)",
  doc: "二、阅读 · Phần Đọc hiểu",
  viet: "三、书写 · Phần Viết",
};

export default function AiExamHomePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const levels = useLevels();
  const [form, setForm] = useState({ cap_do_id: "", chu_de: "", yeu_cau: "" });
  const [blueprint, setBlueprint] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [ready, setReady] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!form.cap_do_id && levels.length) {
      setForm((f) => ({ ...f, cap_do_id: location.state?.cap_do_id ?? levels[0].ma_cap_do }));
    }
  }, [levels]); // eslint-disable-line react-hooks/exhaustive-deps

  function load(signal) {
    return listExamJobs(token, signal)
      .then((data) => { setJobs(data.phien || []); setReady(data.san_sang); })
      .catch((err) => { if (err.name !== "AbortError") setError(err?.message || "Không tải được danh sách"); });
  }

  useEffect(() => {
    const ctrl = new AbortController();
    load(ctrl.signal);
    return () => ctrl.abort();
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!form.cap_do_id || !token) return undefined;
    const ctrl = new AbortController();
    getExamBlueprint(token, Number(form.cap_do_id), ctrl.signal)
      .then(setBlueprint)
      .catch(() => setBlueprint(null));
    return () => ctrl.abort();
  }, [form.cap_do_id, token]);

  const groupedBlueprint = useMemo(() => {
    if (!blueprint?.phan) return [];
    let cursor = 1;
    const bySkill = new Map();
    for (const p of blueprint.phan) {
      const from = cursor;
      const to = cursor + p.so_cau - 1;
      cursor += p.so_cau;
      if (!bySkill.has(p.ky_nang)) bySkill.set(p.ky_nang, []);
      bySkill.get(p.ky_nang).push({ ...p, from, to });
    }
    return Array.from(bySkill.entries()).map(([ky_nang, parts]) => ({
      ky_nang,
      title: SKILL_SECTION_TITLE[ky_nang] || ky_nang,
      total: parts.reduce((sum, x) => sum + x.so_cau, 0),
      parts,
    }));
  }, [blueprint]);

  const totalQuestions = useMemo(
    () => (blueprint?.phan || []).reduce((sum, p) => sum + p.so_cau, 0),
    [blueprint],
  );

  async function start(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await createExamJob(token, {
        cap_do_id: Number(form.cap_do_id), chu_de: form.chu_de.trim() || null, yeu_cau: form.yeu_cau.trim() || null,
      });
      navigate(`/giang-vien/bo-de/ai/${data.id}`);
    } catch (err) {
      setError(err?.message || "Chưa bắt đầu được");
      setBusy(false);
    }
  }

  async function remove(job) {
    if (!window.confirm("Bỏ phiên soạn đề này? Câu đã duyệt (nếu có) vẫn còn trong ngân hàng.")) return;
    try {
      await deleteExamJob(token, job.id);
      load();
    } catch (err) {
      setError(err?.message || "Không bỏ được");
    }
  }

  return (
    <section className="lv-page">
      <Link to="/giang-vien/bo-de" className="lv-back"><Icon name="back" size={18} /> Đề thi thử HSK</Link>
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Soạn đề chuẩn cấu trúc HSK với AI</h1>
          <p>
            Giữ cố định <b>100% khung cấu trúc, số phần, dạng câu và thời lượng đề HSK quốc tế</b> — AI chỉ biên soạn
            ngữ liệu câu hỏi mới, tạo đủ hình ảnh minh họa và <b>ghép liền mạch toàn bộ phần Nghe thành 1 băng MP3 liên tiếp</b>.
          </p>
        </div>
      </div>

      <form className="lv-card ae-hero" onSubmit={start}>
        <fieldset disabled={busy || !levels.length}>
          <div className="lv-grid-3">
            <div className="lv-field">
              <label htmlFor="aj-level">1. Chọn cấp độ đề cần tạo</label>
              <select id="aj-level" value={form.cap_do_id} onChange={(e) => setForm((f) => ({ ...f, cap_do_id: e.target.value }))}>
                {levels.map((l) => <option key={l.ma_cap_do} value={l.ma_cap_do}>{l.ten_cap_do}</option>)}
              </select>
            </div>
            <div className="lv-field">
              <label htmlFor="aj-topic">2. Chủ đề tình huống (không bắt buộc)</label>
              <input id="aj-topic" maxLength={200} value={form.chu_de} placeholder="Để trống = AI phối đa dạng đời sống như đề thật"
                onChange={(e) => setForm((f) => ({ ...f, chu_de: e.target.value }))} />
            </div>
            <div className="lv-field">
              <label htmlFor="aj-req">3. Ghi chú thêm cho AI (không bắt buộc)</label>
              <input id="aj-req" maxLength={1000} value={form.yeu_cau} placeholder="Ví dụ: ưu tiên từ vựng giao tiếp trường học, gia đình"
                onChange={(e) => setForm((f) => ({ ...f, yeu_cau: e.target.value }))} />
            </div>
          </div>

          {blueprint && (
            <div className="ae-bp-box" aria-label="Khung cấu trúc đề chuẩn HSK">
              <div className="ae-bp-box__head">
                <strong>
                  Khung cấu trúc cố định {blueprint.cap}: {totalQuestions} câu tính điểm · {blueprint.thoi_luong_phut} phút
                </strong>
                <span>
                  {blueprint.phat_nghe > 1
                    ? `Phần Nghe đọc ${blueprint.phat_nghe} lần/câu, phát liên tiếp từ đầu đến hết phần Nghe`
                    : "Phần Nghe đọc 1 lần/câu, phát liên tiếp toàn phần"}
                </span>
              </div>
              <div className="ae-bp-groups">
                {groupedBlueprint.map((g) => (
                  <div key={g.ky_nang} className="ae-bp-group">
                    <p className="ae-bp-group__title">
                      <b>{g.title}</b> <span>({g.total} câu)</span>
                    </p>
                    <ul className="ae-bp-parts">
                      {g.parts.map((p) => (
                        <li key={p.phan}>
                          <span className="ae-bp-range">Câu {p.from}–{p.to}</span>
                          <span className="zh ae-bp-zh">{p.ten}</span>
                          <span className="ae-bp-desc">{p.mo_ta}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="lv-actions">
            <button type="submit" className="xbtn ae-hero__go" disabled={ready && !ready.ai}>
              <Icon name="spark" /> {busy ? "Đang khởi tạo…" : `Tạo bộ đề ${blueprint?.cap || "HSK"} mới đúng cấu trúc`}
            </button>
            <span className="lv-help">
              AI tự làm trọn gói 6 bước (khoảng 3–8 phút). Bạn có thể rời trang và quay lại bấm Duyệt khi xong.
            </span>
          </div>
        </fieldset>
        {ready && (
          <ul className="ae-layers" aria-label="Các lớp AI đang bật">
            {LAYERS.map(([k, name, env]) => (
              <li key={k} className={ready[k] ? "is-on" : "is-off"} title={ready[k] ? `Đang bật (${env})` : `Chưa bật (${env})`}>
                <Icon name={ready[k] ? "check" : "x"} size={14} /> {name}
              </li>
            ))}
          </ul>
        )}
      </form>

      {error && <p role="alert" className="lv-alert">{error}</p>}

      <section className="lv-card" aria-label="Các phiên soạn đề AI">
        <h2 className="lv-ai__title">Các bộ đề AI đã tạo</h2>
        {jobs.length === 0 ? <p className="lv-help">Chưa có phiên soạn đề nào. Bấm nút tạo bộ đề ở trên để bắt đầu.</p> : (
          <ul className="ae-jobs">
            {jobs.map((j) => (
              <li key={j.id}>
                <Link to={`/giang-vien/bo-de/ai/${j.id}`}>
                  <b>{j.cap}{j.chu_de ? ` · ${j.chu_de}` : " · Đề chuẩn cấu trúc HSK"}</b>
                  <small>
                    {(j.tao_luc || "").replace("T", " ").slice(0, 16)} ·{" "}
                    {j.so_cau != null ? `${j.so_cau}/${j.tong_cau} câu` : `${j.so_muc} mục`}
                  </small>
                </Link>
                <span className={`ae-st ${STATUS[j.trang_thai]?.[1] || ""}`}>{STATUS[j.trang_thai]?.[0] || j.trang_thai}</span>
                {j.trang_thai !== "dang_chay" && (
                  <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => remove(j)} aria-label="Bỏ phiên">
                    <Icon name="x" size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <details className="ae-more">
        <summary>Tùy chọn nâng cao (dành cho giảng viên muốn tự chỉnh thủ công từng phần)</summary>
        <p className="lv-help">
          <Link to="/giang-vien/bo-de/ai-tung-phan">Soạn và duyệt lẻ từng phần</Link> ·{" "}
          <Link to="/giang-vien/bo-de/ai-ngan-hang">Ghép đề từ câu hỏi có sẵn trong ngân hàng</Link> (cả hai cách đều tự động ghép 1 băng Nghe liên tiếp khi tạo đề).
        </p>
      </details>
    </section>
  );
}
