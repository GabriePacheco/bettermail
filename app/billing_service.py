from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from app.firebase_service import get_db, get_or_create_mailbox_user
from app.models import OfficeUser
from app.payphone_service import (
    amount_to_cents,
    confirm_payphone_transaction,
    encrypt_card_holder,
    get_payphone_public_config,
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
):
    plan = _require_plan(plan_id)
    user = OfficeUser(email=email)
    user_ref, data = get_or_create_mailbox_user(user, trial_limit)
    db = get_db()

    now = _now_utc()
    period_end = now + timedelta(days=30)
    email_normalized = normalize_email(email)
    email_hash = hash_email(email_normalized)

    user_ref.update({
        "email": email_normalized,
        "plan": "pro",
        "status": "active",
        "subscriptionStatus": "active",
        "paymentProvider": provider,
        "planId": plan["id"],
        "providerSubscriptionId": provider_subscription_id,
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodStart": now,
        "currentPeriodEnd": period_end,
        "updatedAt": SERVER_TIMESTAMP,
    })

    subscription_id = uuid4().hex
    subscription_payload = {
        "subscriptionId": subscription_id,
        "email": email_normalized,
        "emailHash": email_hash,
        "plan": "pro",
        "planId": plan["id"],
        "status": "active",
        "provider": provider,
        "providerSubscriptionId": provider_subscription_id,
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodStart": now,
        "currentPeriodEnd": period_end,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }

    db.collection("subscriptions").document(subscription_id).set(subscription_payload)
    db.collection("billing_events").add({
        "event": event_name,
        "emailHash": email_hash,
        "plan": "pro",
        "planId": plan["id"],
        "provider": provider,
        "providerSubscriptionId": provider_subscription_id,
        "previousStatus": data.get("status", "trial"),
        "createdAt": SERVER_TIMESTAMP,
    })

    return {
        "plan": "pro",
        "status": "active",
        "subscriptionStatus": "active",
        "monthlyLimit": plan["monthlyLimit"],
        "monthlyUsed": 0,
        "currentPeriodEnd": period_end.isoformat(),
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
        })

    db.collection("billing_events").add({
        "event": "payphone_payment_approved",
        "emailHash": email_hash,
        "orderId": order.get("orderId"),
        "provider": "payphone_cajita",
        "payphoneTransactionId": transaction_id,
        "hasCardToken": bool(token),
        "createdAt": SERVER_TIMESTAMP,
    })

    return _activate_subscription(
        email=email,
        plan_id=order["planId"],
        trial_limit=trial_limit,
        provider="payphone_cajita",
        provider_subscription_id=str(transaction_id),
        event_name="payphone_subscription_activated",
    )


def get_billing_status(user: OfficeUser, trial_limit: int):
    _, data = get_or_create_mailbox_user(user, trial_limit)

    plan = data.get("plan", "trial")
    return {
        "plan": plan,
        "status": data.get("status", "trial"),
        "subscriptionStatus": data.get("subscriptionStatus"),
        "monthlyLimit": int(data.get("monthlyLimit", 0)),
        "monthlyUsed": int(data.get("monthlyUsed", 0)),
        "currentPeriodEnd": _iso(data.get("currentPeriodEnd")),
    }
