import { http } from "../../../shared/api/httpClient.js";

export function resendVerification(email) {
  return http.post("/api/auth/resend-verification", { email });
}