import { http } from "../../../shared/api/httpClient.js";

// Gửi đoạn chat hiện tại của 1 câu; backend tự lấy đề, đáp án từ CSDL
export const askXiang = (token, luotId, cauHoiId, messages) =>
  http.post("/api/hoi-xiang", { luot_id: luotId, cau_hoi_id: cauHoiId, tin_nhan: messages }, { token });