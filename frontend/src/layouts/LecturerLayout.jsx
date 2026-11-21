import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { useAuth } from "../features/auth/context/AuthContext.jsx";
import { getOverview } from "../features/lecturer/api/lecturerApi.js";
import { LECTURER_MENU } from "../shared/navigation/roleMenus.js";
import StaffLayout from "./StaffLayout.jsx";

export default function LecturerLayout() {
  const { token } = useAuth();
  const location = useLocation();
  const [badges, setBadges] = useState({});

  // Số việc chờ trên thanh bên lấy từ dữ liệu thật, cập nhật khi chuyển trang
  useEffect(() => {
    const controller = new AbortController();
    getOverview(token, controller.signal).then((d) => setBadges(d.viec_can_lam)).catch(() => {});
    return () => controller.abort();
  }, [token, location.pathname]);

  return <StaffLayout roleLabel="Giảng viên" menu={LECTURER_MENU} badges={badges} />;
}
