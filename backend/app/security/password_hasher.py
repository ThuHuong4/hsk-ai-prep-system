import base64
import binascii
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16
HASH_BYTES = 32


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=HASH_BYTES
    )
    return f"{ALGORITHM}${ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored_hash.split("$")
        if algorithm != ALGORITHM or int(iterations) != ITERATIONS:
            return False
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(hash_b64, validate=True)
        if len(salt) != SALT_BYTES or len(expected) != HASH_BYTES:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=HASH_BYTES
        )
        return hmac.compare_digest(digest, expected)
    except (AttributeError, ValueError, OverflowError, binascii.Error):
        return False