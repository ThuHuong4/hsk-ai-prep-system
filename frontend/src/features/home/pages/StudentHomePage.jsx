import { Link, Navigate } from "react-router-dom";

import xiangFull from "../../../assets/images/xiang/home/xiang_full.webp";
import { useRequest } from "../../../shared/api/useRequest.js";
import Icon from "../../../shared/components/Icon.jsx";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import "../../exam_catalog/styles/catalog.css";
import { getHistory } from "../../mock_test/api/mockTestApi.js";
import DailyMissions from "../../notebook/components/DailyMissions.jsx";
import { getSurvey } from "../../survey/api/surveyApi.js";

const firstName = (name) => (name || "").trim().split(/\s+/).pop() || "bạn";

// Lời chào theo dữ liệu thật: đang làm dở → làm tiếp; đã nộp → điểm gần nhất; chưa có → bắt đầu
function greeting(history, name) {
  const open = history?.find((a) => a.trang_thai === "dang_lam");
  if (open) {
    return { eyebrow: `Đang làm · ${open.ma_de}`, title: `Chào ${name}, làm tiếp nhé!`, text: open.ten,
      action: { to: `/thi-thu/lam-bai/${open.id}`, label: "Làm tiếp" } };
  }
  const last = history?.find((a) => a.trang_thai === "da_nop");
  if (last) {
    return { eyebrow: `Lần thi gần nhất · ${last.diem.tong_diem.toFixed(0)}/${last.diem.diem_toi_da}`, title: `Chào ${name}, luyện tiếp nhé!`,
      text: last.ten, action: { to: "/hoc-vien/thi-thu", label: "Làm đề mới" } };
  }
  return { eyebrow: "Bắt đầu", title: `Chào ${name}, bắt đầu nhé!`, text: "Học theo từng thửa ở Ôn luyện hoặc làm một đề Thi thử tính giờ.",
    action: { to: "/hoc-vien/thi-thu", label: "Chọn đề thi thử" } };
}

export default function StudentHomePage() {
  const { user, token } = useAuth();
  const { data: history, error } = useRequest((signal) => getHistory(token, signal), [token]);
  const { data: survey } = useRequest((signal) => getSurvey(token, signal), [token]);
  const g = greeting(history, firstName(user?.ho_ten));
  const done = (history ?? []).filter((a) => a.trang_thai === "da_nop");

  // Lần đầu vào (chưa làm, chưa bỏ qua khảo sát) → khảo sát 5 câu
  if (survey?.trang_thai === "chua_lam") return <Navigate to="/khao-sat" replace />;

  return (
    <section className="xc sh">
      <div className="sh-dash">
        <div className="sh-col">
          <div className="sh-scene sh-welcome">
            <span className="sh-bghz" aria-hidden="true">加油</span>
            <img className="sh-xiang" src={xiangFull} alt="" />
            <span className="sh-eyebrow">{g.eyebrow}</span>
            <h1>{g.title}</h1>
            <p>{g.text}</p>
            <Link className="xc-btn xc-btn--coral" to={g.action.to}>{g.action.label}<Icon name="arrow" /></Link>
          </div>
          <div className="sh-duo">
            <Link className="sh-tile sh-tile--practice" to="/hoc-vien/on-luyen">
              <span className="sh-ti"><Icon name="route" size={26} /></span>
              <h2>Ôn luyện</h2>
              <p>Chọn Nghe, Đọc, Từ vựng hoặc Viết, học theo từng thửa.</p>
              <span className="sh-go">Chọn kỹ năng <Icon name="arrow" /></span>
            </Link>
            <Link className="sh-tile sh-tile--exam" to="/hoc-vien/thi-thu">
              <span className="sh-ti"><Icon name="timer" size={26} /></span>
              <h2>Thi thử</h2>
              <p>Chọn đề HSK bất kỳ, tính giờ như phòng thi.</p>
              <span className="sh-go">Chọn đề <Icon name="arrow" /></span>
            </Link>
          </div>
        </div>
        <div className="sh-col">
          <DailyMissions />
          <div className="sh-panel">
            <div className="sh-panel__head"><Icon name="timer" /><h2>Lịch sử thi gần đây</h2></div>
            {error && <p className="xc-muted">Không tải được lịch sử thi.</p>}
            {history && done.length === 0 && <p className="xc-muted">Bạn chưa nộp bài thi thử nào.</p>}
            {done.length > 0 && (
              <ul className="sh-hist">
                {done.slice(0, 3).map((a) => (
                  <li key={a.id}>
                    <Link to={`/thi-thu/ket-qua/${a.id}`}>
                      <span><b>{a.ten}</b><small>{a.ten_cap_do} · {a.ma_de}</small></span>
                      <span className={`sh-score${a.diem.dat ? " is-pass" : ""}`}>{a.diem.tong_diem.toFixed(0)}<small>/{a.diem.diem_toi_da}</small></span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <Link className="sh-link" to="/hoc-vien/lich-su-thi">Xem lịch sử thi</Link>
          </div>
          <div className="sh-panel">
            <div className="sh-panel__head sh-panel__head--bad"><Icon name="book" /><h2>Ôn câu sai</h2></div>
            <p>Câu làm sai hoặc bỏ trống ở Ôn luyện được tự lưu vào Sổ tay. Ôn Sổ tay không tốn năng lượng.</p>
            <Link className="sh-link" to="/hoc-vien/so-tay-cau-sai">Mở Sổ tay</Link>
          </div>
        </div>
      </div>
    </section>
  );
}
