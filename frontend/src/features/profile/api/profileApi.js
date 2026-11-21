import { http } from "../../../shared/api/httpClient.js";

export const getProfile = (token, signal) => http.get("/api/ca-nhan", { token, signal });
export const saveName = (token, ho_ten) => http.patch("/api/ca-nhan/ho-so", { ho_ten }, { token });
export const saveReminder = (token, on) => http.patch("/api/ca-nhan/nhac-hoc", { nhan_email_nhac: on }, { token });
export const changePassword = (token, mat_khau_cu, mat_khau_moi) =>
  http.post("/api/ca-nhan/doi-mat-khau", { mat_khau_cu, mat_khau_moi }, { token });
