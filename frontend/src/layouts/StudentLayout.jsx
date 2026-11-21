import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

import { useAuth } from "../features/auth/context/AuthContext.jsx";
import { getPracticeOverview } from "../features/practice/api/practiceApi.js";
import StudentStats from "../features/practice/components/StudentStats.jsx";
import DictionaryButton from "../features/search/components/DictionaryButton.jsx";
import { STUDENT_MENU } from "../shared/navigation/roleMenus.js";
import StaffLayout from "./StaffLayout.jsx";
import "./studentShell.css";

export default function StudentLayout() {
  const { token } = useAuth();
  const location = useLocation();
  const [stats, setStats] = useState(null);
  const [tick, setTick] = useState(0);

  // Nhận năng lượng/KN ở trang con → tải lại số trên thanh trên
  useEffect(() => {
    const refresh = () => setTick((t) => t + 1);
    window.addEventListener("xianglingo:stats", refresh);
    return () => window.removeEventListener("xianglingo:stats", refresh);
  }, []);

  // Năng lượng và KN thật từ máy chủ, cập nhật khi chuyển trang
  useEffect(() => {
    const controller = new AbortController();
    getPracticeOverview(token, controller.signal).then(setStats).catch(() => {});
    return () => controller.abort();
  }, [token, location.pathname, tick]);

  return <StaffLayout roleLabel="Học viên" menu={STUDENT_MENU} tabs variant="student" topExtra={<><DictionaryButton /><StudentStats stats={stats} /></>} />;
}
