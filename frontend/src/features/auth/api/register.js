import { http } from "../../../shared/api/httpClient.js";

export function register(hoTen, email, password) {
  return http.post("/api/auth/register", { ho_ten: hoTen, email, password });
}