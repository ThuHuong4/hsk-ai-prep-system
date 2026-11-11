import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/context/AuthContext.jsx";

const ITEMS = [
  { to: "lich-su", label: "Lịch sử làm bài", description: "Các lần Thi thử và Ôn luyện đã làm." },
  { to: "tien-bo", label: "Tiến bộ học tập", description: "Điểm mạnh, điểm yếu và thay đổi theo thời gian." },
  { to: "ho-so", label: "Hồ sơ", description: "Họ tên và thông tin tài khoản." },
  { to: "khao-sat", label: "Khảo sát định hướng", description: "Nhu cầu, mục tiêu và thời gian học." },
  { to: "nhac-hoc", label: "Nhắc học", description: "Lịch nhắc học qua email." },
  { to: "google", label: "Tài khoản Google", description: "Đăng nhập bằng Google." },
];

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <section>
      <h1>Cá nhân</h1>
      <p className="muted">{user?.ho_ten} · {user?.email}</p>
      <ul className="card-grid">
        {ITEMS.map((item) => (
          <li key={item.to}>
            <Link className="card" to={`/hoc-vien/ca-nhan/${item.to}`}>
              <span className="card__title">{item.label}</span>
              <span className="muted">{item.description}</span>
            </Link>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => {
          logout();
          navigate("/dang-nhap", { replace: true });
        }}
      >
        Đăng xuất
      </button>
    </section>
  );
}