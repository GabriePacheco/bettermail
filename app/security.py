import hashlib
from fastapi import Header, HTTPException, status
from app.config import get_settings


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str) -> str:
    normalized = normalize_email(email)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_app_secret(x_app_secret: str | None = Header(default=None)):
    settings = get_settings()

    received_secret = (x_app_secret or "").strip()
    expected_secret = (settings.app_shared_secret or "").strip()

    if not received_secret or received_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized client",
        )

    return True