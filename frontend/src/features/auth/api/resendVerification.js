import { http } from "../../../shared/api/httpClient.js";

// Người đã đăng nhập tự gửi lại thư xác minh cho email của mình
export function resendVerification(token) {
  return http.post("/api/auth/resend-verification", undefined, { token });
}
