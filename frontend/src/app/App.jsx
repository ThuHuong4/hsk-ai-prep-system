import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";

import ExamPreviewPage from "../features/admin/exams/pages/ExamPreviewPage.jsx";
import { AuthProvider, useAuth } from "../features/auth/context/AuthContext.jsx";
import ForgotPasswordPage from "../features/auth/pages/ForgotPasswordPage.jsx";
import LoginPage from "../features/auth/pages/LoginPage.jsx";
import RegisterPage from "../features/auth/pages/RegisterPage.jsx";
import ResetPasswordPage from "../features/auth/pages/ResetPasswordPage.jsx";
import VerifyEmailPage from "../features/auth/pages/VerifyEmailPage.jsx";
import { ROLE, homePathForRole } from "../features/auth/utils/roles.js";
import ExamInfoPage from "../features/exam_catalog/pages/ExamInfoPage.jsx";
import ExamListPage from "../features/exam_catalog/pages/ExamListPage.jsx";
import LevelPickerPage from "../features/exam_catalog/pages/LevelPickerPage.jsx";
import PublicHomePage from "../features/home/pages/PublicHomePage.jsx";
import StudentHomePage from "../features/home/pages/StudentHomePage.jsx";
import PracticeSkillPickerPage from "../features/practice/pages/PracticeSkillPickerPage.jsx";
import PracticeSkillStartPage from "../features/practice/pages/PracticeSkillStartPage.jsx";
import ProfilePage from "../features/profile/pages/ProfilePage.jsx";
import AdminLayout from "../layouts/AdminLayout.jsx";
import LecturerLayout from "../layouts/LecturerLayout.jsx";
import PublicLayout from "../layouts/PublicLayout.jsx";
import StudentLayout from "../layouts/StudentLayout.jsx";
import RequireRole from "../routes/RequireRole.jsx";
import UnderDevelopment from "../shared/components/UnderDevelopment.jsx";

const PUBLIC_RETURN_PREFIXES = ["/thi-thu", "/on-luyen"];

// Giữ token trong bộ nhớ rồi xóa khỏi thanh địa chỉ và lịch sử trình duyệt
function useOneTimeTokenFromUrl(pathname) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [token] = useState(() => searchParams.get("token") ?? "");

  useEffect(() => {
    if (searchParams.has("token")) navigate(pathname, { replace: true });
  }, [searchParams, navigate, pathname]);

  return token;
}

function homeOf(user) {
  return homePathForRole(user.vai_tro) ?? "/";
}

// Chỉ quay lại trang nội bộ thuộc khu vực của vai trò đó, hoặc trang công khai (đề, ôn luyện)
function returnPathFor(user, from) {
  const home = homeOf(user);
  if (typeof from !== "string" || !from.startsWith("/") || from.startsWith("//")) return home;
  const isUnder = (prefix) => from === prefix || from.startsWith(`${prefix}/`);
  if ((home !== "/" && isUnder(home)) || PUBLIC_RETURN_PREFIXES.some(isUnder)) return from;
  return home;
}

function LoginRoute() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  if (user) return <Navigate to={returnPathFor(user, location.state?.from)} replace />;
  return (
    <LoginPage
      onLogin={login}
      onGoRegister={() => navigate("/dang-ky")}
      onGoForgotPassword={() => navigate("/quen-mat-khau")}
    />
  );
}

function RegisterRoute() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  if (user) return <Navigate to={homeOf(user)} replace />;

  return (
    <RegisterPage
      onLogin={login}
      onGoLogin={() => navigate("/dang-nhap")}
      onGoForgotPassword={() => navigate("/quen-mat-khau")}
    />
  );
}
function VerifyEmailRoute() {
  const navigate = useNavigate();
  const token = useOneTimeTokenFromUrl("/xac-minh-email");
  return <VerifyEmailPage token={token} onGoLogin={() => navigate("/dang-nhap")} />;
}

function ForgotPasswordRoute() {
  const { user } = useAuth();
  const navigate = useNavigate();
  if (user) return <Navigate to={homeOf(user)} replace />;
  return <ForgotPasswordPage onGoLogin={() => navigate("/dang-nhap")} />;
}

function ResetPasswordRoute() {
  const navigate = useNavigate();
  const token = useOneTimeTokenFromUrl("/dat-lai-mat-khau");
  return (
    <ResetPasswordPage
      token={token}
      onGoLogin={() => navigate("/dang-nhap")}
      onGoForgotPassword={() => navigate("/quen-mat-khau")}
    />
  );
}

// Chọn cấp → đề / kỹ năng: dùng chung cho khách (prefix "") và Học viên (prefix "/hoc-vien")
function catalogRoutes(prefix, guest) {
  const examBase = `${prefix}/thi-thu`;
  const practiceBase = `${prefix}/on-luyen`;
  return (
    <>
      <Route
        path="thi-thu"
        element={<LevelPickerPage title="Thi thử HSK" description="Chọn cấp độ để xem danh sách đề." basePath={examBase} />}
      />
      <Route path="thi-thu/hsk/:maCapDo" element={<ExamListPage basePath={examBase} />} />
      <Route path="thi-thu/de/:maBoDe" element={<ExamInfoPage basePath={examBase} />} />
      <Route
        path="on-luyen"
        element={<LevelPickerPage title="Ôn luyện" description="Chọn cấp độ, sau đó chọn kỹ năng." basePath={practiceBase} />}
      />
      <Route path="on-luyen/hsk/:maCapDo" element={<PracticeSkillPickerPage basePath={practiceBase} />} />
      <Route
        path="on-luyen/hsk/:maCapDo/:kyNang"
        element={<PracticeSkillStartPage basePath={practiceBase} guest={guest} />}
      />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Khu vực công khai: khách và người đã đăng nhập đều xem được */}
          <Route path="/" element={<PublicLayout />}>
            <Route index element={<PublicHomePage />} />
            {catalogRoutes("", true)}
            <Route path="dang-nhap" element={<LoginRoute />} />
            <Route path="dang-ky" element={<RegisterRoute />} />
            <Route path="xac-minh-email" element={<VerifyEmailRoute />} />
            <Route path="quen-mat-khau" element={<ForgotPasswordRoute />} />
            <Route path="dat-lai-mat-khau" element={<ResetPasswordRoute />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>

          {/* Học viên: ôn luyện, thi thử */}
          <Route
            path="/hoc-vien"
            element={
              <RequireRole allowed={[ROLE.HOC_VIEN]}>
                <StudentLayout />
              </RequireRole>
            }
          >
            <Route index element={<StudentHomePage />} />
            {catalogRoutes("/hoc-vien", false)}
            <Route path="so-tay-cau-sai" element={<UnderDevelopment title="Sổ tay câu sai" />} />
            <Route path="ca-nhan" element={<ProfilePage />} />
            <Route path="ca-nhan/lich-su" element={<UnderDevelopment title="Lịch sử làm bài" />} />
            <Route path="ca-nhan/tien-bo" element={<UnderDevelopment title="Tiến bộ học tập" />} />
            <Route path="ca-nhan/ho-so" element={<UnderDevelopment title="Hồ sơ" />} />
            <Route path="ca-nhan/khao-sat" element={<UnderDevelopment title="Khảo sát định hướng" />} />
            <Route path="ca-nhan/nhac-hoc" element={<UnderDevelopment title="Nhắc học" />} />
            <Route path="ca-nhan/google" element={<UnderDevelopment title="Tài khoản Google" />} />
            <Route path="*" element={<Navigate to="/hoc-vien" replace />} />
          </Route>

          {/* Giảng viên: quản lý nội dung, xem đề */}
          <Route
            path="/giang-vien"
            element={
              <RequireRole allowed={[ROLE.GIANG_VIEN]}>
                <LecturerLayout />
              </RequireRole>
            }
          >
            <Route index element={<UnderDevelopment title="Tổng quan" />} />
            <Route path="cau-hoi" element={<UnderDevelopment title="Câu hỏi" />} />
            <Route path="bo-de" element={<ExamPreviewPage />} />
            <Route path="bai-luyen" element={<UnderDevelopment title="Bài luyện" />} />
            <Route path="hoc-lieu" element={<UnderDevelopment title="Học liệu" />} />
            <Route path="cham-viet" element={<UnderDevelopment title="Chấm bài Viết" />} />
            <Route path="bao-loi" element={<UnderDevelopment title="Báo lỗi nội dung" />} />
            <Route path="*" element={<Navigate to="/giang-vien" replace />} />
          </Route>

          {/* Quản trị viên: tài khoản và vai trò */}
          <Route
            path="/quan-tri"
            element={
              <RequireRole allowed={[ROLE.QUAN_TRI_VIEN]}>
                <AdminLayout />
              </RequireRole>
            }
          >
            <Route index element={<UnderDevelopment title="Tổng quan" />} />
            <Route path="tai-khoan" element={<UnderDevelopment title="Tài khoản" />} />
            <Route path="*" element={<Navigate to="/quan-tri" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}