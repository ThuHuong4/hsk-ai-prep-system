import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import xiangFace from "../../../assets/images/xiang/home/xiang_face.webp";
import "../../../layouts/staffShell.css";
import HanziText from "../../../shared/components/HanziText.jsx";
import Icon from "../../../shared/components/Icon.jsx";
import { CHOICE, LATIN, Option, SKILL, instruction } from "../../../shared/components/LessonParts.jsx";
import SentenceBuilder, { isPieceList, pickDistractors } from "../../../shared/components/SentenceBuilder.jsx";
import { useTheme } from "../../../shared/hooks/useTheme.js";
import { mediaUrl, splitOption } from "../../../shared/utils/format.js";
import XiangChat from "../../ai_tutor/components/XiangChat.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import DailyMissions from "../../notebook/components/DailyMissions.jsx";
import ReportQuestionButton from "../../reports/components/ReportQuestionButton.jsx";
import { pronounceUrl } from "../../search/api/searchApi.js";
import "../../exam_catalog/styles/catalog.css";
import "../../mock_test/styles/mockTest.css";
import {
  abandonAttempt,
  checkAnswer,
  getLessonAttempt,
  markLessonSolutionViewed,
  openLessonHint,
  startLesson,
} from "../api/practiceApi.js";
import "../styles/practice.css";
import { skillSlug } from "../utils/skills.js";

export default function LessonPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [pick, setPick] = useState(null);
  const [text, setText] = useState("");
  const [shown, setShown] = useState(null);
  const [revealAnswer, setRevealAnswer] = useState(false);
  const [wordFlipped, setWordFlipped] = useState(false);
  const [busy, setBusy] = useState(false);
  const [exitOpen, setExitOpen] = useState(false);
  const [energyOpen, setEnergyOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const load = useCallback(
    (signal) =>
      getLessonAttempt(token, luotId, signal).then((d) => {
        if (d.trang_thai === "da_bo") {
          navigate(`/hoc-vien/on-luyen/${skillSlug(d.bai.ky_nang)}?cap=${d.bai.cap_do_id}`, { replace: true });
          return;
        }
        setData(d);
      }),
    [token, luotId, navigate]
  );

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setShown(null);
    setRevealAnswer(false);
    setWordFlipped(false);
    setPick(null);
    setText("");
    load(controller.signal).catch((err) => err?.name !== "AbortError" && setError(err?.message || "Không tải được bài"));
    return () => controller.abort();
  }, [load]);

  const mapUrl = data ? `/hoc-vien/on-luyen/${skillSlug(data.bai.ky_nang)}?cap=${data.bai.cap_do_id}` : "/hoc-vien/on-luyen";
  const items = data?.cau_hoi ?? [];
  const current = useMemo(() => {
    if (shown != null) return items.find((i) => i.thu_tu === shown);
    return items.find((i) => !i.ket_qua);
  }, [items, shown]);
  const doneCount = items.filter((i) => i.ket_qua).length;

  async function submit(skip = false) {
    if (!current || busy) return;
    const q = current.cau_hoi;
    const body = { cau_hoi_id: q.id, phuong_an_chon_id: null, van_ban: null };
    if (!skip) {
      if (CHOICE.includes(q.dang)) body.phuong_an_chon_id = pick;
      else body.van_ban = text.trim() || null;
    }
    setBusy(true);
    setError("");
    setRevealAnswer(false);
    setWordFlipped(false);
    try {
      const res = await checkAnswer(token, luotId, body);
      setData((d) => ({
        ...d,
        nang_luong: res.nang_luong,
        kn: res.kn,
        xong: res.ket_thuc,
        cau_hoi: d.cau_hoi.map((i) =>
          i.thu_tu === current.thu_tu
            ? { ...i, tra_loi: { phuong_an_chon_id: body.phuong_an_chon_id, van_ban: body.van_ban }, ket_qua: res.ket_qua }
            : i
        ),
      }));
      window.dispatchEvent(new Event("xianglingo:stats"));

      if (skip) {
        setPick(null);
        setText("");
        setShown(null);
        setChatOpen(false);
        if (res.ket_thuc) await load();
        return;
      }
      setShown(current.thu_tu);
    } catch (err) {
      setError(err?.message || "Chưa kiểm tra được, hãy thử lại");
    } finally {
      setBusy(false);
    }
  }

  async function next() {
    setPick(null);
    setText("");
    setShown(null);
    setRevealAnswer(false);
    setWordFlipped(false);
    setChatOpen(false);
    if (data.xong) {
      setBusy(true);
      try {
        await load();
      } finally {
        setBusy(false);
      }
    }
  }

  async function handleOpenHint() {
    if (!current || busy || !current.cho_phep_goi_y || (current.muc_goi_y || 0) >= 2) return;
    setBusy(true);
    setError("");
    try {
      const res = await openLessonHint(token, luotId, current.cau_hoi.id);
      setData((d) => ({
        ...d,
        cau_hoi: d.cau_hoi.map((i) =>
          i.thu_tu === current.thu_tu ? { ...i, muc_goi_y: res.muc_goi_y, goi_y_da_mo: res.goi_y_da_mo } : i
        ),
      }));
    } catch (err) {
      setError(err?.message || "Chưa mở được gợi ý");
    } finally {
      setBusy(false);
    }
  }

  async function restart() {
    setBusy(true);
    setError("");
    try {
      if (data.trang_thai === "dang_lam") await abandonAttempt(token, luotId);
      const res = await startLesson(token, data.bai.ma_goc_id);
      setExitOpen(false);
      navigate(`/on-luyen/bai/${res.luot_id}`, { replace: true });
    } catch (err) {
      const msg = err?.message || "Không mở lại được bài";
      setError(msg);
      setExitOpen(false);
      if (/năng lượng/i.test(msg)) setEnergyOpen(true);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (!current || exitOpen || energyOpen || ["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      if (e.key === "Enter") {
        e.preventDefault();
        if (shown != null) next();
        else if (pick != null) submit(false);
        return;
      }
      const n = Number(e.key);
      if (shown == null && n >= 1 && n <= current.phuong_an.length && CHOICE.includes(current.cau_hoi.dang)) {
        setPick(current.phuong_an[n - 1].id);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const shell = (body, footer) => (
    <div className="xg xc sl" data-theme={theme}>
      <div className="sl-wrap">
        <header className="sl-top">
          <button
            type="button"
            className="sl-x"
            aria-label="Thoát bài"
            onClick={() => (data?.trang_thai === "dang_lam" ? setExitOpen(true) : navigate(mapUrl))}
          >
            <Icon name="x" />
          </button>
          <span
            className="sl-progress"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={items.length || 1}
            aria-valuenow={doneCount}
            aria-label="Tiến độ bài"
          >
            <i style={{ width: `${items.length ? (100 * doneCount) / items.length : 0}%` }} />
          </span>
          {data && (
            <span className="sl-tag">
              {SKILL[data.bai.ky_nang]} · {data.bai.ten_cap_do}
            </span>
          )}
          {data && (
            <button
              type="button"
              className="sp-stat sp-stat--energy"
              onClick={() => setEnergyOpen(true)}
              style={{ cursor: "pointer", font: "inherit" }}
              title="Bấm để mở Nhiệm vụ hồi năng lượng"
            >
              <Icon name="sprout" size={18} />
              <b>
                {data.nang_luong}/{data.nang_luong_toi_da}
              </b>
            </button>
          )}
        </header>
        <main className="sl-main">{body}</main>
      </div>
      {footer}
      {energyOpen && (
        <div
          className="xt-dialog sl-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="sl-energy"
          onClick={(e) => e.target === e.currentTarget && setEnergyOpen(false)}
        >
          <div className="xt-dialog__box" style={{ maxWidth: "540px", width: "100%" }}>
            <h2 id="sl-energy">
              Năng lượng hiện tại: {data?.nang_luong ?? 0}/{data?.nang_luong_toi_da ?? 5}
            </h2>
            <DailyMissions
              compact
              onNavigate={() => setEnergyOpen(false)}
              onClaimed={(res) => setData((d) => (d ? { ...d, nang_luong: res.nang_luong } : d))}
            />
            <div className="sl-dialog__acts" style={{ marginTop: "12px" }}>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => setEnergyOpen(false)}>
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
      {exitOpen && (
        <div className="xt-dialog sl-dialog" role="dialog" aria-modal="true" aria-labelledby="sl-exit">
          <div className="xt-dialog__box">
            <h2 id="sl-exit">Rời bài?</h2>
            <p>
              Câu đã kiểm tra được giữ lại; lần sau bấm ô này sẽ làm tiếp đúng bộ câu. Bỏ lượt thì tạo lượt mới, không hoàn năng lượng đã trừ.
            </p>
            <div className="sl-dialog__acts">
              <button type="button" className="xc-btn xc-btn--sm" onClick={() => setExitOpen(false)}>
                Làm tiếp
              </button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" onClick={() => navigate(mapUrl)}>
                Thoát, giữ bài
              </button>
              <button type="button" className="xc-btn xc-btn--plain xc-btn--sm" disabled={busy} onClick={restart}>
                Bỏ lượt và làm lại
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (error && !data) return shell(<p role="alert">{error}</p>);
  if (!data) return shell(<p className="xc-muted">Đang tải bài...</p>);

  const meta = `${data.bai.loai === "cuoi_thua" ? "Kiểm tra cuối thửa" : `Bài ${data.bai.vi_tri}`} · ${data.bai.ten}`;

  if (data.trang_thai === "da_nop" && data.ket_qua) {
    const r = data.ket_qua;
    return shell(
      <div className={`sl-done${r.dat ? " is-pass" : ""}`}>
        <span className="sl-seal hz" aria-hidden="true">
          {r.dat ? "好" : "再"}
        </span>
        <p className="sl-meta">
          {data.bai.thua} · {meta}
        </p>
        <h1>{r.dat ? "Đạt rồi!" : "Chưa đạt"}</h1>
        <p className="sl-score">
          <b>
            {r.so_dung}/{r.tong}
          </b>{" "}
          câu đúng · cần đúng {r.tong}/{r.tong}
        </p>
        {r.dat && data.muc_dich !== "on_lai" && (
          <p className="sl-gain">
            {r.kn_nhan ? `+${r.kn_nhan} KN` : "Bài này đã nhận KN trước đó"}
            {r.nang_luong_thuong ? ` · +${r.nang_luong_thuong} 🌱 Năng lượng` : ""} ·{" "}
            {data.bai.loai === "cuoi_thua" ? "Đã thu hoạch thửa, mở thửa kế" : "Đã mở ô kế"}
          </p>
        )}
        {data.muc_dich === "on_lai" && <p className="sl-gain">Ôn lại: không tốn năng lượng, không cộng KN.</p>}
        {r.cau_can_on.length > 0 && (
          <div className="sl-review">
            <b>Câu cần ôn (đã lưu vào Sổ tay)</b>
            <ul>
              {r.cau_can_on.map((c) => (
                <li key={c.thu_tu}>
                  <span>Câu {c.thu_tu}</span> {c.noi_dung}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="sl-done__acts">
          {r.dat ? (
            <button type="button" className="xc-btn" onClick={() => navigate(mapUrl)}>
              Về bản đồ <Icon name="arrow" />
            </button>
          ) : (
            <>
              <button type="button" className="xc-btn xc-btn--plain" onClick={() => navigate(mapUrl)}>
                Để sau
              </button>
              <button type="button" className="xc-btn" disabled={busy} onClick={restart}>
                Làm lại bài
              </button>
            </>
          )}
        </div>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  }

  if (!current) return shell(<p className="xc-muted">Đang tổng kết...</p>);

  const q = current.cau_hoi;
  const fb = shown != null ? current.ket_qua : null;
  const chosen = fb ? current.tra_loi?.phuong_an_chon_id : pick;
  const right = fb?.dap_an_id;
  const allowTutor = data.bai.loai === "bai";
  const canAskXiang = allowTutor && Boolean(fb) && !fb.bo_qua;
  const isOpenWriting = q.dang === "viet_mo" || q.dang === "dich_cau";
  const hasAnswer = CHOICE.includes(q.dang) ? pick != null : Boolean(text.trim());
  const canSpeakStem =
    data.bai.ky_nang !== "nghe" &&
    !q.tep_audio &&
    Boolean(q.noi_dung) &&
    !LATIN.test(q.noi_dung) &&
    !/[（(_]/.test(q.noi_dung) &&
    q.noi_dung.length <= 60;

  // Dữ liệu mặt sau của thẻ từ (CHỈ mở khóa bấm lật sau khi đã bấm Kiểm tra và có kết quả `fb`)
  const flipWord = (() => {
    if (!fb || fb.bo_qua) return null;
    if (fb.tu_vung) return fb.tu_vung;
    if (data.bai.ky_nang !== "tu_vung") return null;
    const rightOpt = right ? current.phuong_an.find((x) => x.id === right) : null;
    if (!rightOpt?.noi_dung && !fb.dap_an_chap_nhan?.length) return null;
    if (q.noi_dung && !LATIN.test(q.noi_dung)) {
      return {
        chu_han: q.noi_dung,
        pinyin: q.pinyin || "",
        nghia: rightOpt ? splitOption(rightOpt.noi_dung).text : fb.dap_an_chap_nhan.join(" / "),
        vd_cau: null,
        vd_nghia: fb.dich_nghia || null,
      };
    }
    const parsed = rightOpt ? splitOption(rightOpt.noi_dung) : { text: fb.dap_an_chap_nhan[0] || "", pinyin: "" };
    return {
      chu_han: parsed.text,
      pinyin: parsed.pinyin || "",
      nghia: q.noi_dung || "",
      vd_cau: null,
      vd_nghia: fb.dich_nghia || null,
    };
  })();

  function playAudioText(zhText, e) {
    if (e) e.stopPropagation();
    if (!zhText) return;
    try {
      new Audio(pronounceUrl(zhText)).play().catch(() => {});
    } catch {
      /* trình duyệt chặn tự phát */
    }
  }

  function handleFlipWordCard() {
    if (!flipWord) return;
    setWordFlipped((v) => !v);
    if (!fb.dung && !revealAnswer) {
      setRevealAnswer(true);
      markLessonSolutionViewed(token, luotId, q.id).catch(() => {});
    }
  }

  const footer = fb ? (
    <footer className={`sl-foot sl-foot--fb ${fb.dung ? "is-ok" : "is-bad"}`} role="status">
      <div className="sl-foot__in">
        <span className="sl-badge" aria-hidden="true">
          {fb.dung ? <Icon name="check" size={30} /> : "!"}
        </span>
        <div className="sl-fb">
          <b>
            {fb.dung ? "Chính xác!" : "Chưa đúng"}
            {isOpenWriting && fb.diem != null ? ` · ${fb.diem}/${fb.diem_toi_da} điểm` : ""}
          </b>
          {fb.dung ? (
            <>
              {fb.nhan_xet && <p>{fb.nhan_xet}</p>}
              {fb.giai_thich && <p>{fb.giai_thich}</p>}
              {fb.loi_nghe && (
                <p>
                  Lời nghe: <span className="hz">{fb.loi_nghe}</span>
                </p>
              )}
              {fb.dich_nghia && <p className="sl-fb__vi">{fb.dich_nghia}</p>}
            </>
          ) : (
            <>
              {(fb.nhan_xet || fb.goi_mo) && <p>{fb.nhan_xet || fb.goi_mo}</p>}
              {!revealAnswer ? (
                <button
                  type="button"
                  className="sl-fb-link"
                  onClick={() => {
                    setRevealAnswer(true);
                    markLessonSolutionViewed(token, luotId, q.id).catch(() => {});
                  }}
                >
                  Xem đáp án & lời giải
                </button>
              ) : (
                <>
                  {right &&
                    (() => {
                      const o = current.phuong_an.find((x) => x.id === right);
                      return (
                        o && (
                          <p>
                            Đáp án đúng: <strong><Option option={o} /></strong>
                          </p>
                        )
                      );
                    })()}
                  {fb.dap_an_chap_nhan?.length > 0 && (
                    <p>
                      Đáp án: <strong className="hz">{fb.dap_an_chap_nhan.join(" / ")}</strong>
                    </p>
                  )}
                  {fb.cau_sua && (
                    <p>
                      Gợi ý câu chuẩn: <strong>{fb.cau_sua}</strong>
                    </p>
                  )}
                  {fb.giai_thich && <p>{fb.giai_thich}</p>}
                  {fb.loi_nghe && (
                    <p>
                      Lời nghe: <span className="hz">{fb.loi_nghe}</span>
                    </p>
                  )}
                  {fb.dich_nghia && <p className="sl-fb__vi">{fb.dich_nghia}</p>}
                </>
              )}
              <p className="sl-fb__vi">
                {fb.nang_luong_tru
                  ? `−1 năng lượng · còn ${data.nang_luong}/${data.nang_luong_toi_da}. `
                  : data.tieu_hao
                  ? "Năng lượng đang 0, không trừ thêm. "
                  : "Ôn lại không trừ năng lượng. "}
                Câu đã lưu vào Sổ tay.
              </p>
            </>
          )}
          <ReportQuestionButton key={q.id} luotId={luotId} cauHoiId={q.id} />
        </div>
        <div className="sl-acts">
          {canAskXiang && (
            <button
              type="button"
              className="xx-open sl-ask"
              aria-pressed={chatOpen}
              onClick={() => setChatOpen((v) => !v)}
            >
              <img src={xiangFace} alt="" /> Hỏi Xiang
            </button>
          )}
          <button type="button" className="xc-btn" onClick={next} disabled={busy} autoFocus>
            Tiếp tục
          </button>
        </div>
      </div>
    </footer>
  ) : (
    <footer className="sl-foot">
      <div className="sl-foot__in">
        {error && <p role="alert">{error}</p>}
        <button type="button" className="xc-btn xc-btn--plain" onClick={() => submit(true)} disabled={busy}>
          Bỏ qua
        </button>
        <button type="button" className="xc-btn" onClick={() => submit(false)} disabled={busy || !hasAnswer}>
          {busy ? "Đang kiểm tra…" : "Kiểm tra"}
        </button>
      </div>
    </footer>
  );

  const isShortWordStem = q.noi_dung && !LATIN.test(q.noi_dung) && q.noi_dung.length <= 4;

  return shell(
    <div className="sl-q">
      <div className="sl-meta-row">
        <p className="sl-meta">
          {meta} · Câu {current.thu_tu}/{items.length}
          {data.muc_dich === "on_lai" ? " · Ôn lại" : q.thu_thach_lam_lai ? " · Làm lại (ẩn Pinyin chống học vẹt)" : ""}
        </p>
        {allowTutor && !fb && current.cho_phep_goi_y && (current.muc_goi_y || 0) < 2 && (
          <button type="button" className="sl-hint-btn" onClick={handleOpenHint} disabled={busy}>
            <Icon name="spark" size={14} /> {(current.muc_goi_y || 0) === 0 ? "Gợi ý (1/2)" : "Gợi ý (2/2)"}
          </button>
        )}
      </div>

      <h1>{instruction(q, data.bai.ky_nang)}</h1>

      {!fb && q.ngu_canh_lam_lai && (
        <div className="sl-stem__ctx">
          <small>Ngữ cảnh câu thực tế:</small>
          <span className="hz">{q.ngu_canh_lam_lai}</span>
        </div>
      )}

      {current.ngu_lieu && (current.ngu_lieu.noi_dung || current.ngu_lieu.tep_hinh) && (
        <div className="sl-passage">
          {current.ngu_lieu.tep_hinh && <img src={mediaUrl(current.ngu_lieu.tep_hinh)} alt="" />}
          {current.ngu_lieu.noi_dung && <HanziText text={current.ngu_lieu.noi_dung} pinyin={current.ngu_lieu.pinyin} />}
        </div>
      )}

      {(q.tep_audio || current.ngu_lieu?.tep_audio) && (
        <audio className="sl-audio" controls src={mediaUrl(q.tep_audio || current.ngu_lieu.tep_audio)} />
      )}

      {((q.noi_dung && !isPieceList(q.noi_dung)) || q.tep_hinh) &&
        (flipWord ? (
          <div className="sl-flip-wrap">
            <div
              className={`sl-flip${wordFlipped ? " is-flipped" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={wordFlipped ? "Lật lại mặt câu hỏi" : "Bấm để lật xem nghĩa và ví dụ của từ"}
              onClick={handleFlipWordCard}
              onKeyDown={(e) => {
                if (e.key === " ") {
                  e.preventDefault();
                  handleFlipWordCard();
                }
              }}
            >
              <div className="sl-flip__face sl-flip__front">
                {canSpeakStem && (
                  <button
                    type="button"
                    className="sl-stem__speak"
                    onClick={(e) => playAudioText(q.noi_dung, e)}
                    aria-label="Nghe phát âm"
                    title="Nghe phát âm"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 9v6h4l5 4V5L8 9H4z" />
                      <path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11" />
                    </svg>
                  </button>
                )}
                {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
                {q.noi_dung &&
                  !isPieceList(q.noi_dung) &&
                  (LATIN.test(q.noi_dung) ? <p>{q.noi_dung}</p> : <HanziText text={q.noi_dung} pinyin={q.pinyin} />)}
                <span className="sl-flip__badge">↻ Bấm vào thẻ để lật xem đáp án từ</span>
              </div>

              <div className="sl-flip__face sl-flip__back">
                {flipWord.chu_han && (
                  <button
                    type="button"
                    className="sl-stem__speak"
                    onClick={(e) => playAudioText(flipWord.chu_han, e)}
                    aria-label={`Nghe ${flipWord.chu_han}`}
                    title="Nghe phát âm"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 9v6h4l5 4V5L8 9H4z" />
                      <path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11" />
                    </svg>
                  </button>
                )}
                <b className="hz">{flipWord.chu_han}</b>
                {flipWord.pinyin && <em>{flipWord.pinyin}</em>}
                <span className="sl-flip__mean">{flipWord.nghia}</span>
                {(flipWord.vd_cau || flipWord.vd_nghia) && (
                  <div className="sl-flip__ex">
                    {flipWord.vd_cau && <span className="sl-flip__ex-zh">{flipWord.vd_cau}</span>}
                    {flipWord.vd_nghia && <span className="sl-flip__ex-vi">{flipWord.vd_nghia}</span>}
                  </div>
                )}
                <span className="sl-flip__badge">↻ Bấm để lật lại</span>
              </div>
            </div>
          </div>
        ) : (
          <div className={`sl-stem${isShortWordStem ? " sl-stem--word" : ""}`}>
            {canSpeakStem && (
              <button
                type="button"
                className="sl-stem__speak"
                onClick={(e) => playAudioText(q.noi_dung, e)}
                aria-label="Nghe phát âm"
                title="Nghe phát âm"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 9v6h4l5 4V5L8 9H4z" />
                  <path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11" />
                </svg>
              </button>
            )}
            {q.tep_hinh && <img src={mediaUrl(q.tep_hinh)} alt={q.mo_ta_hinh || ""} />}
            {q.noi_dung &&
              !isPieceList(q.noi_dung) &&
              (LATIN.test(q.noi_dung) ? <p>{q.noi_dung}</p> : <HanziText text={q.noi_dung} pinyin={q.pinyin} />)}
            {q.tu_bat_buoc && (
              <p style={{ width: "100%", fontSize: "16px", marginTop: "4px" }}>
                Từ bắt buộc: <span className="hz" style={{ color: "var(--coral-ink)", fontSize: "20px" }}>{q.tu_bat_buoc}</span>
              </p>
            )}
          </div>
        ))}

      {CHOICE.includes(q.dang) ? (
        <div className={`sl-opts${current.phuong_an.some((o) => o.tep_hinh) ? " sl-opts--img" : ""}`} role="radiogroup" aria-label="Phương án">
          {current.phuong_an.map((o, i) => {
            let cls = "";
            if (fb) {
              if (fb.dung || revealAnswer) cls = o.id === right ? " is-right" : o.id === chosen ? " is-wrong" : " is-dim";
              else cls = o.id === chosen ? " is-wrong" : "";
            } else if (o.id === pick) {
              cls = " is-picked";
            }
            return (
              <button
                key={o.id}
                type="button"
                role="radio"
                aria-checked={o.id === chosen}
                className={`sl-opt${cls}`}
                disabled={Boolean(fb) || busy}
                onClick={() => setPick(o.id)}
              >
                <kbd>{i + 1}</kbd>
                <Option option={o} />
              </button>
            );
          })}
        </div>
      ) : q.dang === "sap_xep" && current.phuong_an?.length ? (
        <SentenceBuilder
          key={q.id}
          pieces={current.phuong_an}
          extra={pickDistractors(items, current)}
          prompt={q.nghia_cau}
          value={text}
          onChange={setText}
          disabled={Boolean(fb) || busy}
          answered={fb ? current.tra_loi?.van_ban || "" : null}
        />
      ) : isOpenWriting ? (
        <textarea
          className="sl-textarea"
          placeholder="Nhập câu trả lời tiếng Trung của bạn…"
          value={fb ? current.tra_loi?.van_ban || "" : text}
          disabled={Boolean(fb) || busy}
          maxLength={500}
          aria-label="Câu trả lời"
          onChange={(e) => setText(e.target.value)}
        />
      ) : (
        <input
          className="sl-input hz"
          placeholder="Nhập đáp án chữ Hán…"
          value={fb ? current.tra_loi?.van_ban || "" : text}
          disabled={Boolean(fb) || busy}
          maxLength={200}
          aria-label="Câu trả lời"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && text.trim() && submit(false)}
        />
      )}

      {current.goi_y_da_mo?.length > 0 && !fb && (
        <div className="sl-hints" role="region" aria-label="Gợi ý">
          {current.goi_y_da_mo.map((hint, idx) => (
            <div key={idx} className="sl-hint-box">
              <b>Gợi ý {idx + 1}:</b>
              {hint}
            </div>
          ))}
        </div>
      )}

      {canAskXiang && chatOpen && (
        <XiangChat
          key={q.id}
          luotId={Number(luotId)}
          cauHoiId={q.id}
          isCorrect={fb.dung}
          defaultOpen
          onClose={() => setChatOpen(false)}
        />
      )}
    </div>,
    footer
  );
}
