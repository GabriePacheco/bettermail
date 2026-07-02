from datetime import datetime, timezone
import hmac

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.billing_service import activate_certification_subscription
from app.config import get_settings
from app.firebase_service import get_db, get_or_create_mailbox_user
from app.models import OfficeUser
from app.security import hash_email, normalize_email


def _as_utc(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _active_pro_response(data: dict):
    period_end = _as_utc(data.get("currentPeriodEnd"))
    has_active_state = (
        data.get("plan") == "pro"
        and data.get("status") == "active"
        and data.get("subscriptionStatus") in {"active", "cancel_pending", "past_due"}
    )
    is_paid_access = has_active_state and data.get("paymentProvider") != "certification"
    is_current_certification = (
        has_active_state
        and data.get("paymentProvider") == "certification"
        and bool(period_end and period_end > datetime.now(timezone.utc))
    )
    if not is_paid_access and not is_current_certification:
        return None

    return {
        "activated": True,
        "plan": "pro",
        "status": "active",
        "valid_until": period_end.isoformat(),
        "message": (
            "El acceso de certificacion ya esta activo."
            if is_current_certification
            else "La cuenta ya tiene BetterMail Pro activo."
        ),
    }


def activate_certification_access(email: str, license_key: str, trial_limit: int):
    settings = get_settings()
    expected_key = (settings.certification_license_secret or "").strip()
    received_key = (license_key or "").strip()

    if not settings.certification_access_enabled or not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La activacion de certificacion no esta disponible.",
        )

    if not hmac.compare_digest(received_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar la licencia de certificacion.",
        )

    normalized_email = normalize_email(email)
    user = OfficeUser(email=normalized_email, account_type="outlook")
    user_ref, user_data = get_or_create_mailbox_user(user, trial_limit)

    if user_data.get("status") == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta cuenta no puede activar acceso de certificacion.",
        )

    active_response = _active_pro_response(user_data)
    if active_response:
        return active_response

    result = activate_certification_subscription(
        email=normalized_email,
        plan_id="pro_monthly",
        trial_limit=trial_limit,
        period_days=settings.certification_access_days,
    )

    email_hash = hash_email(normalized_email)
    get_db().collection("certification_activations").document(email_hash).set(
        {
            "emailHash": email_hash,
            "status": "active",
            "plan": "pro",
            "validUntil": result.get("currentPeriodEnd"),
            "activatedAt": SERVER_TIMESTAMP,
            "updatedAt": SERVER_TIMESTAMP,
        },
        merge=True,
    )
    user_ref.update({
        "certificationAccess": True,
        "certificationActivatedAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    })

    return {
        "activated": True,
        "plan": result["plan"],
        "status": result["status"],
        "valid_until": result.get("currentPeriodEnd"),
        "message": "BetterMail Pro de certificacion fue activado correctamente.",
    }
