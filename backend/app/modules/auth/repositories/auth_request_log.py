from sqlalchemy import text
from sqlalchemy.orm import Session


def record_auth_request(db: Session, muc_dich: str, bam_email: bytes, dia_chi_ip: str) -> None:
    db.execute(
        text("""
            INSERT INTO yeu_cau_xac_thuc (muc_dich, bam_email, dia_chi_ip, ngay_tao)
            VALUES (:muc_dich, :bam_email, :dia_chi_ip, NOW(3))
        """),
        {"muc_dich": muc_dich, "bam_email": bam_email, "dia_chi_ip": dia_chi_ip},
    )


def get_email_request_stats(db: Session, muc_dich: str, bam_email: bytes) -> dict:
    # FOR UPDATE: đọc bản mới nhất đã commit, không dùng snapshot cũ của transaction
    row = db.execute(
        text("""
            SELECT COUNT(*) AS so_lan_1_gio,
                   TIMESTAMPDIFF(SECOND, MAX(ngay_tao), NOW(3)) AS giay_tu_lan_cuoi
            FROM yeu_cau_xac_thuc
            WHERE bam_email = :bam_email
              AND muc_dich = :muc_dich
              AND ngay_tao > NOW(3) - INTERVAL 1 HOUR
            FOR UPDATE
        """),
        {"muc_dich": muc_dich, "bam_email": bam_email},
    ).mappings().one()
    return dict(row)


def count_ip_requests_last_hour(db: Session, muc_dich: str, dia_chi_ip: str) -> int:
    return db.execute(
        text("""
            SELECT COUNT(*)
            FROM yeu_cau_xac_thuc
            WHERE dia_chi_ip = :dia_chi_ip
              AND muc_dich = :muc_dich
              AND ngay_tao > NOW(3) - INTERVAL 1 HOUR
            FOR UPDATE
        """),
        {"muc_dich": muc_dich, "dia_chi_ip": dia_chi_ip},
    ).scalar_one()


def delete_old_auth_requests(db: Session, retention_days: int, batch_size: int = 1000) -> int:
    result = db.execute(
        text("""
            DELETE FROM yeu_cau_xac_thuc
            WHERE ngay_tao < NOW(3) - INTERVAL :retention_days DAY
            ORDER BY ngay_tao
            LIMIT :batch_size
        """),
        {"retention_days": retention_days, "batch_size": batch_size},
    )
    return result.rowcount