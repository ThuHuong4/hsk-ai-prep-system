import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";
import { useRequest } from "../../../shared/api/useRequest.js";
import "../../exam_catalog/styles/catalog.css";
import { formatDateTime } from "../../lecturer/utils/labels.js";
import { getHistory } from "../api/mockTestApi.js";
import "../styles/examFlags.css";

export default function ExamHistoryPage() {
  const { token } = useAuth();
  const { data, error, loading } = useRequest((signal) => getHistory(token, signal), [token]);
  // Lần thứ mấy của cùng một đề (theo đề gốc, xếp theo thời điểm bắt đầu)
  const attemptNo = {};
  if (data) {
    const byExam = {};
    [...data].sort((a, b) => new Date(a.bat_dau_luc) - new Date(b.bat_dau_luc)).forEach((a) => {
      byExam[a.ma_goc_id] = (byExam[a.ma_goc_id] || 0) + 1;
      attemptNo[a.id] = byExam[a.ma_goc_id];
    });
  }
  return (
    <section className="xc">
      <div className="sh-pghead">
        <header className="xc-head">
          <h1>Lịch sử thi thử</h1>
          <p>Mở lại để xem nguyên đề đã làm, câu đã chọn và đáp án đúng/sai. Điểm lần đầu phản ánh sát năng lực nhất; lần làm lại có thể cao hơn do đã quen đề.</p>
        </header>
        <Link className="xc-btn xc-btn--sm" to="/hoc-vien/thi-thu">Làm đề mới</Link>
      </div>
      {error && <p role="alert">{error}</p>}
      {loading && <p className="xc-muted">Đang tải...</p>}
      {data?.length === 0 && (
        <div className="xc-empty">
          <p>Bạn chưa nộp bài thi thử nào.</p>
          <Link className="xc-btn xc-btn--sm" to="/hoc-vien/thi-thu">Chọn đề thi thử</Link>
        </div>
      )}
      {data?.length > 0 && (
        <ul className="xc-list sh-hlist">
          {data.map((a) => (
            <li key={a.id} className="xc-exam">
              <span className="xc-tag">{a.ten_cap_do}</span>
              <span className="xc-exam__body">
                <span className="xc-exam__name">{a.ten}</span>
                <span className="xc-meta">
                  <span className={`xh-try${attemptNo[a.id] === 1 ? " is-first" : ""}`}>
                    {attemptNo[a.id] === 1 ? "Lần đầu" : `Lần ${attemptNo[a.id]} · làm lại`}
                  </span>
                  <span>{a.ma_de}</span>
                  <span>{a.nop_luc ? `Nộp ${formatDateTime(a.nop_luc)}` : `Bắt đầu ${formatDateTime(a.bat_dau_luc)}`}</span>
                </span>
              </span>
              {a.trang_thai === "da_nop" ? (
                <>
                  <span className={`sh-score${a.diem.dat ? " is-pass" : ""}`}>{a.diem.tong_diem.toFixed(0)}<small>/{a.diem.diem_toi_da}</small></span>
                  <Link className="xc-btn xc-btn--plain xc-btn--sm" to={`/thi-thu/ket-qua/${a.id}`}>Xem lại</Link>
                </>
              ) : (
                <Link className="xc-btn xc-btn--coral xc-btn--sm" to={`/thi-thu/lam-bai/${a.id}`}>Làm tiếp · {Math.ceil(a.con_lai_giay / 60)}′</Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
