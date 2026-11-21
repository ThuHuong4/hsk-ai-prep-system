import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { ROLE } from "../../auth/utils/roles.js";
import Icon from "../../../shared/components/Icon.jsx";
import { getExamInfo, startAttempt } from "../../mock_test/api/mockTestApi.js";
import "../styles/catalog.css";

const SKILL = { nghe: "Nghe", doc: "Đọc", viet: "Viết", tu_vung: "Từ vựng" };

export default function ExamInfoPage({ basePath }) {
  const { maBoDe } = useParams();
  const examId = /^\d+$/.test(maBoDe ?? "") && Number(maBoDe) >= 1 ? Number(maBoDe) : null;
  const { data: exam, error, loading } = useRequest(
    examId ? (signal) => getExamInfo(examId, signal) : null,
    [examId]
  );
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notice, setNotice] = useState("");
  const [starting, setStarting] = useState(false);

  async function handleStart() {
    if (!user) {
      // Ghi nhớ đúng đề đang xem để quay lại sau khi đăng nhập
      navigate("/dang-nhap", { state: { from: location.pathname } });
      return;
    }
    if (user.vai_tro !== ROLE.HOC_VIEN) {
      setNotice("Chỉ tài khoản Học viên được làm bài thi thử.");
      return;
    }
    setStarting(true);
    setNotice("");
    try {
      const res = await startAttempt(token, examId);
      navigate(`/thi-thu/lam-bai/${res.luot_id}`);
    } catch (err) {
      setNotice(err?.message || "Không bắt đầu được bài thi");
      setStarting(false);
    }
  }

  return (
    <section className="xc">
      <Link className="xc-back" to={exam ? `${basePath}/hsk/${exam.cap_do_id}` : basePath}>
        <Icon name="arrowLeft" />Danh sách đề
      </Link>
      {!examId && <p role="alert">Mã đề không hợp lệ.</p>}
      {loading && <p className="xc-muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {exam && (
        <>
          <header className="xc-head">
            <span className="xc-title"><span className="xc-tag">{exam.ten_cap_do}</span><h1>{exam.ten}</h1></span>
            <span className="xc-meta">
              <span><Icon name="book" />{exam.so_cau} câu hỏi</span>
              <span><Icon name="timer" />{exam.thoi_luong_phut} phút</span>
              <span>Đạt từ {exam.diem_dat_thi}/{exam.diem_toi_da_thi} điểm</span>
              <span>Mã đề {exam.ma_de}</span>
            </span>
          </header>
          <div className="xc-detail">
            <ol className="xc-parts" aria-label="Cấu trúc đề">
              {exam.cac_phan.map((p, i) => (
                <li key={p.phan}>
                  <span className={`xc-tag xc-tag--${p.ky_nang}`}>{SKILL[p.ky_nang].toUpperCase()}</span>
                  <span>{SKILL[p.ky_nang]} · Phần {i + 1}{p.tu ? ` (câu ${p.tu}${p.den !== p.tu ? `–${p.den}` : ""})` : ""}</span>
                  <span>{p.so_cau} câu</span>
                </li>
              ))}
            </ol>
            <div className="xc-card">
              <h2>Trước khi bắt đầu</h2>
              <ul className="xc-checks">
                <li><Icon name="check" />Tính giờ {exam.thoi_luong_phut} phút, hết giờ tự nộp.</li>
                {exam.tep_audio_chung && <li><Icon name="check" />Phần Nghe dùng một audio chung.</li>}
                <li><Icon name="check" />Mỗi lần chọn được lưu ngay; không hiện đáp án trong lúc làm.</li>
                <li><Icon name="check" />Đáp án, lời nghe và dịch nghĩa mở sau khi nộp.</li>
                {exam.nguon && <li><Icon name="check" />Nguồn đề: {exam.nguon}</li>}
              </ul>
              <button type="button" className="xc-btn xc-btn--block" onClick={handleStart} disabled={starting}>
                {starting ? "Đang mở đề..." : "Bắt đầu thi"}
              </button>
              {notice && <p role="status">{notice}</p>}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
