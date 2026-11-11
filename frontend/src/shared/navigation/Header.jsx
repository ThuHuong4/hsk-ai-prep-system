import { Link, NavLink } from "react-router-dom";

import xiangFace from "../../assets/images/xiang/home/xiang_face.webp";
import { useAuth } from "../../features/auth/context/AuthContext.jsx";
import { homePathForRole } from "../../features/auth/utils/roles.js";
import "./siteShell.css";

export default function Header() {
  const { user } = useAuth();
  const home = user ? homePathForRole(user.vai_tro) : null;

  return (
    <header className="xs site-head">
      <div className="wrap">
        <Link className="brand" to="/" aria-label="Xianglingo – Trang chủ">
          <span className="face"><img src={xiangFace} alt="" /></span>
          <span>Xiang<b>lingo</b></span>
        </Link>
        <nav className="mainnav" aria-label="Điều hướng chính">
          <NavLink to="/thi-thu">Thi thử</NavLink>
          <NavLink to="/on-luyen">Ôn luyện</NavLink>
        </nav>
        <div className="head-actions">
          {user ? (
            home && <span className="ha-user"><Link className="btn sm" to={home}>Vào trang của tôi</Link></span>
          ) : (
            <span className="ha-user">
              <Link className="gline hide-sm" to="/dang-nhap">Đăng nhập</Link>
              <Link className="btn sm" to="/dang-ky">Đăng ký</Link>
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
