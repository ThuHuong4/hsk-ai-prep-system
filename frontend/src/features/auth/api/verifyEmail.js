import { http } from "../../../shared/api/httpClient.js";

export function verifyEmail(token) {
  return http.post("/api/auth/verify-email", { token });
}