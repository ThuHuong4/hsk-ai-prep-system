// Công cụ gọi API dùng chung
import { http } from "../../../shared/api/httpClient.js";

// Gửi email và mật khẩu đến backend để đăng nhập, trả về kết quả
export function login(email, password) {
  return http.post("/api/auth/login", { email, password });
}
//Luồng chạy: Bấm Đăng nhập → gọi hàm login → 
// gửi đến backend → backend kiểm tra → trang nhận kết quả thành công hoặc lỗi.