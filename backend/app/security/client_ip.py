import ipaddress

from fastapi import Request

UNKNOWN_IP = "unknown"


def get_client_ip(request: Request) -> str:
    # Chỉ dùng IP kết nối trực tiếp; không đọc X-Forwarded-For vì chưa có proxy đáng tin cậy
    host = request.client.host if request.client else None
    if not host:
        return UNKNOWN_IP
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return UNKNOWN_IP
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return str(ip)