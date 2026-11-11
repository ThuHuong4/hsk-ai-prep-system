import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/context/AuthContext.jsx";
import "./roleLayout.css";

// variant="tabs": điện thoại hiện thanh tab ở đáy (Học viên); "sidebar": nút Menu (Giảng viên, Admin)
export default function RoleLayout({ roleLabel, menu, variant = "sidebar" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const isTabs = variant === "tabs";

  function handleLogout() {
    logout();
    navigate("/dang-nhap", { replace: true });
  }

  return (
    <div className={`role-layout${isTabs ? " role-layout--tabs" : ""}`}>
      <header className="role-layout__header">
        {!isTabs && (
          <button
            type="button"
            className="role-layout__menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="role-layout-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? "Đóng menu" : "Menu"}
          </button>
        )}
        <Link to="/" className="role-layout__brand">HSK AI</Link>
        <span className="role-layout__user">
          <span className="badge">{roleLabel}</span> {user?.ho_ten}
        </span>
        <button type="button" onClick={handleLogout}>Đăng xuất</button>
      </header>

      <div className="role-layout__body">
        <nav
          id="role-layout-nav"
          className={`role-layout__nav${menuOpen ? " is-open" : ""}`}
          aria-label={`Menu ${roleLabel}`}
        >
          <ul>
            {menu.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  onClick={() => setMenuOpen(false)}
                  className={({ isActive }) => (isActive ? "is-active" : undefined)}
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="role-layout__main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}