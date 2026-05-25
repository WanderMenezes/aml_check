from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from django.conf import settings


def _build_payload(subject: str, token_type: str, expires_at: datetime, extra: dict | None = None) -> dict:
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.JWT_SETTINGS["ISSUER"],
    }
    if extra:
        payload.update(extra)
    return payload


def create_access_token(subject: str, extra: dict | None = None) -> tuple[str, dict]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.JWT_SETTINGS["ACCESS_TTL_MINUTES"])
    payload = _build_payload(subject, "access", expires_at, extra)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_SETTINGS["ALGORITHM"])
    return token, payload


def create_refresh_token(subject: str, extra: dict | None = None) -> tuple[str, dict]:
    expires_at = datetime.now(UTC) + timedelta(days=settings.JWT_SETTINGS["REFRESH_TTL_DAYS"])
    payload = _build_payload(subject, "refresh", expires_at, extra)
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_SETTINGS["ALGORITHM"])
    return token, payload


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_SETTINGS["ALGORITHM"]],
        issuer=settings.JWT_SETTINGS["ISSUER"],
    )
