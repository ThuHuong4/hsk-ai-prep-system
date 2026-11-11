import logging

from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.google_config import GOOGLE_CLIENT_ID

logger = logging.getLogger(__name__)
_transport = google_requests.Request()


class InvalidGoogleTokenError(Exception):
    pass


class GoogleServiceUnavailableError(Exception):
    pass


def verify_google_id_token(credential: str) -> dict:
    try:
        claims = id_token.verify_oauth2_token(
            credential,
            _transport,
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except google_exceptions.TransportError as error:
        raise GoogleServiceUnavailableError() from error
    except (ValueError, google_exceptions.GoogleAuthError) as error:
        message = str(error).lower()

        if "audience" in message:
            reason = "CLIENT_ID_KHONG_KHOP"
        elif "too early" in message or "iat" in message:
            reason = "KIEM_TRA_GIO_MAY_TINH"
        elif "expired" in message:
            reason = "TOKEN_HET_HAN_HOAC_GIO_MAY_SAI"
        elif "signature" in message:
            reason = "LOI_CHU_KY"
        elif "issuer" in message:
            reason = "LOI_ISSUER"
        else:
            reason = "CHUA_XAC_DINH"

        logger.warning(
            "Google token rejected: reason=%s, type=%s",
            reason,
            type(error).__name__,
        )
        raise InvalidGoogleTokenError() from error

    sub = claims.get("sub")
    email = claims.get("email")

    if (
        not isinstance(sub, str)
        or not sub
        or len(sub) > 255
        or not isinstance(email, str)
        or not email
    ):
        raise InvalidGoogleTokenError()

    return {
        "sub": sub,
        "email": email,
        "email_verified": claims.get("email_verified") is True,
        "name": (
            claims.get("name")
            if isinstance(claims.get("name"), str)
            else ""
        ),
    }