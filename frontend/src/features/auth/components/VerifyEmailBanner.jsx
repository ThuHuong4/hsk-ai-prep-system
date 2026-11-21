import { useAuth } from "../context/AuthContext.jsx";
import ResendVerificationButton from "./ResendVerificationButton.jsx";

// Thanh nhắc xác minh: chỉ hiện khi đã đăng nhập mà email chưa xác minh
export default function VerifyEmailBanner() {
  const { user } = useAuth();
  if (!user || user.email_da_xac_minh) return null;
  return (
    <div className="verify-banner" role="region" aria-label="Xác minh email">
      <span>
        Xác minh <strong>{user.email}</strong> để lấy lại mật khẩu khi quên và nhận email nhắc học.
      </span>
      <ResendVerificationButton />
    </div>
  );
}
