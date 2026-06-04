from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models import RewriteRequest, RewriteResponse, UsageStatusResponse, OfficeUser
from app.security import verify_app_secret
from app.usage_service import check_usage_allowed, consume_rewrite_credit
from app.openai_service import rewrite_email_text

import socket
import os

from fastapi import Depends
from app.security import verify_app_secret

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="BetterMail AI API",
    version="1.0.0",
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
    allow_headers=["Content-Type", "X-App-Secret", "x-app-secret"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


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


@app.post(
    "/usage/status",
    response_model=UsageStatusResponse,
    dependencies=[Depends(verify_app_secret)],
)
@limiter.limit("30/minute")
def usage_status(request: Request, user: OfficeUser):
    usage = check_usage_allowed(user, settings.trial_limit)

    return {
        "status": usage["status"],
        "remaining": usage["remaining"],
        "trial_limit": usage["trial_limit"],
        "trial_used": usage["trial_used"],
    }


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
            "remaining": usage["remaining"],
            "trial_limit": usage["trial_limit"],
            "trial_used": usage["trial_used"],
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
        "remaining": usage_after["remaining"],
        "trial_limit": usage["trial_limit"],
        "trial_used": usage_after["trial_used"],
        "rewritten_text": rewritten_text,
        "detected_tone": None,
        "suggested_tone": payload.tone,
        "message": "Texto reescrito correctamente.",
    }
