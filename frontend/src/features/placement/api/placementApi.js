/**
 * Tầng gọi API cho phân hệ Đánh giá trình độ đầu vào 8 câu (`placement/`).
 * - Vai trò: Đóng gói mọi HTTP request tới `/api/danh-gia-dau-vao/*`.
 * - Được gọi bởi: `PlacementTestPage.jsx`, `PlacementResultPage.jsx`, `StudentHomePage.jsx`, `PracticeHomePage.jsx`.
 */
import { http } from "../../../shared/api/httpClient.js";

export const getPlacementGate = (token, signal) =>
  http.get("/api/danh-gia-dau-vao/trang-thai", { token, signal });

export const startPlacement = (token) =>
  http.post("/api/danh-gia-dau-vao/bat-dau", undefined, { token });

export const deferPlacement = (token) =>
  http.post("/api/danh-gia-dau-vao/de-sau", undefined, { token });

export const getPlacementSession = (token, luotId, signal) =>
  http.get(`/api/danh-gia-dau-vao/luot/${luotId}`, { token, signal });

export const submitPlacementStep = (token, luotId, body) =>
  http.post(`/api/danh-gia-dau-vao/luot/${luotId}/tra-loi`, body, { token });

export const replaceBrokenQuestion = (token, luotId, lyDo = "loi_audio") =>
  http.post(`/api/danh-gia-dau-vao/luot/${luotId}/doi-cau`, { ly_do: lyDo }, { token });

export const analyzePlacement = (token, luotId) =>
  http.post(`/api/danh-gia-dau-vao/luot/${luotId}/phan-tich`, undefined, { token });

export const getPlacementResult = (token, luotId, signal) =>
  http.get(`/api/danh-gia-dau-vao/luot/${luotId}/ket-qua`, { token, signal });

export const savePlacementGoal = (token, body) =>
  http.put("/api/danh-gia-dau-vao/muc-tieu", body, { token });
