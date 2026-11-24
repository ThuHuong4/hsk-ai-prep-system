import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import {
  approveExamJob,
  assembleJobAudio,
  fixJobItem,
  getExamJob,
  jobItemFile,
  markJobGreen,
  markJobItem,
  redoJobItem,
  resumeExamJob,
  uploadMedia,
} from "../api/lecturerApi.js";
import AiPartCard from "../components/AiPartCard.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { mediaUrl } from "../../../shared/utils/format.js";
import { slotId } from "../utils/aiExamParts.js";
import "../styles/lecturer.css";
import "../styles/aiExam.css";

/**
 * Giảng viên duyệt đề AI đã soạn: xem như tờ đề, đèn màu theo kết quả kiểm định tự động,
 * nghe cả bài Nghe (bấm câu nhảy tới đúng đoạn), Đạt / Nhờ AI sửa / Làm lại từng mục -> Duyệt và đăng đề.
 */
const KIND_LABEL = {
  nghe_tranh_dung_sai: "Nghe – tranh Đúng/Sai", nghe_chon_tranh: "Nghe – chọn tranh", nghe_noi_tranh: "Nghe – nối tranh A–F",
  nghe_chon_chu: "Nghe – chọn đáp án", nghe_phan_doan: "Nghe – phán đoán ★", nghe_doan_2cau: "Nghe – đoạn 2 câu hỏi",
  doc_tranh_tu: "Đọc – tranh và từ", doc_noi_tranh: "Đọc – nối tranh A–F", doc_ghep_cau: "Đọc – ghép câu A–F",
  doc_chon_tu: "Đọc – chọn từ điền", doc_phan_doan: "Đọc – phán đoán ★", doc_doan_chon: "Đọc – đoạn văn chọn đáp án",
  doc_doan_2cau: "Đọc – đoạn 2 câu hỏi", doc_sap_xep_doan: "Đọc – sắp xếp 3 câu", viet_sap_xep: "Viết – sắp xếp thành câu",
  viet_dien_chu: "Viết – viết chữ theo pinyin", viet_tranh: "Viết – xem tranh viết câu",
};
const DOT = { do: "🔴", vang: "🟡", xanh: "🟢" };

function Progress({ job }) {
  const step = job.buoc;
  const pct = step ? Math.round(((step.so - 1) / step.tong) * 100) : 5;
  return (
    <section className="lv-card ae-progress" aria-live="polite">
      <h2 className="lv-ai__title">AI đang soạn đề {job.cap}</h2>
      <div className="ae-bar"><span style={{ width: `${Math.max(5, pct)}%` }} /></div>
      <p><b>{step ? `Bước ${step.so}/${step.tong}: ${step.ten}` : "Đang xếp hàng…"}</b>{step?.chi_tiet ? ` · ${step.chi_tiet}` : ""}</p>
      <ol className="ae-steps">
        {["Soạn nội dung", "Kiểm định nội dung", "Tự sửa lỗi", "Tạo hình", "Tạo giọng đọc", "Ghép bài Nghe"].map((name, i) => (
          <li key={name} className={step && i + 1 < step.so ? "is-done" : step && i + 1 === step.so ? "is-now" : ""}>{name}</li>
        ))}
      </ol>
      <p className="lv-help">Bạn có thể rời trang; AI vẫn chạy và đề sẽ chờ bạn duyệt.</p>
    </section>
  );
}

export default function AiExamReviewPage() {
  const { id } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("can_xem");
  const [working, setWorking] = useState({}); // key -> mô tả việc đang chạy
  const [media, setMedia] = useState({}); // key -> {slotId: "dang" | lỗi}
  const [asks, setAsks] = useState({});
  const [info, setInfo] = useState({ ten: "", ma_de: "", thoi_luong_phut: "" });
  const [pauses, setPauses] = useState({});
  const [approving, setApproving] = useState(false);
  const tape = useRef(null);

  // ---------------------------------------------------------------- tải & theo dõi tiến trình
  useEffect(() => {
    let timer;
    const ctrl = new AbortController();
    async function tick() {
      try {
        const data = await getExamJob(token, id, ctrl.signal);
        setJob(data);
        if (data.trang_thai === "dang_chay") timer = setTimeout(tick, 3000);
      } catch (err) {
        if (err.name !== "AbortError") setError(err?.message || "Không tải được đề");
      }
    }
    tick();
    return () => { ctrl.abort(); clearTimeout(timer); };
  }, [id, token, job?.trang_thai === "dang_chay"]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!job) return;
    setInfo((x) => (x.ten ? x : {
      ten: `Đề thi thử ${job.cap} – AI ${(job.tao_luc || "").slice(0, 10)}`,
      ma_de: `${job.cap.replace(/\s+/g, "")}_AI_${job.id.slice(0, 4).toUpperCase()}`,
      thoi_luong_phut: job.thoi_luong_phut,
    }));
    setPauses((x) => (Object.keys(x).length ? x : Object.fromEntries(job.phan.filter((p) => p.nghi).map((p) => [p.phan, p.nghi]))));
  }, [job]);

  const marks = useMemo(() => {
    const map = {};
    (job?.am_thanh?.moc || []).forEach((m) => { for (let n = m.so; n <= m.den; n += 1) map[n] = m; });
    return map;
  }, [job]);

  // ---------------------------------------------------------------- thao tác
  async function act(key, label, fn) {
    setWorking((w) => ({ ...w, [key]: label }));
    setError("");
    try {
      const data = await fn();
      if (data?.the) setJob(data);
      return data;
    } catch (err) {
      setError(err?.message || "Thao tác chưa thành công");
      return null;
    } finally {
      setWorking((w) => ({ ...w, [key]: undefined }));
    }
  }

  async function fileAction(key, path, run) {
    const sid = slotId(path);
    setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: "dang" } }));
    try {
      setJob(await run());
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: undefined } }));
    } catch (err) {
      setMedia((m) => ({ ...m, [key]: { ...(m[key] || {}), [sid]: err?.message || "Thất bại" } }));
    }
  }

  const regen = (key, path) => fileAction(key, path, () => jobItemFile(token, id, key, path));
  const upload = (key, path, file) => fileAction(key, path, async () => {
    const kind = path[path.length - 1] === "tep_hinh" ? "hinh" : "audio";
    const up = await uploadMedia(token, kind, file);
    return jobItemFile(token, id, key, path, up.duong_dan);
  });

  async function sendFix(key) {
    const text = (asks[key] || "").trim();
    if (!text) return;
    const data = await act(key, "AI đang sửa và kiểm định lại", () => fixJobItem(token, id, key, text));
    if (data) setAsks((a) => ({ ...a, [key]: "" }));
  }

  function playAt(no) {
    const m = marks[no];
    if (!m || !tape.current) return;
    tape.current.currentTime = m.bat_dau;
    tape.current.play().catch(() => {});
  }

  async function approve() {
    setApproving(true);
    setError("");
    try {
      const data = await approveExamJob(token, id, {
        ten: info.ten.trim(), ma_de: info.ma_de.trim(), thoi_luong_phut: Number(info.thoi_luong_phut) || null,
      });
      navigate(`/giang-vien/bo-de/${data.bo_de_id}`, { state: { thongBao: data.ghi_chu || "Đã duyệt và đăng đề." } });
    } catch (err) {
      setError(err?.message || "Chưa duyệt được");
      getExamJob(token, id).then(setJob).catch(() => {});
    } finally {
      setApproving(false);
    }
  }

  // ---------------------------------------------------------------- hiển thị
  if (error && !job) return <section className="lv-page"><p className="lv-alert">{error}</p></section>;
  if (!job) return <section className="lv-page"><p className="lv-help">Đang tải…</p></section>;

  const back = <Link to="/giang-vien/bo-de/ai" className="lv-back"><Icon name="back" size={18} /> Tạo đề với AI</Link>;
  if (job.trang_thai === "dang_chay") return <section className="lv-page">{back}<Progress job={job} /></section>;
  if (job.trang_thai === "gian_doan" || job.trang_thai === "loi") {
    return (
      <section className="lv-page">
        {back}
        <div className="lv-card">
          <h2 className="lv-ai__title">{job.trang_thai === "loi" ? "AI gặp lỗi khi soạn đề" : "Phiên soạn đề bị gián đoạn"}</h2>
          <p>{job.loi || "Máy chủ đã khởi động lại giữa chừng."} Phần đã làm vẫn được giữ.</p>
          <button type="button" className="xbtn" onClick={() => act("job", "", async () => { await resumeExamJob(token, id); return getExamJob(token, id); })}>
            <Icon name="replay" /> Chạy tiếp
          </button>
        </div>
      </section>
    );
  }

  const done = job.trang_thai === "da_duyet";
  const pending = job.the.filter((c) => !c.duyet);
  const notOk = pending.filter((c) => !c.da_xem);
  const reds = pending.filter((c) => c.den === "do").length;
  const total = job.phan.reduce((n, p) => n + p.so_cau, 0);
  const haveTotal = job.the.reduce((n, c) => n + c.so_cau, 0);
  const listenParts = job.phan.filter((p) => p.ky_nang === "nghe");
  const totalListen = listenParts.reduce((n, p) => n + p.so_cau, 0);
  const hasContinuousTape = Boolean(job.am_thanh?.duong_dan);
  const needsAutoComplete = !done && (haveTotal < total || reds > 0 || (listenParts.length > 0 && !hasContinuousTape));
  const shown = (cards) => (filter === "can_xem" ? cards.filter((c) => !c.da_xem && !c.duyet) : cards);
  const anyBusy = Object.values(working).some(Boolean);

  return (
    <section className="lv-page ae-review">
      {back}
      <div className="lv-page__head">
        <div className="lv-page__intro">
          <h1>Duyệt đề {job.cap}{job.chu_de ? ` · ${job.chu_de}` : ""}</h1>
          <p>
            <span className="ae-count">📋 Cấu trúc: {haveTotal}/{total} câu chuẩn {job.cap}</span>
            <span className="ae-count">{DOT.do} {job.dem.do} thiếu tệp/lỗi</span>
            <span className="ae-count">{DOT.vang} {job.dem.vang} cần lưu ý</span>
            <span className="ae-count">{DOT.xanh} {job.dem.xanh} qua hết kiểm tra</span>
            <span className="ae-count">✔ {job.the.length - notOk.length}/{job.the.length} mục đã Đạt</span>
          </p>
        </div>
        {!done && (
          <div className="lv-actions">
            {job.dem.xanh > 0 && (
              <button type="button" className="xbtn xbtn--ghost" disabled={anyBusy}
                onClick={() => act("all-green", "", () => markJobGreen(token, id, null, false))}>
                <Icon name="check" /> Đạt mục {DOT.xanh}
              </button>
            )}
            <button type="button" className="xbtn" disabled={anyBusy || notOk.filter((c) => c.den !== "do").length === 0}
              onClick={() => act("all-valid", "", () => markJobGreen(token, id, null, true))}>
              <Icon name="check" /> Đạt tất cả mục hợp lệ
            </button>
          </div>
        )}
      </div>

      {needsAutoComplete && (
        <div className="lv-card lv-card--warn" role="status">
          <div>
            <strong>Đề đang còn thiếu thành phần so với cấu trúc chuẩn {job.cap}:</strong>{" "}
            {haveTotal < total && `mới có ${haveTotal}/${total} câu; `}
            {reds > 0 && `còn ${reds} mục thiếu hình hoặc âm thanh; `}
            {listenParts.length > 0 && !hasContinuousTape && "chưa ghép xong băng Nghe liên tiếp."}
          </div>
          <button type="button" className="xbtn" disabled={anyBusy}
            onClick={() => act("resume-fill", "", async () => { await resumeExamJob(token, id); return getExamJob(token, id); })}>
            <Icon name="spark" /> Tự động bù đủ câu, hình ảnh & ghép băng Nghe liên tiếp
          </button>
        </div>
      )}

      {error && <p role="alert" className="lv-alert">{error}</p>}
      {done && <p className="lv-ai__ok">Đề đã duyệt và xuất bản. <Link to={`/giang-vien/bo-de/${job.bo_de_id}`}>Mở đề thi</Link></p>}

      {listenParts.length > 0 && (
        <section className="lv-card ae-tape" aria-label="Băng Nghe liên tiếp toàn đề">
          <div className="ae-tape__head">
            <div>
              <h2 className="lv-ai__title">
                <Icon name="audio" /> Băng Nghe liên tiếp toàn phần Nghe (Câu 1–{totalListen})
                {job.am_thanh?.giay ? ` · ${Math.floor(job.am_thanh.giay / 60)} phút ${job.am_thanh.giay % 60} giây` : ""}
              </h2>
              <p className="lv-help">
                Khi học viên làm bài thi thử, hệ thống phát <b>duy nhất 1 băng MP3 liên tiếp này từ Câu 1 đến Câu {totalListen}</b> (gồm lời mở đầu, hướng dẫn từng phần, đọc lặp câu và khoảng nghỉ chọn đáp án — không ngắt rời từng câu).
              </p>
            </div>
            {job.am_thanh?.cu && <span className="ae-st ae-st--bad">Có câu vừa sửa lời nghe: bấm Ghép lại băng Nghe</span>}
          </div>
          {job.am_thanh?.duong_dan ? (
            <>
              <audio ref={tape} controls preload="metadata" src={mediaUrl(job.am_thanh.duong_dan)} className="ae-tape__player" />
              <div className="ae-tape__jumps" aria-label="Nhảy nhanh tới từng phần trong băng Nghe">
                {(() => {
                  let startNo = 1;
                  return listenParts.map((lp) => {
                    const pStart = startNo;
                    const pEnd = startNo + lp.so_cau - 1;
                    startNo += lp.so_cau;
                    return (
                      <button key={lp.phan} type="button" className="xbtn xbtn--ghost xbtn--sm"
                        disabled={!marks[pStart]} onClick={() => playAt(pStart)}>
                        <Icon name="play" size={13} /> {lp.ten} (Câu {pStart}–{pEnd})
                      </button>
                    );
                  });
                })()}
              </div>
            </>
          ) : (
            <p className="lv-ai__warn">{job.am_thanh?.loi || "Chưa ghép được băng Nghe liên tiếp — bấm nút Tự động bù ở trên hoặc Ghép lại bên dưới."}</p>
          )}
          {!done && (
            <details className="ae-more">
              <summary>Tùy chỉnh giây nghỉ sau mỗi câu & ghép lại băng Nghe</summary>
              <div className="ae-tape__opts">
                {listenParts.map((p) => (
                  <label key={p.phan} className="lv-field ae-pause">
                    <span className="zh">{p.ten}</span> nghỉ sau mỗi câu (giây)
                    <input type="number" min={3} max={60} value={pauses[p.phan] ?? p.nghi}
                      onChange={(e) => setPauses((x) => ({ ...x, [p.phan]: e.target.value }))} />
                  </label>
                ))}
                <button type="button" className="xbtn xbtn--ghost" disabled={anyBusy}
                  onClick={() => act("tape", "", () => assembleJobAudio(token, id,
                    Object.fromEntries(Object.entries(pauses).map(([k, v]) => [k, Number(v) || 10]))))}>
                  <Icon name="replay" /> {working.tape !== undefined ? "Đang ghép…" : "Ghép lại băng Nghe"}
                </button>
              </div>
            </details>
          )}
        </section>
      )}

      <div className="ae-layout">
        <nav className="ae-parts" aria-label="Danh sách câu">
          <div className="ae-filter" role="tablist">
            <button type="button" className={filter === "can_xem" ? "is-active" : ""} onClick={() => setFilter("can_xem")}>
              Chưa Đạt ({notOk.reduce((n, c) => n + c.so_cau, 0)} câu)
            </button>
            <button type="button" className={filter === "tat_ca" ? "is-active" : ""} onClick={() => setFilter("tat_ca")}>
              Tất cả ({haveTotal} câu)
            </button>
          </div>
          <div className="ae-grid">
            {job.the.flatMap((c) =>
              Array.from({ length: c.so_cau }, (_, offset) => {
                const qNum = (c.so || 1) + offset;
                const targetHref = c.so_cau > 1 ? `#cau-${qNum}` : `#muc-${c.key}`;
                return (
                  <a key={`${c.key}-${qNum}`} href={targetHref}
                    onClick={() => { if (filter === "can_xem" && (c.da_xem || c.duyet)) setFilter("tat_ca"); }}
                    className={`ae-dot ae-dot--${c.den}${c.da_xem || c.duyet ? " is-ok" : ""}`}
                    title={c.so_cau > 1 ? `Câu ${qNum} (thuộc cụm Câu ${c.so}–${c.so + c.so_cau - 1})` : `Câu ${qNum}`}>
                    {qNum}{c.da_xem || c.duyet ? "✓" : ""}
                  </a>
                );
              }),
            )}
          </div>
          <p className="lv-help">Đỏ: phải xử lý mới duyệt được · Vàng: AI còn nghi ngờ, nên xem kỹ · Xanh: qua mọi lớp kiểm tra.</p>
        </nav>

        <div className="ae-main">
          {job.phan.map((p) => {
            const cards = shown(job.the.filter((c) => c.phan === p.phan));
            const all = job.the.filter((c) => c.phan === p.phan);
            const have = all.reduce((n, c) => n + c.so_cau, 0);
            return (
              <section key={p.phan} className="lv-card" aria-label={p.ten}>
                <div className="ae-part__head">
                  <div>
                    <h2 className="lv-ai__title"><span className="zh">{p.ten}</span> · {p.mo_ta}</h2>
                    <p className="lv-help">{have}/{p.so_cau} câu{have < p.so_cau ? " — thiếu câu so với cấu trúc, bấm Làm lại ở mục bất kỳ hoặc tạo lại đề" : ""}</p>
                  </div>
                  {!done && all.some((c) => c.den === "xanh" && !c.da_xem) && (
                    <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={anyBusy}
                      onClick={() => act(`p${p.phan}`, "", () => markJobGreen(token, id, p.phan))}>
                      Đạt các mục {DOT.xanh} của phần này
                    </button>
                  )}
                </div>
                {cards.length === 0 && <p className="lv-help">Phần này đã Đạt hết.</p>}
                <ol className="ae-list">
                  {cards.map((c) => {
                    const busy = working[c.key];
                    const last = (c.trao_doi || []).filter((t) => t.vai_tro === "ai").slice(-1)[0];
                    const actions = done || c.duyet ? null : (
                      <div className="ae-review__actions">
                        {p.ky_nang === "nghe" && marks[c.so] && (
                          <button type="button" className="xbtn xbtn--ghost xbtn--sm" onClick={() => playAt(c.so)}>
                            <Icon name="play" size={14} /> Nghe từ câu {c.so} trên băng chung
                          </button>
                        )}
                        <button type="button" className={`xbtn xbtn--sm${c.da_xem ? " xbtn--ghost" : ""}`} disabled={Boolean(busy) || (c.den === "do" && !c.da_xem)}
                          onClick={() => act(c.key, "", () => markJobItem(token, id, c.key, !c.da_xem))}>
                          <Icon name="check" size={14} /> {c.da_xem ? "Bỏ Đạt" : "Đạt"}
                        </button>
                        <form className="ae-ask" onSubmit={(e) => { e.preventDefault(); sendFix(c.key); }}>
                          <input value={asks[c.key] || ""} maxLength={1000} disabled={Boolean(busy)} aria-label={`Nhờ AI sửa câu ${c.so}`}
                            placeholder="Nhờ AI sửa: vd “đáp án B cũng đúng, đổi B”, “tranh C giống tranh A quá”"
                            onChange={(e) => setAsks((a) => ({ ...a, [c.key]: e.target.value }))} />
                          <button type="submit" className="xbtn xbtn--ghost xbtn--sm" disabled={Boolean(busy) || !(asks[c.key] || "").trim()}>
                            <Icon name="spark" size={14} /> Sửa
                          </button>
                        </form>
                        <button type="button" className="xbtn xbtn--ghost xbtn--sm" disabled={Boolean(busy)}
                          onClick={() => act(c.key, "AI đang soạn lại", () => redoJobItem(token, id, c.key))}>
                          <Icon name="replay" size={14} /> Làm lại
                        </button>
                        {busy && <span className="ae-busy">{busy}… (30–90 giây)</span>}
                        {last && <p className="lv-ai__msg lv-ai__msg--ai"><b>AI:</b> {last.noi_dung}</p>}
                      </div>
                    );
                    return (
                      <div key={c.key} id={`muc-${c.key}`} className={`ae-wrap ae-wrap--${c.den}${c.da_xem ? " is-ok" : ""}`}>
                        <AiPartCard card={c} from={c.so} label={`${DOT[c.den]} ${KIND_LABEL[c.muc.kieu]}${c.da_xem ? " · Đã Đạt" : ""}`}
                          media={media[c.key] || {}} busy={Boolean(busy)}
                          onRegen={(path) => regen(c.key, path)} onUpload={(path, file) => upload(c.key, path, file)}
                          review={{
                            red: c.ly_do_do,
                            yellow: c.ly_do_vang,
                            actions,
                            locked: done,
                            continuousTape: p.ky_nang === "nghe" && hasContinuousTape,
                          }} />
                      </div>
                    );
                  })}
                </ol>
              </section>
            );
          })}

          {!done && (
            <section className="lv-card ae-final" aria-label="Duyệt và đăng đề">
              <h2 className="lv-ai__title">Duyệt và đăng đề</h2>
              <p className="lv-help">
                {notOk.length ? `Còn ${notOk.length} mục chưa Đạt${reds ? ` (${reds} mục đỏ phải xử lý trước)` : ""}.` : "Mọi mục đã Đạt."}{" "}
                Đề có {job.the.reduce((n, c) => n + c.so_cau, 0)}/{total} câu. Khi duyệt, câu được lưu vào ngân hàng (nguồn “Soạn với AI”, ghi tên bạn là người duyệt),
                đề được tạo kèm bài Nghe chung và đăng ngay.
              </p>
              <div className="lv-grid-3">
                <div className="lv-field">
                  <label htmlFor="ar-name">Tên đề</label>
                  <input id="ar-name" maxLength={150} value={info.ten} onChange={(e) => setInfo((x) => ({ ...x, ten: e.target.value }))} />
                </div>
                <div className="lv-field">
                  <label htmlFor="ar-code">Mã đề</label>
                  <input id="ar-code" maxLength={30} value={info.ma_de} onChange={(e) => setInfo((x) => ({ ...x, ma_de: e.target.value }))} />
                </div>
                <div className="lv-field">
                  <label htmlFor="ar-time">Thời lượng (phút)</label>
                  <input id="ar-time" type="number" min={1} max={300} value={info.thoi_luong_phut}
                    onChange={(e) => setInfo((x) => ({ ...x, thoi_luong_phut: e.target.value }))} />
                </div>
              </div>
              <button type="button" className="xbtn" onClick={approve}
                disabled={approving || anyBusy || notOk.length > 0 || !info.ten.trim() || info.ma_de.trim().length < 2}>
                <Icon name="check" /> {approving ? "Đang lưu và đăng…" : "Duyệt và đăng đề"}
              </button>
            </section>
          )}
        </div>
      </div>
    </section>
  );
}
