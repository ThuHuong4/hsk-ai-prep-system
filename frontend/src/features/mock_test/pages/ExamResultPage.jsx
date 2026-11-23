import { useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import { mediaUrl } from "../../../shared/utils/format.js";
import { getResult, startAttempt } from "../api/mockTestApi.js";
import ExamPaper from "../components/ExamPaper.jsx";
import ExamShell from "../components/ExamShell.jsx";
import QuestionNav from "../components/QuestionNav.jsx";
import { buildPaper } from "../utils/paper.js";
import RoadmapCard from "../components/RoadmapCard.jsx";
const SKILL = { nghe: "Nghe 听力", doc: "Đọc 阅读", viet: "Viết 书写", tu_vung: "Từ vựng" };

export default function ExamResultPage() {
  const { luotId } = useParams();
  const { token } = useAuth();
  const navigate = useNavigate();
  const { data, error, loading } = useRequest((signal) => getResult(token, luotId, signal), [token, luotId]);
  const sections = useMemo(() => (data ? buildPaper(data.cau_hoi) : []), [data]);

  async function retry() {
    try {
      const res = await startAttempt(token, data.de.ma_goc_id);
      navigate(`/thi-thu/lam-bai/${res.luot_id}`);
    } catch { /* lỗi hiển thị qua trang đề */ }
  }

  if (loading) return <ExamShell title="Kết quả"><p className="lv-muted">Đang tải…</p></ExamShell>;
  if (error) return <ExamShell title="Kết quả"><p role="alert" className="lv-alert">{error}</p></ExamShell>;

  const d = data.diem;
  const wrong = data.cau_hoi.filter((i) => i.ket_qua && i.ket_qua.dung === false).length;
  return (
    <ExamShell title={`Kết quả · ${data.de.ten}`}>
      <div className="xt-layout">
        <main className="xt-main">
          <div className={`xt-score${d.dat ? " is-pass" : ""}`}>
            <div className="xt-score__total">
              <span className="xt-score__num">{d.tong_diem.toFixed(2)}</span>
              <span>/ {d.diem_toi_da}</span>
            </div>
            <div className="xt-score__info">
              <span className={`lv-status lv-status--${d.so_cau_cho_cham ? "nhap" : d.dat ? "da_dang" : "moi"}`}>
                {d.so_cau_cho_cham ? `Còn ${d.so_cau_cho_cham} câu chờ chấm` : d.dat ? "Đạt" : "Chưa đạt"}
              </span>
              <span>Mốc đạt {d.diem_dat}/{d.diem_toi_da}{data.ly_do_nop === "het_gio" && " · Tự nộp khi hết giờ"}</span>
              <div className="xt-skills">
                {d.ky_nang.map((s) => (
                  <div key={s.ky_nang} className="xt-skill">
                    <span>{SKILL[s.ky_nang]}</span>
                    <span className="xt-skill__bar" aria-hidden="true"><span style={{ width: `${s.diem}%` }} /></span>
                    <strong>{s.diem.toFixed(2)}</strong>
                    <span className="xt-skill__sub">{s.dung}/{s.so_cau} câu đúng</span>
                  </div>
                ))}
              </div>
              <p className="lv-help">Điểm thi thử của Xianglingo, không phải điểm HSK chính thức.{wrong > 0 && ` ${wrong} câu sai/bỏ trống, xem lại bên dưới hoặc trong Lịch sử thi.`}</p>
              <div className="lv-actions">
                <button type="button" className="xbtn" onClick={retry}>Làm lại đề</button>
                <Link className="xbtn xbtn--ghost" to={`/hoc-vien/thi-thu/hsk/${data.de.cap_do_id}`}>Đề khác</Link>
                <Link className="xbtn xbtn--ghost" to="/hoc-vien/lich-su-thi">Lịch sử</Link>
              </div>
            </div>
          </div>
          <RoadmapCard luotId={luotId} />
          <ExamPaper sections={sections} passages={data.ngu_lieu} mode="review" luotId={Number(luotId)} onPick={() => {}} onText={() => {}}
            disabled audioUrl={mediaUrl(data.de.tep_audio_chung)} />
        </main>
        <aside className="xt-side">
          <div className="xt-side__card">
            <p className="xt-side__stat">Xem lại từng câu</p>
            <QuestionNav items={data.cau_hoi} mode="review" />
            <p className="lv-help"><span className="xt-dot is-ok" /> đúng <span className="xt-dot is-bad" /> sai/bỏ trống</p>
          </div>
        </aside>
      </div>
    </ExamShell>
  );
}
