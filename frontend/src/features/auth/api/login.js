import { http } from "../../../shared/api/httpClient.js";

export function login(email, password) {
  return http.post("/api/auth/login", { email, password });
}