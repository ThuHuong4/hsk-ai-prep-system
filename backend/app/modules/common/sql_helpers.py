def in_params(prefix: str, values) -> tuple[str, dict]:
    """Tạo ':p0, :p1' và dict tham số cho câu IN (...)."""
    params = {f"{prefix}{n}": v for n, v in enumerate(values)}
    return ", ".join(f":{k}" for k in params) or "NULL", params
