import { Link } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";

export default function StudentHomePage() {
  const { user } = useAuth();

  return (
    <section>
      <h1>Xin chào, {user?.ho_ten}</h1>
      {/* Chưa có bài đánh giá đầu vào nên trạng thái luôn là chưa đánh giá */}
      <p><span className="badge">Chưa đánh giá trình độ</span></p>
      <ul className="card-grid">
        <li>
          <Link className="card" to="/hoc-vien/thi-thu">
            <span className="card__title">Thi thử</span>
            <span className="muted">Làm đề HSK 1–4 có đếm giờ như thi thật.</span>
          </Link>
        </li>
        <li>
          <Link className="card" to="/hoc-vien/on-luyen">
            <span className="card__title">Ôn luyện</span>
            <span className="muted">Chọn cấp HSK, sau đó luyện Nghe, Đọc, Từ vựng hoặc Viết.</span>
          </Link>
        </li>
      </ul>
    </section>
  );
}