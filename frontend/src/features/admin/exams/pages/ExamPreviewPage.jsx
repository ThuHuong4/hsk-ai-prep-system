import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "../../../auth/context/AuthContext.jsx";
import { previewExam } from "../api/previewExam.js";

const STATUS_LABELS = { 0: "Nháp", 1: "Đã xuất bản", 2: "Ẩn/ngừng dùng" };

function toMediaUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//i.test(path) || path.startsWith("/")) return path;
  return `/media/${path}`;
}

function formatMinutes(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return rest ? `${minutes} phút ${rest} giây` : `${minutes} phút`;
}

function MediaImage({ src, alt }) {
  const url = toMediaUrl(src);
  return url ? <img src={url} alt={alt} style={{ maxWidth: "100%" }} /> : null;
}

function MediaAudio({ src }) {
  const url = toMediaUrl(src);
  return url ? <audio controls preload="none" src={url} /> : null;
}

function QuestionGroup({ group }) {
  return (
    <div style={{ border: "1px dashed #999", padding: 8, margin: "8px 0" }}>
      <strong>Nội dung dùng chung (nhóm {group.ma_nhom_cau_hoi})</strong>
      {group.noi_dung && <p style={{ whiteSpace: "pre-wrap" }}>{group.noi_dung}</p>}
      <MediaImage src={group.hinh_anh_url} alt={`Nhóm ${group.ma_nhom_cau_hoi}`} />
    </div>
  );
}

function Question({ question }) {
  return (
    <div style={{ margin: "12px 0" }}>
      <p>
        <strong>Câu {question.so_cau}.</strong>{" "}
        <span style={{ whiteSpace: "pre-wrap" }}>{question.noi_dung}</span>
      </p>
      {question.ngu_lieu && <p style={{ whiteSpace: "pre-wrap" }}>{question.ngu_lieu}</p>}
      <MediaImage src={question.hinh_anh_url} alt={`Câu ${question.so_cau}`} />
      <MediaAudio src={question.am_thanh_url} />
      {question.phuong_an.length > 0 && (
        <ul style={{ listStyle: "none", paddingLeft: 0 }}>
          {question.phuong_an.map((option) => (
            <li key={option.ma_phuong_an}>
              <strong>{option.ky_hieu}.</strong> {option.noi_dung}
              <MediaImage src={option.hinh_anh_url} alt={`Phương án ${option.ky_hieu}`} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Section({ section, groupsById }) {
  return (
    <section style={{ borderTop: "1px solid #ccc", marginTop: 16 }}>
      <h2>
        Phần {section.thu_tu}: {section.ten_phan}
      </h2>
      {section.huong_dan && <p style={{ whiteSpace: "pre-wrap" }}>{section.huong_dan}</p>}
      {section.cau_hoi.map((question, index) => {
        const groupId = question.ma_nhom_cau_hoi;
        const previousGroupId = index > 0 ? section.cau_hoi[index - 1].ma_nhom_cau_hoi : null;
        const group = groupId != null && groupId !== previousGroupId ? groupsById.get(groupId) : null;
        return (
          <div key={question.ma_cau_hoi}>
            {group && <QuestionGroup group={group} />}
            <Question question={question} />
          </div>
        );
      })}
    </section>
  );
}

export default function ExamPreviewPage() {
  const { token } = useAuth();
  const [input, setInput] = useState("");
  const [exam, setExam] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const groupsById = useMemo(
    () => new Map((exam?.nhom_cau_hoi ?? []).map((g) => [g.ma_nhom_cau_hoi, g])),
    [exam]
  );

  async function handleSubmit(event) {
    event.preventDefault();
    const value = input.trim();
    if (!/^\d+$/.test(value) || Number(value) < 1) {
      setError("Mã đề phải là số nguyên dương");
      return;
    }

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setError("");
    setExam(null);
    try {
      const data = await previewExam(Number(value), token, controller.signal);
      setExam(data);
    } catch (err) {
      if (err.name === "AbortError") return;
      setError(err?.message || "Không tải được đề thi");
    } finally {
      if (controllerRef.current === controller) setLoading(false);
    }
  }

  return (
    <div>
      <h1>Xem trước đề thi</h1>

      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="preview-exam-id">Mã đề</label>
        <input
          id="preview-exam-id"
          type="number"
          min="1"
          step="1"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Đang tải..." : "Xem trước"}
        </button>
      </form>

      {error && <p role="alert">{error}</p>}

      {exam && (
        <article>
          <h2>{exam.ten_bo_de}</h2>
          <p>
            Mã đề: {exam.ma_bo_de} · HSK {exam.ma_cap_do} · Trạng thái:{" "}
            {STATUS_LABELS[exam.trang_thai] ?? exam.trang_thai} · Thời lượng:{" "}
            {formatMinutes(exam.thoi_gian_giay)}
          </p>
          {exam.am_thanh_url && (
            <div>
              <strong>Audio của đề:</strong> <MediaAudio src={exam.am_thanh_url} />
            </div>
          )}
          {exam.phan.map((section) => (
            <Section key={section.ma_phan} section={section} groupsById={groupsById} />
          ))}
        </article>
      )}
    </div>
  );
}