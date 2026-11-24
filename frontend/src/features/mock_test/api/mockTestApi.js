/**
 * Tầng gọi API cho phân hệ Thi thử HSK của Học viên (`mock_test/`).
 * - Vai trò: Nhận thông tin phòng chờ chọn cấp HSK (mặc định theo cấp Đánh giá đầu vào),
 *   yêu cầu cấp đề ngẫu nhiên bảo mật trước giờ thi, lưu bài làm và nộp bài.
 */
import { http } from "../../../shared/api/httpClient.js";

export const getExamLobby = (token, signal) =>
  http.get("/api/thi-thu/chon-cap", { token, signal });

export const startRandomExam = (token) =>
  http.post("/api/thi-thu/bat-dau", {}, { token });

export const getAttempt = (token, id, signal) =>
  http.get(`/api/thi-thu/luot/${id}`, { token, signal });

export const saveAnswer = (token, id, body) =>
  http.put(`/api/thi-thu/luot/${id}/tra-loi`, body, { token });

export const advanceExamSection = (token, id) =>
  http.post(`/api/thi-thu/luot/${id}/chuyen-phan`, {}, { token });

export const submitAttempt = (token, id, hetGio = false, thuBaiViPham = false) =>
  http.post(`/api/thi-thu/luot/${id}/nop`, { het_gio: hetGio, thu_bai_vi_pham: thuBaiViPham }, { token });

export const getResult = (token, id, signal) =>
  http.get(`/api/thi-thu/luot/${id}/ket-qua`, { token, signal });

export const getHistory = (token, signal) =>
  http.get("/api/thi-thu/lich-su", { token, signal });
