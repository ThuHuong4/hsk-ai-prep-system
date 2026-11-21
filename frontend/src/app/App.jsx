import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

import { AuthProvider, useAuth } from "../features/auth/context/AuthContext.jsx";
import ForgotPasswordPage from "../features/auth/pages/ForgotPasswordPage.jsx";
import LoginPage from "../features/auth/pages/LoginPage.jsx";
import RegisterPage from "../features/auth/pages/RegisterPage.jsx";
import ResetPasswordPage from "../features/auth/pages/ResetPasswordPage.jsx";
import VerifyEmailPage from "../features/auth/pages/VerifyEmailPage.jsx";
import { ROLE, homePathForRole } from "../features/auth/utils/roles.js";
import ExamInfoPage from "../features/exam_catalog/pages/ExamInfoPage.jsx";
import ExamListPage from "../features/exam_catalog/pages/ExamListPage.jsx";
import ExamHistoryPage from "../features/mock_test/pages/ExamHistoryPage.jsx";
import ExamResultPage from "../features/mock_test/pages/ExamResultPage.jsx";
import ExamSessionPage from "../features/mock_test/pages/ExamSessionPage.jsx";
import LevelPickerPage from "../features/exam_catalog/pages/LevelPickerPage.jsx";
import PublicHomePage from "../features/home/pages/PublicHomePage.jsx";
import StudentHomePage from "../features/home/pages/StudentHomePage.jsx";
import ContentReportsPage from "../features/lecturer/pages/ContentReportsPage.jsx";
import ExamEditorPage from "../features/lecturer/pages/ExamEditorPage.jsx";
import LecturerOverviewPage from "../features/lecturer/pages/LecturerOverviewPage.jsx";
import LessonEditorPage from "../features/lecturer/pages/LessonEditorPage.jsx";
import LevelsPage from "../features/lecturer/pages/LevelsPage.jsx";
import MaterialEditorPage from "../features/lecturer/pages/MaterialEditorPage.jsx";
import MaterialListPage from "../features/lecturer/pages/MaterialListPage.jsx";
import PracticePathPage from "../features/lecturer/pages/PracticePathPage.jsx";
import VocabularyPage from "../features/lecturer/pages/VocabularyPage.jsx";
import WritingReviewDetailPage from "../features/lecturer/pages/WritingReviewDetailPage.jsx";
import WritingReviewListPage from "../features/lecturer/pages/WritingReviewListPage.jsx";
import LecturerExamListPage from "../features/lecturer/pages/LecturerExamListPage.jsx";
import QuestionEditorPage from "../features/lecturer/pages/QuestionEditorPage.jsx";
import QuestionListPage from "../features/lecturer/pages/QuestionListPage.jsx";
import LessonPage from "../features/practice/pages/LessonPage.jsx";
import PracticeHomePage from "../features/practice/pages/PracticeHomePage.jsx";
import PracticeMapPage from "../features/practice/pages/PracticeMapPage.jsx";
import AccountsPage from "../features/admin/pages/AccountsPage.jsx";
import AdminLogPage from "../features/admin/pages/AdminLogPage.jsx";
import AdminOverviewPage from "../features/admin/pages/AdminOverviewPage.jsx";
import RolesPage from "../features/admin/pages/RolesPage.jsx";
import NotebookPage from "../features/notebook/pages/NotebookPage.jsx";
import NotebookReviewPage from "../features/notebook/pages/NotebookReviewPage.jsx";
import SurveyPage from "../features/survey/pages/SurveyPage.jsx";
import SkipTestPage from "../features/practice/pages/SkipTestPage.jsx";
import GuestLessonPage from "../features/practice/guest/GuestLessonPage.jsx";
import GuestPracticeHomePage from "../features/practice/guest/GuestPracticeHomePage.jsx";
import GuestPracticeMapPage from "../features/practice/guest/GuestPracticeMapPage.jsx";
import ProfilePage from "../features/profile/pages/ProfilePage.jsx";
import AdminLayout from "../layouts/AdminLayout.jsx";
import LecturerLayout from "../layouts/LecturerLayout.jsx";
import PublicLayout from "../layouts/PublicLayout.jsx";
import StudentLayout from "../layouts/StudentLayout.jsx";
import RequireRole from "../routes/RequireRole.jsx";
import UnderDevelopment from "../shared/components/UnderDevelopment.jsx";
import StatisticsPage from "../features/statistics/pages/StatisticsPage.jsx";
import MaterialsPage from "../features/study_materials/pages/MaterialsPage.jsx";
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

// Đường dẫn cũ /on-luyen/hsk/:cap/:kyNang → /on-luyen/:kyNang?cap=
function OldGuestMapRedirect() {
  const { maCapDo, kyNang } = useParams();
  return <Navigate to={`/on-luyen/${kyNang}?cap=${encodeURIComponent(maCapDo)}`} replace />;
}

// Chọn cấp → đề / kỹ năng: dùng chung cho khách (prefix "") và Học viên (prefix "/hoc-vien")
function catalogRoutes(prefix, guest) {
  const examBase = `${prefix}/thi-thu`;
  return (
    <>
      <Route
        path="thi-thu"
        element={<LevelPickerPage kind="exam" title="Đề thi thử HSK" description="Đề theo cấu trúc HSK 2.0, tính giờ như phòng thi. Xem đề tự do, đăng nhập khi bắt đầu làm bài." basePath={examBase} />}
      />
      <Route path="thi-thu/hsk/:maCapDo" element={<ExamListPage basePath={examBase} />} />
      <Route path="thi-thu/de/:maBoDe" element={<ExamInfoPage basePath={examBase} />} />
      {guest ? (
        <>
          {/* Khách: giống Học viên — chọn kỹ năng → bản đồ; tiến độ chỉ lưu trên trình duyệt */}
          <Route path="on-luyen" element={<GuestPracticeHomePage />} />
          <Route path="on-luyen/hsk/:maCapDo" element={<Navigate to="/on-luyen" replace />} />
          <Route path="on-luyen/hsk/:maCapDo/:kyNang" element={<OldGuestMapRedirect />} />
          <Route path="on-luyen/:kyNang" element={<GuestPracticeMapPage />} />
        </>
      ) : (
        <>
          {/* Học viên: Kỹ năng → bản đồ thửa theo cấp (mục 4.1) */}
          <Route path="on-luyen" element={<PracticeHomePage />} />
          <Route path="on-luyen/:kyNang" element={<PracticeMapPage />} />
        </>
      )}
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

          {/* Khảo sát đầu vào: một lần sau lần đăng nhập đầu, toàn màn hình */}
          <Route path="/khao-sat" element={<RequireRole allowed={[ROLE.HOC_VIEN]}><SurveyPage /></RequireRole>} />

          {/* Kiểm tra vượt thửa: toàn màn hình, chỉ Học viên */}
          <Route
            path="/on-luyen/vuot/:luotId"
            element={<RequireRole allowed={[ROLE.HOC_VIEN]}><SkipTestPage /></RequireRole>}
          />

          {/* Khách học thử một bài: toàn màn hình, không lưu */}
          <Route path="/on-luyen/hoc-thu/:maGoc" element={<GuestLessonPage />} />

          <Route
            path="/on-luyen/bai/:luotId"
            element={<RequireRole allowed={[ROLE.HOC_VIEN]}><LessonPage /></RequireRole>}
          />

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
            <Route path="cau-hoi/moi" element={<QuestionEditorPage />} />
            <Route path="cau-hoi/:id" element={<QuestionEditorPage />} />
            <Route path="bo-de" element={<LecturerExamListPage />} />
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
      </AuthProvider>
    </BrowserRouter>
  );
}