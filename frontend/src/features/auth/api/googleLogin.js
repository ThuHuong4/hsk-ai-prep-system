import { http } from "../../../shared/api/httpClient.js";

export function googleLogin(credential) {
  return http.post("/api/auth/google", { credential });
}