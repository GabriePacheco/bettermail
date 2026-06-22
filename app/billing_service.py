from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase_service import get_db, get_or_create_mailbox_user
from app.config import get_settings
from app.models import OfficeUser
from app.payphone_service import (
    amount_to_cents,
    build_token_charge_payload,
    charge_payphone_card_token,
    confirm_payphone_transaction,
    encrypt_card_holder,
    get_payphone_public_config,
    is_payphone_charge_approved,
    is_payphone_configured,
)
from app.plans_service import get_plan
from app.security import hash_email, normalize_email


def _now_utc():
    return datetime.now(timezone.utc)


def _iso(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _as_utc(value):
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_due(value, now=None):
    timestamp = _as_utc(value)
    return bool(timestamp and timestamp <= (now or _now_utc()))


def _subscription_sort_key(data):
    return _as_utc(data.get("currentPeriodEnd")) or datetime.min.replace(tzinfo=timezone.utc)


def _find_current_subscription(db, email_hash: str, subscription_id: str | None = None):
    if subscription_id:
        snapshot = db.collection("subscriptions").document(subscription_id).get()
        if snapshot.exists:
            return snapshot.reference, snapshot.to_dict() or {}

    snapshots = db.collection("subscriptions").where("emailHash", "==", email_hash).stream()
    candidates = []
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        if data.get("status") == "replaced":
            continue
        candidates.append((snapshot.reference, data))

    if not candidates:
        return None, None

    return max(candidates, key=lambda item: _subscription_sort_key(item[1]))


def _billing_event(db, event: str, email_hash: str, **payload):
    db.collection("billing_events").add({
        "event": event,
        "emailHash": email_hash,
        **payload,
        "createdAt": SERVER_TIMESTAMP,
    })


def _require_plan(plan_id: str):
    plan = get_plan(plan_id)

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan no disponible.",
        )

    return plan


def _new_client_transaction_id():
    return uuid4().hex[:15]


def create_checkout_order(user: OfficeUser, plan_id: str, provider: str, source: str):
    if provider not in {"manual", "payphone_cajita"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proveedor de pago no soportado.",
        )

    plan = _require_plan(plan_id)
    db = get_db()
    order_id = uuid4().hex
    email = normalize_email(user.email)
    amount = amount_to_cents(plan["price"])
    client_transaction_id = _new_client_transaction_id()
    payphone_config = get_payphone_public_config() if provider == "payphone_cajita" else None
    payment_unavailable_reason = None

    if provider == "payphone_cajita" and not is_payphone_configured():
        payment_unavailable_reason = "payphone_not_configured"

    db.collection("payment_orders").document(order_id).set({
        "orderId": order_id,
        "email": email,
        "emailHash": hash_email(email),
        "displayName": user.display_name,
        "accountType": user.account_type,
        "timeZone": user.time_zone,
        "planId": plan["id"],
        "provider": provider,
        "source": source,
        "amount": plan["price"],
        "amountCents": amount,
        "currency": plan["currency"],
        "clientTransactionId": client_transaction_id,
        "paymentUnavailableReason": payment_unavailable_reason,
        "status": "pending",
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    })

    response = {
        "checkout_url": f"/static/pricing.html?order_id={order_id}",
        "order_id": order_id,
        "status": "pending",
        "provider": provider,
        "plan": plan,
        "payment_unavailable_reason": payment_unavailable_reason,
    }

    if provider == "payphone_cajita" and payphone_config:
        response.update({
            "payphone_token": payphone_config["token"],
            "payphone_client_transaction_id": client_transaction_id,
            "payphone_amount": amount,
            "payphone_amount_without_tax": amount,
            "payphone_currency": plan["currency"],
            "payphone_reference": "BetterMail Pro mensual",
            "payphone_default_method": "card",
        })
        if payphone_config["store_id"]:
            response["payphone_store_id"] = payphone_config["store_id"]

    return response


def get_checkout_order(order_id: str):
    db = get_db()
    snapshot = db.collection("payment_orders").document(order_id).get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden de pago no encontrada.",
        )

    data = snapshot.to_dict() or {}
    plan = _require_plan(data.get("planId", ""))
    provider = data.get("provider", "manual")
    payphone_config = get_payphone_public_config() if provider == "payphone_cajita" else None

    response = {
        "checkout_url": f"/static/pricing.html?order_id={order_id}",
        "order_id": order_id,
        "status": data.get("status", "pending"),
        "provider": provider,
        "payment_unavailable_reason": data.get(
            "paymentUnavailableReason",
            "payment_provider_pending" if provider == "manual" else None,
        ),
        "plan": plan,
        "email": data.get("email"),
        "source": data.get("source"),
    }

    if provider == "payphone_cajita" and payphone_config:
        response.update({
            "payphone_token": payphone_config["token"],
            "payphone_client_transaction_id": data.get("clientTransactionId"),
            "payphone_amount": int(data.get("amountCents", amount_to_cents(plan["price"]))),
            "payphone_amount_without_tax": int(
                data.get("amountWithoutTaxCents", data.get("amountCents", amount_to_cents(plan["price"])))
            ),
            "payphone_currency": data.get("currency", plan["currency"]),
            "payphone_reference": "BetterMail Pro mensual",
            "payphone_default_method": "card",
        })
        if payphone_config["store_id"]:
            response["payphone_store_id"] = payphone_config["store_id"]

    return response


def _activate_subscription(
    *,
    email: str,
    plan_id: str,
    trial_limit: int,
    provider: str,
    provider_subscription_id: str | None = None,
    event_name: str,
    auto_renew: bool = False,
):
    plan = _require_plan(plan_id)
    user = OfficeUser(email=email)
    user_ref, data = get_or_create_mailbox_user(user, trial_limit)
    db = get_db()

    now = _now_utc()
    period_end = now + timedelta(days=30)
    email_normalized = normalize_email(email)
    email_hash = hash_email(email_normalized)

    subscription_id = f"sub_{email_hash}"

    for snapshot in db.collection("subscriptions").where("emailHash", "==", email_hash).stream():
        if snapshot.id != subscription_id:
            snapshot.reference.update({
                "status": "replaced",
                "replacedBy": subscription_id,
                "updatedAt": SERVER_TIMESTAMP,
            })

    user_ref.update({
        "email": email_normalized,
        "plan": "pro",
        "status": "active",
        "subscriptionStatus": "active",
        "subscriptionId": subscription_id,
        "paymentProvider": provider,
        "planId": plan["id"],
        "providerSubscriptionId": provider_subscription_id,
        "autoRenew": auto_renew,
        "cancelAtPeriodEnd": False,
        "paymentActionRequired": False,
        "renewalFailureCount": 0,
        "gracePeriodEnd": None,
        "nextRenewalAttemptAt": None,
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodStart": now,
        "currentPeriodEnd": period_end,
        "updatedAt": SERVER_TIMESTAMP,
    })

    subscription_payload = {
        "subscriptionId": subscription_id,
        "email": email_normalized,
        "emailHash": email_hash,
        "plan": "pro",
        "planId": plan["id"],
        "status": "active",
        "provider": provider,
        "providerSubscriptionId": provider_subscription_id,
        "lastProviderTransactionId": provider_subscription_id,
        "autoRenew": auto_renew,
        "cancelAtPeriodEnd": False,
        "paymentActionRequired": False,
        "renewalFailureCount": 0,
        "gracePeriodEnd": None,
        "nextRenewalAttemptAt": None,
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodStart": now,
        "currentPeriodEnd": period_end,
        "activatedAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }

    db.collection("subscriptions").document(subscription_id).set(
        subscription_payload,
        merge=True,
    )
    _billing_event(
        db,
        event_name,
        email_hash,
        plan="pro",
        planId=plan["id"],
        provider=provider,
        providerSubscriptionId=provider_subscription_id,
        previousStatus=data.get("status", "trial"),
    )

    return {
        "plan": "pro",
        "status": "active",
        "subscriptionStatus": "active",
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodEnd": period_end.isoformat(),
        "cancelAtPeriodEnd": False,
        "autoRenew": auto_renew,
        "paymentActionRequired": False,
        "renewalFailureCount": 0,
    }


def activate_manual_subscription(email: str, plan_id: str, trial_limit: int):
    return _activate_subscription(
        email=email,
        plan_id=plan_id,
        trial_limit=trial_limit,
        provider="manual",
        event_name="manual_subscription_activated",
    )


def confirm_payphone_subscription(
    *,
    transaction_id: int,
    client_transaction_id: str,
    card_token: str | None,
    trial_limit: int,
):
    db = get_db()
    orders = (
        db.collection("payment_orders")
        .where("clientTransactionId", "==", client_transaction_id)
        .limit(1)
        .stream()
    )
    order_snapshot = next(orders, None)

    if not order_snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden PayPhone no encontrada.",
        )

    order_ref = order_snapshot.reference
    order = order_snapshot.to_dict() or {}

    if order.get("provider") != "payphone_cajita":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La orden no pertenece a PayPhone.",
        )

    if order.get("status") == "completed":
        return get_billing_status(OfficeUser(email=order["email"]), trial_limit)

    confirmation = confirm_payphone_transaction(transaction_id, client_transaction_id)
    status_code = int(confirmation.get("statusCode") or 0)
    transaction_status = confirmation.get("transactionStatus")

    if status_code != 3 or transaction_status != "Approved":
        order_ref.update({
            "status": "failed",
            "payphoneStatusCode": status_code,
            "payphoneTransactionStatus": transaction_status,
            "payphoneResponse": confirmation,
            "updatedAt": SERVER_TIMESTAMP,
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pago PayPhone no aprobado: {transaction_status or status_code}",
        )

    expected_amount = int(order.get("amountCents", 0))
    confirmed_amount = int(confirmation.get("amount") or 0)

    if expected_amount and confirmed_amount != expected_amount:
        order_ref.update({
            "status": "amount_mismatch",
            "payphoneResponse": confirmation,
            "updatedAt": SERVER_TIMESTAMP,
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El monto confirmado por PayPhone no coincide con la orden.",
        )

    token = card_token or confirmation.get("cardToken") or confirmation.get("ctoken")
    card_holder_name = confirmation.get("optionalParameter4")
    encrypted_card_holder = encrypt_card_holder(card_holder_name)

    order_ref.update({
        "status": "completed",
        "payphoneTransactionId": transaction_id,
        "payphoneStatusCode": status_code,
        "payphoneTransactionStatus": transaction_status,
        "payphoneAuthorizationCode": confirmation.get("authorizationCode"),
        "payphoneResponse": confirmation,
        "completedAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    })

    email = normalize_email(order["email"])
    email_hash = hash_email(email)

    if token:
        db.collection("payment_methods").document(f"payphone_{email_hash}").set({
            "email": email,
            "emailHash": email_hash,
            "provider": "payphone_cajita",
            "cardToken": token,
            "cardHolder": encrypted_card_holder,
            "cardHolderNameStored": bool(encrypted_card_holder),
            "documentId": confirmation.get("document"),
            "phoneNumber": confirmation.get("phoneNumber"),
            "cardType": confirmation.get("cardType"),
            "cardBrand": confirmation.get("cardBrand"),
            "bin": confirmation.get("bin"),
            "lastDigits": confirmation.get("lastDigits"),
            "createdAt": SERVER_TIMESTAMP,
            "updatedAt": SERVER_TIMESTAMP,
        }, merge=True)

    _billing_event(
        db,
        "payphone_payment_approved",
        email_hash,
        orderId=order.get("orderId"),
        provider="payphone_cajita",
        payphoneTransactionId=transaction_id,
        hasCardToken=bool(token),
    )

    return _activate_subscription(
        email=email,
        plan_id=order["planId"],
        trial_limit=trial_limit,
        provider="payphone_cajita",
        provider_subscription_id=str(transaction_id),
        event_name="payphone_subscription_activated",
        auto_renew=bool(token),
    )


def _expire_subscription(
    *,
    db,
    subscription_ref,
    subscription: dict,
    trial_limit: int,
    reason: str,
    final_status: str = "expired",
):
    email = normalize_email(subscription["email"])
    email_hash = subscription.get("emailHash") or hash_email(email)
    user_ref, user_data = get_or_create_mailbox_user(OfficeUser(email=email), trial_limit)
    now = _now_utc()

    subscription_ref.update({
        "status": final_status,
        "autoRenew": False,
        "cancelAtPeriodEnd": False,
        "paymentActionRequired": final_status != "cancelled",
        "expiredAt": now,
        "expirationReason": reason,
        "updatedAt": SERVER_TIMESTAMP,
    })
    user_ref.update({
        "plan": "pro",
        "status": "blocked" if user_data.get("status") == "blocked" else final_status,
        "subscriptionStatus": final_status,
        "autoRenew": False,
        "cancelAtPeriodEnd": False,
        "paymentActionRequired": final_status != "cancelled",
        "updatedAt": SERVER_TIMESTAMP,
    })
    _billing_event(
        db,
        f"subscription_{final_status}",
        email_hash,
        subscriptionId=subscription.get("subscriptionId") or subscription_ref.id,
        reason=reason,
    )


def _reconcile_subscription(db, user_ref, user_data: dict, trial_limit: int):
    if user_data.get("plan") != "pro":
        return user_data

    email = normalize_email(user_data.get("email", ""))
    if not email:
        return user_data

    email_hash = hash_email(email)
    subscription_ref, subscription = _find_current_subscription(
        db,
        email_hash,
        user_data.get("subscriptionId"),
    )
    if not subscription_ref or not subscription:
        return user_data

    if "autoRenew" not in subscription and subscription.get("provider") == "payphone_cajita":
        payment_snapshot = (
            db.collection("payment_methods")
            .document(f"payphone_{email_hash}")
            .get()
        )
        payment_data = payment_snapshot.to_dict() if payment_snapshot.exists else {}
        legacy_auto_renew = bool(payment_data.get("cardToken"))
        subscription_ref.update({
            "autoRenew": legacy_auto_renew,
            "updatedAt": SERVER_TIMESTAMP,
        })
        user_ref.update({
            "autoRenew": legacy_auto_renew,
            "updatedAt": SERVER_TIMESTAMP,
        })
        subscription["autoRenew"] = legacy_auto_renew
        user_data["autoRenew"] = legacy_auto_renew

    now = _now_utc()
    period_end = subscription.get("currentPeriodEnd") or user_data.get("currentPeriodEnd")
    subscription_status = subscription.get("status", user_data.get("subscriptionStatus"))

    if subscription.get("cancelAtPeriodEnd") and _is_due(period_end, now):
        _expire_subscription(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="cancelled_at_period_end",
            final_status="cancelled",
        )
    elif subscription_status == "past_due" and _is_due(subscription.get("gracePeriodEnd"), now):
        _expire_subscription(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="payment_grace_period_ended",
        )
    elif subscription_status == "active" and _is_due(period_end, now):
        if subscription.get("autoRenew"):
            grace_end = now + timedelta(days=max(get_settings().billing_grace_days, 0))
            update = {
                "status": "past_due",
                "paymentActionRequired": True,
                "gracePeriodEnd": grace_end,
                "nextRenewalAttemptAt": now,
                "updatedAt": SERVER_TIMESTAMP,
            }
            subscription_ref.update(update)
            user_ref.update({
                "status": "active",
                "subscriptionStatus": "past_due",
                "paymentActionRequired": True,
                "gracePeriodEnd": grace_end,
                "nextRenewalAttemptAt": now,
                "updatedAt": SERVER_TIMESTAMP,
            })
        else:
            _expire_subscription(
                db=db,
                subscription_ref=subscription_ref,
                subscription=subscription,
                trial_limit=trial_limit,
                reason="manual_renewal_required",
            )

    refreshed = user_ref.get()
    return refreshed.to_dict() or user_data


def _status_payload(data: dict):
    plan = data.get("plan", "trial")
    return {
        "plan": plan,
        "status": data.get("status", "trial"),
        "subscriptionStatus": data.get("subscriptionStatus"),
        "monthlyLimit": int(data.get("monthlyLimit", 0)),
        "monthlyUsed": int(data.get("monthlyUsed", 0)),
        "currentPeriodEnd": _iso(data.get("currentPeriodEnd")),
        "gracePeriodEnd": _iso(data.get("gracePeriodEnd")),
        "nextRenewalAttemptAt": _iso(data.get("nextRenewalAttemptAt")),
        "cancelAtPeriodEnd": bool(data.get("cancelAtPeriodEnd", False)),
        "autoRenew": bool(data.get("autoRenew", False)),
        "paymentActionRequired": bool(data.get("paymentActionRequired", False)),
        "renewalFailureCount": int(data.get("renewalFailureCount", 0)),
    }


def get_billing_status(user: OfficeUser, trial_limit: int):
    user_ref, data = get_or_create_mailbox_user(user, trial_limit)
    data = _reconcile_subscription(get_db(), user_ref, data, trial_limit)
    return _status_payload(data)


def cancel_subscription(user: OfficeUser, trial_limit: int, reason: str | None = None):
    db = get_db()
    user_ref, user_data = get_or_create_mailbox_user(user, trial_limit)
    email = normalize_email(user.email)
    email_hash = hash_email(email)
    subscription_ref, subscription = _find_current_subscription(
        db,
        email_hash,
        user_data.get("subscriptionId"),
    )

    if not subscription_ref or not subscription or subscription.get("status") not in {
        "active",
        "past_due",
        "cancel_pending",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay una suscripcion activa para cancelar.",
        )

    period_end = subscription.get("currentPeriodEnd")
    if _is_due(period_end):
        _expire_subscription(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="cancelled_after_period_end",
            final_status="cancelled",
        )
        return get_billing_status(user, trial_limit)

    update = {
        "status": "cancel_pending",
        "cancelAtPeriodEnd": True,
        "autoRenew": False,
        "cancellationReason": (reason or "user_requested").strip(),
        "cancelRequestedAt": SERVER_TIMESTAMP,
        "paymentActionRequired": False,
        "updatedAt": SERVER_TIMESTAMP,
    }
    subscription_ref.update(update)
    user_ref.update({
        "status": "blocked" if user_data.get("status") == "blocked" else "active",
        "subscriptionStatus": "cancel_pending",
        "cancelAtPeriodEnd": True,
        "autoRenew": False,
        "paymentActionRequired": False,
        "updatedAt": SERVER_TIMESTAMP,
    })
    _billing_event(
        db,
        "subscription_cancellation_requested",
        email_hash,
        subscriptionId=subscription.get("subscriptionId") or subscription_ref.id,
        effectiveAt=_iso(period_end),
    )
    return get_billing_status(user, trial_limit)


def reactivate_subscription(user: OfficeUser, trial_limit: int):
    db = get_db()
    user_ref, user_data = get_or_create_mailbox_user(user, trial_limit)
    email = normalize_email(user.email)
    email_hash = hash_email(email)
    subscription_ref, subscription = _find_current_subscription(
        db,
        email_hash,
        user_data.get("subscriptionId"),
    )

    if not subscription_ref or not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suscripcion no encontrada.",
        )
    if _is_due(subscription.get("currentPeriodEnd")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La suscripcion ya termino. Inicia una compra nueva.",
        )

    payment_method = db.collection("payment_methods").document(f"payphone_{email_hash}").get()
    payment_data = payment_method.to_dict() if payment_method.exists else {}
    if not payment_data.get("cardToken"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe un metodo de pago reutilizable. Inicia una compra nueva.",
        )

    subscription_ref.update({
        "status": "active",
        "cancelAtPeriodEnd": False,
        "autoRenew": True,
        "cancellationReason": None,
        "cancelRequestedAt": None,
        "paymentActionRequired": False,
        "updatedAt": SERVER_TIMESTAMP,
    })
    user_ref.update({
        "status": "blocked" if user_data.get("status") == "blocked" else "active",
        "subscriptionStatus": "active",
        "cancelAtPeriodEnd": False,
        "autoRenew": True,
        "paymentActionRequired": False,
        "updatedAt": SERVER_TIMESTAMP,
    })
    _billing_event(
        db,
        "subscription_reactivated",
        email_hash,
        subscriptionId=subscription.get("subscriptionId") or subscription_ref.id,
    )
    return get_billing_status(user, trial_limit)


def _record_renewal_failure(
    *,
    db,
    subscription_ref,
    subscription: dict,
    trial_limit: int,
    reason: str,
    status_code: int | None = None,
    transaction_status: str | None = None,
):
    settings = get_settings()
    now = _now_utc()
    failures = int(subscription.get("renewalFailureCount", 0)) + 1
    max_attempts = max(settings.billing_max_renewal_attempts, 1)
    grace_end = _as_utc(subscription.get("gracePeriodEnd")) or (
        now + timedelta(days=max(settings.billing_grace_days, 0))
    )
    email = normalize_email(subscription["email"])
    email_hash = subscription.get("emailHash") or hash_email(email)

    if failures >= max_attempts or grace_end <= now:
        subscription["renewalFailureCount"] = failures
        _expire_subscription(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="renewal_failed",
        )
        return "expired"

    next_attempt = now + timedelta(days=1)
    user_ref, user_data = get_or_create_mailbox_user(OfficeUser(email=email), trial_limit)
    update = {
        "status": "past_due",
        "renewalFailureCount": failures,
        "paymentActionRequired": True,
        "lastRenewalFailure": reason,
        "lastPayphoneStatusCode": status_code,
        "lastPayphoneTransactionStatus": transaction_status,
        "gracePeriodEnd": grace_end,
        "nextRenewalAttemptAt": next_attempt,
        "updatedAt": SERVER_TIMESTAMP,
    }
    subscription_ref.update(update)
    user_ref.update({
        "status": "blocked" if user_data.get("status") == "blocked" else "active",
        "subscriptionStatus": "past_due",
        "renewalFailureCount": failures,
        "paymentActionRequired": True,
        "gracePeriodEnd": grace_end,
        "nextRenewalAttemptAt": next_attempt,
        "updatedAt": SERVER_TIMESTAMP,
    })
    _billing_event(
        db,
        "subscription_renewal_failed",
        email_hash,
        subscriptionId=subscription.get("subscriptionId") or subscription_ref.id,
        reason=reason,
        attempt=failures,
        payphoneStatusCode=status_code,
        payphoneTransactionStatus=transaction_status,
    )
    return "past_due"


def _renew_payphone_subscription(db, subscription_ref, subscription: dict, trial_limit: int):
    email = normalize_email(subscription["email"])
    email_hash = subscription.get("emailHash") or hash_email(email)
    payment_ref = db.collection("payment_methods").document(f"payphone_{email_hash}")
    payment_snapshot = payment_ref.get()
    payment = payment_snapshot.to_dict() if payment_snapshot.exists else {}

    required = (
        payment.get("cardToken"),
        payment.get("cardHolder"),
        payment.get("documentId"),
        payment.get("phoneNumber"),
    )
    if not all(required):
        return _record_renewal_failure(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="payment_method_incomplete",
        )

    plan = _require_plan(subscription["planId"])
    failure_count = int(subscription.get("renewalFailureCount", 0))
    period_end = _as_utc(subscription.get("currentPeriodEnd")) or _now_utc()
    period_key = period_end.strftime("%Y%m%d%H%M%S")
    attempt_id = f"{subscription_ref.id}_{period_key}_{failure_count + 1}"
    attempt_ref = db.collection("renewal_attempts").document(attempt_id)
    attempt_snapshot = attempt_ref.get()
    attempt = attempt_snapshot.to_dict() if attempt_snapshot.exists else {}

    if attempt.get("status") == "approved":
        return "skipped"
    if attempt.get("status") == "processing" and not _is_due(attempt.get("processingExpiresAt")):
        return "skipped"

    client_transaction_id = attempt.get("clientTransactionId") or _new_client_transaction_id()
    attempt_ref.set({
        "attemptId": attempt_id,
        "subscriptionId": subscription.get("subscriptionId") or subscription_ref.id,
        "emailHash": email_hash,
        "clientTransactionId": client_transaction_id,
        "status": "processing",
        "processingExpiresAt": _now_utc() + timedelta(minutes=10),
        "attempt": failure_count + 1,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }, merge=True)

    payload = build_token_charge_payload(
        card_token=payment["cardToken"],
        card_holder=None,
        encrypted_card_holder=payment["cardHolder"],
        document_id=payment["documentId"],
        phone_number=payment["phoneNumber"],
        email=email,
        amount=amount_to_cents(plan["price"]),
        client_transaction_id=client_transaction_id,
        reference="Renovacion BetterMail Pro mensual",
    )

    try:
        response = charge_payphone_card_token(payload)
    except HTTPException as exc:
        attempt_ref.update({
            "status": "error",
            "errorCategory": "provider_unavailable",
            "processingExpiresAt": None,
            "updatedAt": SERVER_TIMESTAMP,
        })
        return _record_renewal_failure(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason=f"provider_error_{exc.status_code}",
        )

    status_code = int(response.get("statusCode") or 0)
    transaction_status = str(response.get("transactionStatus") or "")
    if not is_payphone_charge_approved(response):
        attempt_ref.update({
            "status": "declined",
            "payphoneStatusCode": status_code,
            "payphoneTransactionStatus": transaction_status,
            "processingExpiresAt": None,
            "updatedAt": SERVER_TIMESTAMP,
        })
        return _record_renewal_failure(
            db=db,
            subscription_ref=subscription_ref,
            subscription=subscription,
            trial_limit=trial_limit,
            reason="payment_declined",
            status_code=status_code,
            transaction_status=transaction_status,
        )

    now = _now_utc()
    next_period_end = now + timedelta(days=30)
    transaction_id = response.get("transactionId") or response.get("id")
    renewal_update = {
        "status": "active",
        "currentPeriodStart": now,
        "currentPeriodEnd": next_period_end,
        "monthlyUsed": 0,
        "renewalFailureCount": 0,
        "paymentActionRequired": False,
        "gracePeriodEnd": None,
        "nextRenewalAttemptAt": None,
        "lastRenewedAt": now,
        "lastProviderTransactionId": str(transaction_id or ""),
        "updatedAt": SERVER_TIMESTAMP,
    }
    subscription_ref.update(renewal_update)
    user_ref, user_data = get_or_create_mailbox_user(OfficeUser(email=email), trial_limit)
    user_ref.update({
        "plan": "pro",
        "status": "blocked" if user_data.get("status") == "blocked" else "active",
        "subscriptionStatus": "active",
        "currentPeriodStart": now,
        "currentPeriodEnd": next_period_end,
        "monthlyUsed": 0,
        "renewalFailureCount": 0,
        "paymentActionRequired": False,
        "gracePeriodEnd": None,
        "nextRenewalAttemptAt": None,
        "updatedAt": SERVER_TIMESTAMP,
    })
    payment_ref.update({
        "lastChargedAt": now,
        "lastChargeStatus": "approved",
        "updatedAt": SERVER_TIMESTAMP,
    })
    attempt_ref.update({
        "status": "approved",
        "payphoneStatusCode": status_code,
        "payphoneTransactionStatus": transaction_status,
        "payphoneTransactionId": transaction_id,
        "completedAt": SERVER_TIMESTAMP,
        "processingExpiresAt": None,
        "updatedAt": SERVER_TIMESTAMP,
    })
    _billing_event(
        db,
        "subscription_renewed",
        email_hash,
        subscriptionId=subscription.get("subscriptionId") or subscription_ref.id,
        payphoneTransactionId=transaction_id,
        currentPeriodEnd=next_period_end.isoformat(),
    )
    return "renewed"


def process_due_subscriptions(*, trial_limit: int, limit: int = 100, dry_run: bool = False):
    settings = get_settings()
    db = get_db()
    now = _now_utc()
    snapshots = list(db.collection("subscriptions").stream())
    current_by_email = {}

    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        if data.get("status") not in {"active", "past_due", "cancel_pending"}:
            continue
        email_hash = data.get("emailHash")
        if not email_hash:
            continue
        existing = current_by_email.get(email_hash)
        if not existing or _subscription_sort_key(data) > _subscription_sort_key(existing[1]):
            current_by_email[email_hash] = (snapshot.reference, data)

    result = {
        "scanned": len(snapshots),
        "due": 0,
        "renewed": 0,
        "past_due": 0,
        "expired": 0,
        "cancelled": 0,
        "skipped": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    for subscription_ref, subscription in list(current_by_email.values())[:limit]:
        status_value = subscription.get("status")
        period_due = _is_due(subscription.get("currentPeriodEnd"), now)
        retry_due = status_value == "past_due" and (
            not subscription.get("nextRenewalAttemptAt")
            or _is_due(subscription.get("nextRenewalAttemptAt"), now)
        )

        if not period_due and not retry_due:
            result["skipped"] += 1
            continue

        result["due"] += 1
        if dry_run:
            continue

        try:
            if subscription.get("cancelAtPeriodEnd") or status_value == "cancel_pending":
                _expire_subscription(
                    db=db,
                    subscription_ref=subscription_ref,
                    subscription=subscription,
                    trial_limit=trial_limit,
                    reason="cancelled_at_period_end",
                    final_status="cancelled",
                )
                result["cancelled"] += 1
                continue

            if status_value == "past_due" and _is_due(subscription.get("gracePeriodEnd"), now):
                _expire_subscription(
                    db=db,
                    subscription_ref=subscription_ref,
                    subscription=subscription,
                    trial_limit=trial_limit,
                    reason="payment_grace_period_ended",
                )
                result["expired"] += 1
                continue

            if not subscription.get("autoRenew"):
                _expire_subscription(
                    db=db,
                    subscription_ref=subscription_ref,
                    subscription=subscription,
                    trial_limit=trial_limit,
                    reason="manual_renewal_required",
                )
                result["expired"] += 1
                continue

            recurring_configured = (
                settings.payphone_recurring_enabled
                and bool(settings.payphone_token.strip())
                and bool(settings.payphone_store_id.strip())
                and bool(settings.payphone_coding_password.strip())
            )
            if not recurring_configured:
                result["skipped"] += 1
                continue

            outcome = _renew_payphone_subscription(
                db,
                subscription_ref,
                subscription,
                trial_limit,
            )
            if outcome in result:
                result[outcome] += 1
            else:
                result["skipped"] += 1
        except Exception:
            result["errors"] += 1

    return result
