import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../features/auth/context/AuthContext.jsx";
import { getPlacementGate } from "../features/placement/api/placementApi.js";
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
  const [gate, setGate] = useState(null);
  const [tick, setTick] = useState(0);

  // Đặt lại ngay thống kê & cổng kiểm tra khi đổi tài khoản (tránh hiển thị tạm dữ liệu người trước - AT29)
  useEffect(() => {
    setStats(null);
    setGate(null);
  }, [token]);

  // Nhận năng lượng/KN ở trang con -> tải lại số trên thanh trên
  useEffect(() => {
    const refresh = () => setTick((t) => t + 1);
    window.addEventListener("xianglingo:stats", refresh);
    return () => window.removeEventListener("xianglingo:stats", refresh);
  }, []);

  // Kiểm tra bắt buộc đã hoàn thành Đánh giá đầu vào 8 câu + lấy Trình độ HSK, Năng lượng, KN hiện trên đầu trang
  useEffect(() => {
    if (!token) return undefined;
    const controller = new AbortController();
    getPlacementGate(token, controller.signal).then(setGate).catch(() => {});
    getPracticeOverview(token, controller.signal).then(setStats).catch(() => {});
    return () => controller.abort();
  }, [token, location.pathname, tick]);

  // Chưa hoàn tất bài Đánh giá đầu vào 8 câu & AI phân tích -> đưa thẳng tới bước đánh giá trước khi vào học
  if (gate?.tu_dong_chuyen_huong) {
    return <Navigate to={gate.tu_dong_chuyen_huong} replace />;
  }

  return (
    <StaffLayout
      roleLabel="Học viên"
      menu={STUDENT_MENU}
      tabs
      variant="student"
      topExtra={<><DictionaryButton /><StudentStats stats={stats} /></>}
    />
  );
}
