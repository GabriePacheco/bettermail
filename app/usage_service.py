import logging
from datetime import datetime, timezone

from google.cloud import firestore as google_firestore
from app.firebase_service import get_or_create_mailbox_user, register_usage


logger = logging.getLogger(__name__)


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _is_future(value):
    if not value:
        return False

    now = datetime.now(timezone.utc)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value > now

    return False


def _usage_response(
    *,
    allowed: bool,
    status: str,
    plan: str,
    used: int,
    limit: int,
    trial_used: int,
    trial_limit: int,
    monthly_used: int = 0,
    monthly_limit: int = 0,
    message: str | None = None,
    user_ref=None,
    usage_bucket: str | None = None,
    upgrade_required: bool = False,
):
    return {
        "allowed": allowed,
        "status": status,
        "plan": plan,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
        "trial_used": trial_used,
        "trial_limit": trial_limit,
        "monthlyUsed": monthly_used,
        "monthlyLimit": monthly_limit,
        "message": message,
        "user_ref": user_ref,
        "usage_bucket": usage_bucket,
        "upgradeRequired": upgrade_required,
    }


def check_usage_allowed(user, trial_limit: int):
    user_ref, data = get_or_create_mailbox_user(user, trial_limit)

    trial_used = _as_int(data.get("trialUsed", 0))
    actual_trial_limit = _as_int(data.get("trialLimit", trial_limit), trial_limit)
    user_status = data.get("status", "trial")
    plan = data.get("plan", "trial")
    subscription_status = data.get("subscriptionStatus")
    monthly_used = _as_int(data.get("monthlyUsed", 0))
    monthly_limit = _as_int(data.get("monthlyLimit", 0))
    current_period_end = data.get("currentPeriodEnd")
    grace_period_end = data.get("gracePeriodEnd")
    payment_action_required = bool(data.get("paymentActionRequired", False))

    if user_status == "blocked":
        return _usage_response(
            allowed=False,
            status="blocked",
            plan=plan,
            used=monthly_used if plan == "pro" else trial_used,
            limit=monthly_limit if plan == "pro" else actual_trial_limit,
            trial_used=trial_used,
            trial_limit=actual_trial_limit,
            monthly_used=monthly_used,
            monthly_limit=monthly_limit,
            message="Usuario bloqueado.",
            upgrade_required=True,
        )

    if plan == "pro":
        subscription_is_usable = (
            subscription_status in {"active", "cancel_pending"}
            and _is_future(current_period_end)
        ) or (
            subscription_status == "past_due"
            and _is_future(grace_period_end)
        )

        if not subscription_is_usable:
            return _usage_response(
                allowed=False,
                status="subscription_expired",
                plan="pro",
                used=monthly_used,
                limit=monthly_limit,
                trial_used=trial_used,
                trial_limit=actual_trial_limit,
                monthly_used=monthly_used,
                monthly_limit=monthly_limit,
                message=(
                    "No pudimos renovar tu plan. Actualiza el pago para continuar."
                    if payment_action_required
                    else "La suscripcion Pro no esta vigente."
                ),
                upgrade_required=True,
            )

        if monthly_used >= monthly_limit:
            return _usage_response(
                allowed=False,
                status="active",
                plan="pro",
                used=monthly_used,
                limit=monthly_limit,
                trial_used=trial_used,
                trial_limit=actual_trial_limit,
                monthly_used=monthly_used,
                monthly_limit=monthly_limit,
                message="Has usado todas tus mejoras del mes.",
                upgrade_required=True,
            )

        return _usage_response(
            allowed=True,
            status="active",
            plan="pro",
            used=monthly_used,
            limit=monthly_limit,
            trial_used=trial_used,
            trial_limit=actual_trial_limit,
            monthly_used=monthly_used,
            monthly_limit=monthly_limit,
            user_ref=user_ref,
            usage_bucket="monthly",
        )

    if user_status == "trial" and trial_used >= actual_trial_limit:
        return _usage_response(
            allowed=False,
            status="trial_expired",
            plan="trial",
            used=trial_used,
            limit=actual_trial_limit,
            trial_used=trial_used,
            trial_limit=actual_trial_limit,
            monthly_used=monthly_used,
            monthly_limit=monthly_limit,
            message="Has usado todas tus mejoras gratuitas.",
            upgrade_required=True,
        )

    return _usage_response(
        allowed=True,
        status=user_status,
        plan="trial",
        used=trial_used,
        limit=actual_trial_limit,
        trial_used=trial_used,
        trial_limit=actual_trial_limit,
        monthly_used=monthly_used,
        monthly_limit=monthly_limit,
        user_ref=user_ref,
        usage_bucket="trial",
    )


def consume_rewrite_credit(user, usage_info: dict, metadata: dict):
    user_ref = usage_info["user_ref"]
    usage_bucket = usage_info.get("usage_bucket", "trial")

    if usage_bucket == "monthly":
        user_ref.update({
            "monthlyUsed": google_firestore.Increment(1)
        })
    else:
        user_ref.update({
            "trialUsed": google_firestore.Increment(1)
        })

    try:
        register_usage(user.email, {
            **metadata,
            "plan": usage_info.get("plan", "trial"),
            "usageBucket": usage_bucket,
        })
    except Exception:
        logger.exception("Rewrite usage telemetry failed")

    used_after = usage_info["used"] + 1
    remaining_after = max(usage_info["limit"] - used_after, 0)
    trial_used_after = usage_info["trial_used"] + (1 if usage_bucket == "trial" else 0)
    monthly_used_after = usage_info["monthlyUsed"] + (1 if usage_bucket == "monthly" else 0)

    return {
        "used": used_after,
        "remaining": remaining_after,
        "trial_used": trial_used_after,
        "monthlyUsed": monthly_used_after,
    }
