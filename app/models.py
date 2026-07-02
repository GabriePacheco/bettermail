from pydantic import BaseModel, EmailStr, Field
from typing import Any, Literal, Optional


Tone = Literal[
    "profesional",
    "firme_amable",
    "ejecutivo",
    "conciliador",
    "directo",
    "diplomatico",
    "institucional",
    "reclamo_formal",
    "custom",
]


class OfficeUser(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    account_type: Optional[str] = None
    time_zone: Optional[str] = None


class RewriteRequest(BaseModel):
    user: OfficeUser
    text: str = Field(default="", max_length=12000)
    tone: Tone = "profesional"
    source: Literal["outlook_addin"] = "outlook_addin"
    mode: str = "rewrite_draft"
    context: Optional[str] = None
    variation: int = Field(default=0, ge=0, le=20)
    custom_tone: Optional[str] = Field(default=None, max_length=600)
    has_signature: bool = False


class RewriteResponse(BaseModel):
    allowed: bool
    status: str
    remaining: int
    trial_limit: int
    trial_used: int
    plan: Optional[str] = None
    used: Optional[int] = None
    limit: Optional[int] = None
    monthlyLimit: Optional[int] = None
    monthlyUsed: Optional[int] = None
    upgradeRequired: Optional[bool] = None
    rewritten_text: Optional[str] = None
    detected_tone: Optional[str] = None
    suggested_tone: Optional[str] = None
    message: Optional[str] = None


class UsageStatusResponse(BaseModel):
    allowed: Optional[bool] = None
    status: str
    plan: Optional[str] = None
    used: Optional[int] = None
    limit: Optional[int] = None
    remaining: int
    trial_limit: int
    trial_used: int
    monthlyLimit: Optional[int] = None
    monthlyUsed: Optional[int] = None
    upgradeRequired: Optional[bool] = None


class PlanResponse(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    monthlyLimit: int
    active: bool


class CheckoutRequest(BaseModel):
    user: OfficeUser
    plan_id: str
    provider: Literal["manual", "payphone_cajita"] = "manual"
    source: Literal["outlook_addin"] = "outlook_addin"


class CheckoutResponse(BaseModel):
    checkout_url: str
    order_id: str
    status: str
    provider: Optional[str] = None
    payment_unavailable_reason: Optional[str] = None
    plan: Optional[PlanResponse] = None
    payphone_token: Optional[str] = None
    payphone_store_id: Optional[str] = None
    payphone_client_transaction_id: Optional[str] = None
    payphone_amount: Optional[int] = None
    payphone_amount_without_tax: Optional[int] = None
    payphone_currency: Optional[str] = None
    payphone_reference: Optional[str] = None
    payphone_default_method: Optional[str] = None


class CheckoutDetailsResponse(CheckoutResponse):
    email: EmailStr
    source: Optional[str] = None


class ManualActivateRequest(BaseModel):
    email: EmailStr
    plan_id: str


class PayphoneConfirmRequest(BaseModel):
    id: int
    client_transaction_id: str
    card_token: Optional[str] = None


class BillingStatusRequest(BaseModel):
    user: OfficeUser


class BillingStatusResponse(BaseModel):
    plan: str
    status: str
    subscriptionStatus: Optional[str] = None
    monthlyLimit: int
    monthlyUsed: int
    currentPeriodEnd: Optional[str] = None
    gracePeriodEnd: Optional[str] = None
    nextRenewalAttemptAt: Optional[str] = None
    cancelAtPeriodEnd: bool = False
    autoRenew: bool = False
    paymentActionRequired: bool = False
    renewalFailureCount: int = 0


class SubscriptionActionRequest(BaseModel):
    user: OfficeUser
    reason: Optional[str] = Field(default=None, max_length=500)


class RenewalJobRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)
    dry_run: bool = False


class RenewalJobResponse(BaseModel):
    scanned: int
    due: int
    renewed: int
    past_due: int
    expired: int
    cancelled: int
    skipped: int
    errors: int
    dry_run: bool


class AdminUserRequest(BaseModel):
    email: EmailStr


class AdminActionRequest(AdminUserRequest):
    reason: Optional[str] = Field(default=None, max_length=500)


class AdminActivateRequest(AdminUserRequest):
    plan_id: str = "pro_monthly"
    reason: Optional[str] = Field(default=None, max_length=500)


class AdminAuditEvent(BaseModel):
    action: str
    createdAt: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminUserResponse(BaseModel):
    exists: bool
    email: EmailStr
    displayName: Optional[str] = None
    accountType: Optional[str] = None
    plan: str = "trial"
    status: str = "not_found"
    subscriptionStatus: Optional[str] = None
    trialLimit: int = 0
    trialUsed: int = 0
    monthlyLimit: int = 0
    monthlyUsed: int = 0
    currentPeriodEnd: Optional[str] = None
    gracePeriodEnd: Optional[str] = None
    cancelAtPeriodEnd: bool = False
    autoRenew: bool = False
    paymentActionRequired: bool = False
    renewalFailureCount: int = 0
    paymentProvider: Optional[str] = None
    hasReusablePaymentMethod: bool = False
    cardBrand: Optional[str] = None
    cardLastDigits: Optional[str] = None
    auditEvents: list[AdminAuditEvent] = Field(default_factory=list)


class OpenAICostDay(BaseModel):
    date: str
    requests: int = 0
    promptTokens: int = 0
    cachedPromptTokens: int = 0
    completionTokens: int = 0
    totalTokens: int = 0
    estimatedCostUsd: float = 0
    model: Optional[str] = None
    pricingLabel: Optional[str] = None


class OpenAICostSummary(BaseModel):
    days: int
    requests: int
    promptTokens: int
    cachedPromptTokens: int
    completionTokens: int
    totalTokens: int
    estimatedCostUsd: float
    daily: list[OpenAICostDay] = Field(default_factory=list)
