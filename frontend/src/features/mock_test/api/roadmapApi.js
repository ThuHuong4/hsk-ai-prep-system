import { http } from "../../../shared/api/httpClient.js";

// Mục 6.2: lần đầu tạo gợi ý (AI một lần) rồi lưu; lần sau trả bản đã lưu
export const getRoadmap = (token, luotId) => http.post(`/api/thi-thu/luot/${luotId}/goi-y-lo-trinh`, undefined, { token });
