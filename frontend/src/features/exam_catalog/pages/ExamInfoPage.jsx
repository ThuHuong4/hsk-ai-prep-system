import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { useRequest } from "../../../shared/api/useRequest.js";
import { useAuth } from "../../auth/context/AuthContext.jsx";
import { ROLE } from "../../auth/utils/roles.js";
import { getExam } from "../api/getExam.js";

export default function ExamInfoPage({ basePath }) {
  const { maBoDe } = useParams();
  const examId = /^\d+$/.test(maBoDe ?? "") && Number(maBoDe) >= 1 ? Number(maBoDe) : null;
  const { data: exam, error, loading } = useRequest(
    examId ? (signal) => getExam(examId, signal) : null,
    [examId]
  );
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notice, setNotice] = useState("");

  function handleStart() {
    if (!user) {
      // Ghi nhớ đúng đề đang xem để quay lại sau khi đăng nhập
      navigate("/dang-nhap", { state: { from: location.pathname } });
      return;
    }
    if (user.vai_tro !== ROLE.HOC_VIEN) {
      setNotice("Chỉ tài khoản Học viên được làm bài thi thử.");
      return;
    }
    setNotice("Chức năng làm bài thi đang phát triển.");
  }

  return (
    <section>
      <Link className="back-link" to={exam ? `${basePath}/hsk/${exam.ma_cap_do}` : basePath}>
        ← Danh sách đề
      </Link>
      {!examId && <p role="alert">Mã đề không hợp lệ.</p>}
      {loading && <p className="muted">Đang tải...</p>}
      {error && <p role="alert">{error}</p>}
      {exam && (
        <>
          <h1>{exam.ten_bo_de}</h1>
          <ul>
            <li>Cấp độ: HSK {exam.ma_cap_do}</li>
            <li>Thời gian làm bài: {Math.round(exam.thoi_gian_giay / 60)} phút</li>
          </ul>
          <p className="muted">
            Bài thi có đếm giờ. Đáp án, giải thích và hỗ trợ AI chỉ hiện sau khi nộp bài.
          </p>
          <button type="button" className="button--primary" onClick={handleStart}>
            Bắt đầu làm bài
          </button>
          {notice && <p role="status" className="muted">{notice}</p>}
        </>
      )}
    </section>
  );
}