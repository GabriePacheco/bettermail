from datetime import datetime, timezone

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.billing_service import (
    _expire_subscription,
    _find_current_subscription,
    _iso,
    activate_manual_subscription,
    cancel_subscription,
    get_billing_status,
)
from app.firebase_service import get_db, get_user_ref
from app.models import OfficeUser
from app.security import hash_email, normalize_email


def _audit_metadata(data: dict | None):
    allowed = {
        "reason",
        "planId",
        "previousStatus",
        "newStatus",
        "effectiveAt",
        "source",
    }
    return {key: value for key, value in (data or {}).items() if key in allowed and value is not None}


def record_admin_audit(action: str, email: str, metadata: dict | None = None):
    normalized_email = normalize_email(email)
    get_db().collection("audit_logs").add({
        "actor": "admin_api",
        "action": action,
        "emailHash": hash_email(normalized_email),
        "metadata": _audit_metadata(metadata),
        "createdAt": SERVER_TIMESTAMP,
    })


def _audit_sort_key(event):
    value = event.get("createdAt")
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _recent_audit_events(db, email_hash: str, limit: int = 20):
    events = []
    snapshots = db.collection("audit_logs").where("emailHash", "==", email_hash).stream()
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        events.append(data)

    events.sort(key=_audit_sort_key, reverse=True)
    return [
        {
            "action": event.get("action", "unknown"),
            "createdAt": _iso(event.get("createdAt")),
            "metadata": _audit_metadata(event.get("metadata")),
        }
        for event in events[:limit]
    ]


def get_admin_user(email: str, trial_limit: int):
    normalized_email = normalize_email(email)
    email_hash = hash_email(normalized_email)
    db = get_db()
    user_ref = get_user_ref(normalized_email)
    snapshot = user_ref.get()

    if not snapshot.exists:
        return {
            "exists": False,
            "email": normalized_email,
            "status": "not_found",
            "auditEvents": _recent_audit_events(db, email_hash),
        }

    get_billing_status(OfficeUser(email=normalized_email), trial_limit)
    data = user_ref.get().to_dict() or {}
    payment_snapshot = db.collection("payment_methods").document(f"payphone_{email_hash}").get()
    payment = payment_snapshot.to_dict() if payment_snapshot.exists else {}

    return {
        "exists": True,
        "email": normalized_email,
        "displayName": data.get("displayName"),
        "accountType": data.get("accountType"),
        "plan": data.get("plan", "trial"),
        "status": data.get("status", "trial"),
        "subscriptionStatus": data.get("subscriptionStatus"),
        "trialLimit": int(data.get("trialLimit", trial_limit)),
        "trialUsed": int(data.get("trialUsed", 0)),
        "monthlyLimit": int(data.get("monthlyLimit", 0)),
        "monthlyUsed": int(data.get("monthlyUsed", 0)),
        "currentPeriodEnd": _iso(data.get("currentPeriodEnd")),
        "gracePeriodEnd": _iso(data.get("gracePeriodEnd")),
        "cancelAtPeriodEnd": bool(data.get("cancelAtPeriodEnd", False)),
        "autoRenew": bool(data.get("autoRenew", False)),
        "paymentActionRequired": bool(data.get("paymentActionRequired", False)),
        "renewalFailureCount": int(data.get("renewalFailureCount", 0)),
        "paymentProvider": data.get("paymentProvider"),
        "hasReusablePaymentMethod": bool(payment.get("cardToken")),
        "cardBrand": payment.get("cardBrand"),
        "cardLastDigits": payment.get("lastDigits"),
        "auditEvents": _recent_audit_events(db, email_hash),
    }


def admin_activate_user(email: str, plan_id: str, trial_limit: int, reason: str | None = None):
    current = get_admin_user(email, trial_limit)
    if current.get("status") == "blocked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Desbloquea el usuario antes de activar Pro.",
        )
    if current.get("plan") == "pro" and current.get("subscriptionStatus") in {
        "active",
        "cancel_pending",
        "past_due",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya tiene una suscripcion Pro vigente.",
        )

    result = activate_manual_subscription(email, plan_id, trial_limit)
    record_admin_audit(
        "manual_subscription_activated",
        email,
        {"planId": plan_id, "reason": reason or "admin_requested"},
    )
    return get_admin_user(email, trial_limit)


def block_user(email: str, trial_limit: int, reason: str | None = None):
    normalized_email = normalize_email(email)
    db = get_db()
    user_ref = get_user_ref(normalized_email)
    snapshot = user_ref.get()
    if not snapshot.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    data = snapshot.to_dict() or {}
    if data.get("status") == "blocked":
        return get_admin_user(normalized_email, trial_limit)

    email_hash = hash_email(normalized_email)
    user_ref.update({
        "previousStatus": data.get("status", "trial"),
        "status": "blocked",
        "blockedAt": SERVER_TIMESTAMP,
        "blockReason": (reason or "admin_requested").strip(),
        "updatedAt": SERVER_TIMESTAMP,
    })
    db.collection("blocked_users").document(email_hash).set({
        "emailHash": email_hash,
        "status": "blocked",
        "reason": (reason or "admin_requested").strip(),
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }, merge=True)
    record_admin_audit(
        "user_blocked",
        normalized_email,
        {"reason": reason or "admin_requested", "previousStatus": data.get("status", "trial")},
    )
    return get_admin_user(normalized_email, trial_limit)


def unblock_user(email: str, trial_limit: int, reason: str | None = None):
    normalized_email = normalize_email(email)
    db = get_db()
    user_ref = get_user_ref(normalized_email)
    snapshot = user_ref.get()
    if not snapshot.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    data = snapshot.to_dict() or {}
    subscription_status = data.get("subscriptionStatus")
    if data.get("plan") == "pro":
        restored_status = "active" if subscription_status in {"active", "cancel_pending", "past_due"} else (subscription_status or "expired")
    else:
        restored_status = "trial"

    user_ref.update({
        "status": restored_status,
        "previousStatus": None,
        "blockedAt": None,
        "blockReason": None,
        "updatedAt": SERVER_TIMESTAMP,
    })
    email_hash = hash_email(normalized_email)
    db.collection("blocked_users").document(email_hash).set({
        "status": "unblocked",
        "resolvedAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }, merge=True)
    record_admin_audit(
        "user_unblocked",
        normalized_email,
        {"reason": reason or "admin_requested", "newStatus": restored_status},
    )
    return get_admin_user(normalized_email, trial_limit)


def admin_cancel_user(email: str, trial_limit: int, reason: str | None = None):
    result = cancel_subscription(
        OfficeUser(email=normalize_email(email)),
        trial_limit,
        reason or "admin_requested",
    )
    record_admin_audit(
        "subscription_cancelled_by_admin",
        email,
        {"reason": reason or "admin_requested", "effectiveAt": result.get("currentPeriodEnd")},
    )
    return get_admin_user(email, trial_limit)


def admin_expire_user(email: str, trial_limit: int, reason: str | None = None):
    normalized_email = normalize_email(email)
    email_hash = hash_email(normalized_email)
    db = get_db()
    user_snapshot = get_user_ref(normalized_email).get()
    if not user_snapshot.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    user_data = user_snapshot.to_dict() or {}
    subscription_ref, subscription = _find_current_subscription(
        db,
        email_hash,
        user_data.get("subscriptionId"),
    )
    if not subscription_ref or not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suscripcion no encontrada.")

    _expire_subscription(
        db=db,
        subscription_ref=subscription_ref,
        subscription=subscription,
        trial_limit=trial_limit,
        reason=reason or "expired_by_admin",
    )
    record_admin_audit(
        "subscription_expired_by_admin",
        normalized_email,
        {"reason": reason or "expired_by_admin"},
    )
    return get_admin_user(normalized_email, trial_limit)
