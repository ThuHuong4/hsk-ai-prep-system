import { Suspense, lazy, useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";

import { AuthProvider, useAuth } from "../features/auth/context/AuthContext.jsx";
import LoginPage from "../features/auth/pages/LoginPage.jsx";
import { ROLE, homePathForRole } from "../features/auth/utils/roles.js";
import PublicHomePage from "../features/home/pages/PublicHomePage.jsx";
import StudentHomePage from "../features/home/pages/StudentHomePage.jsx";
import PublicLayout from "../layouts/PublicLayout.jsx";
import StudentLayout from "../layouts/StudentLayout.jsx";
import RequireRole from "../routes/RequireRole.jsx";

// Tải lười (code-splitting) các trang xác thực phụ, phiên làm bài toàn màn hình, Giảng viên và Quản trị viên
const ForgotPasswordPage = lazy(() => import("../features/auth/pages/ForgotPasswordPage.jsx"));
const RegisterPage = lazy(() => import("../features/auth/pages/RegisterPage.jsx"));
const ResetPasswordPage = lazy(() => import("../features/auth/pages/ResetPasswordPage.jsx"));
const VerifyEmailPage = lazy(() => import("../features/auth/pages/VerifyEmailPage.jsx"));

const ExamHistoryPage = lazy(() => import("../features/mock_test/pages/ExamHistoryPage.jsx"));
const ExamResultPage = lazy(() => import("../features/mock_test/pages/ExamResultPage.jsx"));
const ExamSessionPage = lazy(() => import("../features/mock_test/pages/ExamSessionPage.jsx"));
const MockTestLobbyPage = lazy(() => import("../features/mock_test/pages/MockTestLobbyPage.jsx"));

const LessonPage = lazy(() => import("../features/practice/pages/LessonPage.jsx"));
const PracticeHomePage = lazy(() => import("../features/practice/pages/PracticeHomePage.jsx"));
const PracticeMapPage = lazy(() => import("../features/practice/pages/PracticeMapPage.jsx"));
const SkipTestPage = lazy(() => import("../features/practice/pages/SkipTestPage.jsx"));

const NotebookPage = lazy(() => import("../features/notebook/pages/NotebookPage.jsx"));
const NotebookReviewPage = lazy(() => import("../features/notebook/pages/NotebookReviewPage.jsx"));
const PlacementResultPage = lazy(() => import("../features/placement/pages/PlacementResultPage.jsx"));
const PlacementTestPage = lazy(() => import("../features/placement/pages/PlacementTestPage.jsx"));
const ProfilePage = lazy(() => import("../features/profile/pages/ProfilePage.jsx"));
const StatisticsPage = lazy(() => import("../features/statistics/pages/StatisticsPage.jsx"));
const MaterialsPage = lazy(() => import("../features/study_materials/pages/MaterialsPage.jsx"));

const LecturerLayout = lazy(() => import("../layouts/LecturerLayout.jsx"));
const ContentReportsPage = lazy(() => import("../features/lecturer/pages/ContentReportsPage.jsx"));
const ExamEditorPage = lazy(() => import("../features/lecturer/pages/ExamEditorPage.jsx"));
const LecturerOverviewPage = lazy(() => import("../features/lecturer/pages/LecturerOverviewPage.jsx"));
const LessonEditorPage = lazy(() => import("../features/lecturer/pages/LessonEditorPage.jsx"));
const LevelsPage = lazy(() => import("../features/lecturer/pages/LevelsPage.jsx"));
const MaterialEditorPage = lazy(() => import("../features/lecturer/pages/MaterialEditorPage.jsx"));
const MaterialListPage = lazy(() => import("../features/lecturer/pages/MaterialListPage.jsx"));
const PracticePathPage = lazy(() => import("../features/lecturer/pages/PracticePathPage.jsx"));
const VocabularyPage = lazy(() => import("../features/lecturer/pages/VocabularyPage.jsx"));
const WritingReviewDetailPage = lazy(() => import("../features/lecturer/pages/WritingReviewDetailPage.jsx"));
const WritingReviewListPage = lazy(() => import("../features/lecturer/pages/WritingReviewListPage.jsx"));
const LecturerExamListPage = lazy(() => import("../features/lecturer/pages/LecturerExamListPage.jsx"));
const AiExamBuilderPage = lazy(() => import("../features/lecturer/pages/AiExamBuilderPage.jsx"));
const AiExamHomePage = lazy(() => import("../features/lecturer/pages/AiExamHomePage.jsx"));
const AiExamReviewPage = lazy(() => import("../features/lecturer/pages/AiExamReviewPage.jsx"));
const AiExamStudioPage = lazy(() => import("../features/lecturer/pages/AiExamStudioPage.jsx"));
const AiQuestionStudioPage = lazy(() => import("../features/lecturer/pages/AiQuestionStudioPage.jsx"));
const QuestionEditorPage = lazy(() => import("../features/lecturer/pages/QuestionEditorPage.jsx"));
const QuestionQualityPage = lazy(() => import("../features/lecturer/pages/QuestionQualityPage.jsx"));
const QuestionListPage = lazy(() => import("../features/lecturer/pages/QuestionListPage.jsx"));

const AdminLayout = lazy(() => import("../layouts/AdminLayout.jsx"));
const AccountsPage = lazy(() => import("../features/admin/pages/AccountsPage.jsx"));
const AdminLogPage = lazy(() => import("../features/admin/pages/AdminLogPage.jsx"));
const AdminOverviewPage = lazy(() => import("../features/admin/pages/AdminOverviewPage.jsx"));
const RolesPage = lazy(() => import("../features/admin/pages/RolesPage.jsx"));

function RouteFallback() {
  return (
    <div style={{ padding: "2.5rem 1rem", textAlign: "center", color: "#64748b", fontSize: "0.95rem" }} aria-busy="true">
      Đang tải trang…
    </div>
  );
}

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

// Chỉ quay lại trang nội bộ thuộc khu vực của vai trò đăng nhập
function returnPathFor(user, from) {
  const home = homeOf(user);
  if (typeof from !== "string" || !from.startsWith("/") || from.startsWith("//")) return home;
  const isUnder = (prefix) => from === prefix || from.startsWith(`${prefix}/`);
  if (home !== "/" && isUnder(home)) return from;
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
  const { user } = useAuth();
  const navigate = useNavigate();
  const token = useOneTimeTokenFromUrl("/xac-minh-email");
  return <VerifyEmailPage token={token} onDone={() => navigate(user ? homeOf(user) : "/dang-nhap")} />;
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

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            {/* Khu vực công khai: chỉ giới thiệu hệ thống, tra từ điển nhanh và xác thực tài khoản.
                Mọi luồng Ôn luyện và Thi thử đều bắt buộc Đăng nhập -> Đánh giá trình độ đầu vào trước. */}
            <Route path="/" element={<PublicLayout />}>
              <Route index element={<PublicHomePage />} />
              <Route path="dang-nhap" element={<LoginRoute />} />
              <Route path="dang-ky" element={<RegisterRoute />} />
              <Route path="xac-minh-email" element={<VerifyEmailRoute />} />
              <Route path="quen-mat-khau" element={<ForgotPasswordRoute />} />
              <Route path="dat-lai-mat-khau" element={<ResetPasswordRoute />} />
              <Route path="on-luyen" element={<Navigate to="/hoc-vien/on-luyen" replace />} />
              <Route path="on-luyen/hoc-thu/*" element={<Navigate to="/hoc-vien/on-luyen" replace />} />
              <Route path="on-luyen/hsk/*" element={<Navigate to="/hoc-vien/on-luyen" replace />} />
              <Route path="thi-thu" element={<Navigate to="/hoc-vien/thi-thu" replace />} />
              <Route path="thi-thu/*" element={<Navigate to="/hoc-vien/thi-thu" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>

            {/* Làm bài / xem kết quả thi thử: toàn màn hình, chỉ Học viên */}
            <Route
              path="/thi-thu/lam-bai/:luotId"
              element={<RequireRole allowed={[ROLE.HOC_VIEN]}><ExamSessionPage /></RequireRole>}
            />
            <Route
              path="/thi-thu/ket-qua/:luotId"
              element={<RequireRole allowed={[ROLE.HOC_VIEN]}><ExamResultPage /></RequireRole>}
            />

            {/* Lượt ôn Sổ tay: toàn màn hình */}
            <Route path="/so-tay/on/:luotId" element={<RequireRole allowed={[ROLE.HOC_VIEN]}><NotebookReviewPage /></RequireRole>} />

            {/* Đánh giá trình độ đầu vào thích ứng 8 câu */}
            <Route path="/danh-gia-dau-vao" element={<RequireRole allowed={[ROLE.HOC_VIEN]}><PlacementTestPage /></RequireRole>} />
            <Route path="/danh-gia-dau-vao/lam-bai/:luotId" element={<RequireRole allowed={[ROLE.HOC_VIEN]}><PlacementTestPage /></RequireRole>} />
            <Route path="/danh-gia-dau-vao/ket-qua/:luotId" element={<RequireRole allowed={[ROLE.HOC_VIEN]}><PlacementResultPage /></RequireRole>} />
            <Route path="/khao-sat" element={<Navigate to="/danh-gia-dau-vao" replace />} />

            {/* Kiểm tra vượt thửa / bắt đầu cấp: toàn màn hình, chỉ Học viên */}
            <Route
              path="/on-luyen/vuot/:luotId"
              element={<RequireRole allowed={[ROLE.HOC_VIEN]}><SkipTestPage /></RequireRole>}
            />

            {/* Làm bài ôn luyện: toàn màn hình, chỉ Học viên */}
            <Route
              path="/on-luyen/bai/:luotId"
              element={<RequireRole allowed={[ROLE.HOC_VIEN]}><LessonPage /></RequireRole>}
            />

            {/* Học viên: Đánh giá đầu vào -> Ôn luyện theo trình độ & Thi thử ngẫu nhiên */}
            <Route
              path="/hoc-vien"
              element={
                <RequireRole allowed={[ROLE.HOC_VIEN]}>
                  <StudentLayout />
                </RequireRole>
              }
            >
              <Route index element={<StudentHomePage />} />
              <Route path="thi-thu" element={<MockTestLobbyPage />} />
              <Route path="thi-thu/*" element={<Navigate to="/hoc-vien/thi-thu" replace />} />
              <Route path="on-luyen" element={<PracticeHomePage />} />
              <Route path="on-luyen/:kyNang" element={<PracticeMapPage />} />
              <Route path="so-tay-cau-sai" element={<NotebookPage />} />
              <Route path="ca-nhan" element={<ProfilePage />} />
              <Route path="lich-su-thi" element={<ExamHistoryPage />} />
              <Route path="thong-ke" element={<StatisticsPage />} />
              <Route path="tai-lieu" element={<MaterialsPage />} />
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
              <Route index element={<LecturerOverviewPage />} />
              <Route path="cap-do" element={<LevelsPage />} />
              <Route path="tu-vung" element={<VocabularyPage />} />
              <Route path="cau-hoi" element={<QuestionListPage />} />
              <Route path="cau-hoi/ai" element={<AiQuestionStudioPage />} />
              <Route path="chat-luong" element={<QuestionQualityPage />} />
              <Route path="cau-hoi/moi" element={<QuestionEditorPage />} />
              <Route path="cau-hoi/:id" element={<QuestionEditorPage />} />
              <Route path="bo-de" element={<LecturerExamListPage />} />
              <Route path="bo-de/ai" element={<AiExamHomePage />} />
              <Route path="bo-de/ai/:id" element={<AiExamReviewPage />} />
              <Route path="bo-de/ai-tung-phan" element={<AiExamBuilderPage />} />
              <Route path="bo-de/ai-ngan-hang" element={<AiExamStudioPage />} />
              <Route path="bo-de/moi" element={<ExamEditorPage />} />
              <Route path="bo-de/:id" element={<ExamEditorPage />} />
              <Route path="bai-luyen" element={<PracticePathPage />} />
              <Route path="bai-luyen/bai/:id" element={<LessonEditorPage />} />
              <Route path="hoc-lieu" element={<MaterialListPage />} />
              <Route path="hoc-lieu/moi" element={<MaterialEditorPage />} />
              <Route path="hoc-lieu/:id" element={<MaterialEditorPage />} />
              <Route path="cham-viet" element={<WritingReviewListPage />} />
              <Route path="cham-viet/:id" element={<WritingReviewDetailPage />} />
              <Route path="bao-loi" element={<ContentReportsPage />} />
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
              <Route index element={<AdminOverviewPage />} />
              <Route path="tai-khoan" element={<AccountsPage />} />
              <Route path="vai-tro" element={<RolesPage />} />
              <Route path="nhat-ky" element={<AdminLogPage />} />
              <Route path="*" element={<Navigate to="/quan-tri" replace />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
