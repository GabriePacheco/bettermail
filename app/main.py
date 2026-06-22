from fastapi import FastAPI, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models import (
    AdminActionRequest,
    AdminActivateRequest,
    AdminUserRequest,
    AdminUserResponse,
    BillingStatusRequest,
    BillingStatusResponse,
    CheckoutDetailsResponse,
    CheckoutRequest,
    CheckoutResponse,
    OfficeUser,
    PayphoneConfirmRequest,
    PlanResponse,
    RenewalJobRequest,
    RenewalJobResponse,
    RewriteRequest,
    RewriteResponse,
    SubscriptionActionRequest,
    UsageStatusResponse,
)
from app.admin_service import (
    admin_activate_user,
    admin_cancel_user,
    admin_expire_user,
    block_user,
    get_admin_user,
    unblock_user,
)
from app.security import verify_admin_secret, verify_app_secret, verify_internal_job_secret
from app.usage_service import check_usage_allowed, consume_rewrite_credit
from app.openai_service import rewrite_email_text
from app.billing_service import (
    cancel_subscription,
    confirm_payphone_subscription,
    create_checkout_order,
    get_billing_status,
    get_checkout_order,
    process_due_subscriptions,
    reactivate_subscription,
)
from app.plans_service import list_plans

import socket
import os

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="BetterMail AI API",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.app_env == "development" else None,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Content-Type",
        "X-App-Secret",
        "x-app-secret",
        "X-Admin-Secret",
        "X-Internal-Job-Secret",
    ],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


if settings.app_env == "development":
    @app.get("/debug/env")
    def debug_env(authorized: bool = Depends(verify_app_secret)):
        openai_key = os.getenv("OPENAI_API_KEY", "")

        return {
            "openai_key_exists": bool(openai_key),
            "openai_key_prefix": openai_key[:7] if openai_key else None,
            "openai_key_length": len(openai_key),
            "app_shared_secret_exists": bool(os.getenv("APP_SHARED_SECRET")),
            "model_name": os.getenv("MODEL_NAME"),
        }

    @app.get("/debug/network")
    def debug_network(authorized: bool = Depends(verify_app_secret)):
        try:
            ip = socket.gethostbyname("api.openai.com")
            return {
                "dns_ok": True,
                "api_openai_com_ip": ip,
            }
        except Exception as e:
            return {
                "dns_ok": False,
                "error": str(e),
            }


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Intenta nuevamente en unos segundos."
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "BetterMail AI API"}


@app.get(
    "/plans",
    response_model=list[PlanResponse],
    dependencies=[Depends(verify_app_secret)],
)
def plans():
    return list_plans()


@app.post(
    "/usage/status",
    response_model=UsageStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("30/minute")
def usage_status(request: Request, user: OfficeUser):
    usage = check_usage_allowed(user, settings.trial_limit)

    return {
        "allowed": usage["allowed"],
        "status": usage["status"],
        "plan": usage["plan"],
        "used": usage["used"],
        "limit": usage["limit"],
        "remaining": usage["remaining"],
        "trial_limit": usage["trial_limit"],
        "trial_used": usage["trial_used"],
        "monthlyLimit": usage["monthlyLimit"],
        "monthlyUsed": usage["monthlyUsed"],
        "upgradeRequired": usage["upgradeRequired"],
    }


@app.post(
    "/billing/checkout",
    response_model=CheckoutResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("10/minute")
def billing_checkout(request: Request, payload: CheckoutRequest):
    return create_checkout_order(
        user=payload.user,
        plan_id=payload.plan_id,
        provider=payload.provider,
        source=payload.source,
    )


@app.post(
    "/billing/admin/user",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("30/minute")
def billing_admin_user(request: Request, payload: AdminUserRequest):
    return get_admin_user(str(payload.email), settings.trial_limit)


@app.post(
    "/billing/admin/manual-activate",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("10/minute")
def billing_manual_activate(request: Request, payload: AdminActivateRequest):
    return admin_activate_user(
        email=str(payload.email),
        plan_id=payload.plan_id,
        trial_limit=settings.trial_limit,
        reason=payload.reason,
    )


@app.post(
    "/billing/admin/block",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("10/minute")
def billing_admin_block(request: Request, payload: AdminActionRequest):
    return block_user(str(payload.email), settings.trial_limit, payload.reason)


@app.post(
    "/billing/admin/unblock",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("10/minute")
def billing_admin_unblock(request: Request, payload: AdminActionRequest):
    return unblock_user(str(payload.email), settings.trial_limit, payload.reason)


@app.post(
    "/billing/admin/cancel",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("10/minute")
def billing_admin_cancel(request: Request, payload: AdminActionRequest):
    return admin_cancel_user(str(payload.email), settings.trial_limit, payload.reason)


@app.post(
    "/billing/admin/expire",
    response_model=AdminUserResponse,
    dependencies=[Depends(verify_admin_secret)],
)
@limiter.limit("10/minute")
def billing_admin_expire(request: Request, payload: AdminActionRequest):
    return admin_expire_user(str(payload.email), settings.trial_limit, payload.reason)


@app.get(
    "/billing/checkout/{order_id}",
    response_model=CheckoutDetailsResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("30/minute")
def billing_checkout_details(request: Request, order_id: str):
    return get_checkout_order(order_id)


@app.post(
    "/billing/payphone/confirm",
    response_model=BillingStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("20/minute")
def billing_payphone_confirm(request: Request, payload: PayphoneConfirmRequest):
    return confirm_payphone_subscription(
        transaction_id=payload.id,
        client_transaction_id=payload.client_transaction_id,
        card_token=payload.card_token,
        trial_limit=settings.trial_limit,
    )


@app.post(
    "/billing/cancel",
    response_model=BillingStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("10/minute")
def billing_cancel(request: Request, payload: SubscriptionActionRequest):
    return cancel_subscription(
        payload.user,
        settings.trial_limit,
        payload.reason,
    )


@app.post(
    "/billing/reactivate",
    response_model=BillingStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("10/minute")
def billing_reactivate(request: Request, payload: SubscriptionActionRequest):
    return reactivate_subscription(payload.user, settings.trial_limit)


@app.post(
    "/billing/internal/renew-subscriptions",
    response_model=RenewalJobResponse,
    dependencies=[Depends(verify_internal_job_secret)],
)
def billing_renew_subscriptions(payload: RenewalJobRequest):
    return process_due_subscriptions(
        trial_limit=settings.trial_limit,
        limit=payload.limit,
        dry_run=payload.dry_run,
    )


@app.post(
    "/billing/status",
    response_model=BillingStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("30/minute")
def billing_status(request: Request, payload: BillingStatusRequest):
    return get_billing_status(payload.user, settings.trial_limit)


@app.get(
    "/billing/status",
    response_model=BillingStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("30/minute")
def billing_status_by_email(request: Request, email: str = Query(...)):
    user = OfficeUser(email=email)
    return get_billing_status(user, settings.trial_limit)


@app.post(
    "/rewrite",
    response_model=RewriteResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("10/minute")
def rewrite(request: Request, payload: RewriteRequest):
    usage = check_usage_allowed(payload.user, settings.trial_limit)

    if not usage["allowed"]:
        return {
            "allowed": False,
            "status": usage["status"],
            "plan": usage["plan"],
            "used": usage["used"],
            "limit": usage["limit"],
            "remaining": usage["remaining"],
            "trial_limit": usage["trial_limit"],
            "trial_used": usage["trial_used"],
            "monthlyLimit": usage["monthlyLimit"],
            "monthlyUsed": usage["monthlyUsed"],
            "upgradeRequired": usage["upgradeRequired"],
            "message": usage["message"],
            "rewritten_text": None,
        }

    rewritten_text = rewrite_email_text(
        text=payload.text,
        tone=payload.tone,
        mode=payload.mode,
        context=payload.context,
    )

    usage_after = consume_rewrite_credit(
        user=payload.user,
        usage_info=usage,
        metadata={
            "action": "rewrite",
            "source": payload.source,
            "tone": payload.tone,
            "mode": payload.mode,
            "inputLength": len(payload.text),
            "contextLength": len(payload.context or ""),
            "outputLength": len(rewritten_text),
            "model": settings.model_name,
        },
    )

    return {
        "allowed": True,
        "status": usage["status"],
        "plan": usage["plan"],
        "used": usage_after["used"],
        "limit": usage["limit"],
        "remaining": usage_after["remaining"],
        "trial_limit": usage["trial_limit"],
        "trial_used": usage_after["trial_used"],
        "monthlyLimit": usage["monthlyLimit"],
        "monthlyUsed": usage_after["monthlyUsed"],
        "upgradeRequired": False,
        "rewritten_text": rewritten_text,
        "detected_tone": None,
        "suggested_tone": payload.tone,
        "message": "Texto reescrito correctamente.",
    }
