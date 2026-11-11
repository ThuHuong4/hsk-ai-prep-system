export default function UnderDevelopment({ title }) {
  return (
    <section>
      <h1>{title}</h1>
      <p role="status" className="muted">
        Đang phát triển. Chức năng này sẽ có trong các bản cập nhật tiếp theo.
      </p>
    </section>
  );
}