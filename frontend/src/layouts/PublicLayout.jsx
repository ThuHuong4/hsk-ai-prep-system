import { Outlet, useLocation } from "react-router-dom";
import Footer from "../shared/navigation/Footer.jsx";
import Header from "../shared/navigation/Header.jsx";
import "./publicLayout.css";

export default function PublicLayout() {
  const { pathname } = useLocation();
  // Trang chủ hiển thị tràn màn hình; các trang công khai khác giữ khung nội dung cũ
  const mainClass = pathname === "/" ? "public-layout__main public-layout__main--full" : "public-layout__main";

  return (
    <div className="public-layout">
      <Header />
      <main className={mainClass}>
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
