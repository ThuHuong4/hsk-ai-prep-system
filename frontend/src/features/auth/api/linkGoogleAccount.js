import { http } from "../../../shared/api/httpClient.js";

export function linkGoogleAccount(credential, password) {
  return http.post("/api/auth/google/link", { credential, password });
}