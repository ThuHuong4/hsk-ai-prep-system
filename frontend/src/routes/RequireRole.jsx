import { Link, Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../features/auth/context/AuthContext.jsx";
import { homePathForRole } from "../features/auth/utils/roles.js";

export default function RequireRole({ allowed, children }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    // Ghi nhớ trang đang muốn vào để quay lại sau khi đăng nhập
    return <Navigate to="/dang-nhap" replace state={{ from: location.pathname + location.search }} />;
  }

  if (!allowed.includes(user.vai_tro)) {
    const home = homePathForRole(user.vai_tro);
    return (
      <div>
        <h1>Không có quyền truy cập</h1>
        <p>Tài khoản của bạn không được phép xem trang này.</p>
        {home && <Link to={home}>Về trang của bạn</Link>}
      </div>
    );
  }

  return children;
}