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
    rewritten_text: Optional[str] = None
    detected_tone: Optional[str] = None
    suggested_tone: Optional[str] = None
    message: Optional[str] = None


class UsageStatusResponse(BaseModel):
    status: str
    remaining: int
    trial_limit: int
    trial_used: int
