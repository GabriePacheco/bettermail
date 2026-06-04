from fastapi import HTTPException, status
from google.cloud import firestore as google_firestore
from app.firebase_service import get_or_create_mailbox_user, register_usage


def check_usage_allowed(user, trial_limit: int):
    user_ref, data = get_or_create_mailbox_user(user, trial_limit)

    trial_used = int(data.get("trialUsed", 0))
    actual_trial_limit = int(data.get("trialLimit", trial_limit))
    user_status = data.get("status", "trial")

    if user_status == "blocked":
        return {
            "allowed": False,
            "status": "blocked",
            "trial_used": trial_used,
            "trial_limit": actual_trial_limit,
            "remaining": 0,
            "message": "Usuario bloqueado.",
        }

    if user_status == "trial" and trial_used >= actual_trial_limit:
        return {
            "allowed": False,
            "status": "trial_expired",
            "trial_used": trial_used,
            "trial_limit": actual_trial_limit,
            "remaining": 0,
            "message": "Has usado todas tus mejoras gratuitas.",
        }

    return {
        "allowed": True,
        "status": user_status,
        "trial_used": trial_used,
        "trial_limit": actual_trial_limit,
        "remaining": actual_trial_limit - trial_used,
        "user_ref": user_ref,
    }


def consume_rewrite_credit(user, usage_info: dict, metadata: dict):
    user_ref = usage_info["user_ref"]

    user_ref.update({
        "trialUsed": google_firestore.Increment(1)
    })

    register_usage(user.email, metadata)

    trial_used_after = usage_info["trial_used"] + 1
    remaining_after = max(usage_info["trial_limit"] - trial_used_after, 0)

    return {
        "trial_used": trial_used_after,
        "remaining": remaining_after,
    }