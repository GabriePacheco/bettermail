from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional


Tone = Literal[
    "profesional",
    "firme_amable",
    "ejecutivo",
    "conciliador",
    "directo",
    "diplomatico",
    "institucional",
    "reclamo_formal"
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
