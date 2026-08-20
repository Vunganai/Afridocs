"""
Pydantic schemas for Tenant and User API requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel


# ── Tenant ─────────────────────────────────────────────────────────────────

class TenantCreate(CamelModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    contact_email: EmailStr
    country_code: str = Field(default="ZA", min_length=2, max_length=2)
    default_currency: str = Field(default="ZAR", min_length=3, max_length=3)
    approval_threshold_amount: Decimal | None = None

    @field_validator("slug")
    @classmethod
    def lowercase_slug(cls, v: str) -> str:
        return v.lower().strip()


class TenantResponse(CamelModel):
    id: UUID
    name: str
    slug: str
    contact_email: str
    country_code: str
    plan: str
    monthly_document_limit: int
    default_currency: str
    approval_threshold_amount: Decimal | None
    is_active: bool
    created_at: datetime


# ── User ───────────────────────────────────────────────────────────────────

class UserResponse(CamelModel):
    id: UUID
    supabase_user_id: UUID
    tenant_id: UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(CamelModel):
    """Used when provisioning a new user after Supabase Auth signup."""
    supabase_user_id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str = Field(default="viewer", pattern="^(admin|reviewer|approver|viewer)$")


class UserUpdate(CamelModel):
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|reviewer|approver|viewer)$")
    is_active: bool | None = None


# ── Auth / Onboarding ──────────────────────────────────────────────────────

class OnboardingRequest(CamelModel):
    """
    Sent by the frontend after a user signs up via Supabase Auth.
    Creates the tenant + user records in one call.
    """
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    contact_email: EmailStr
    full_name: str | None = None
    country_code: str = Field(default="ZA")
    default_currency: str = Field(default="ZAR")


class OnboardingResponse(CamelModel):
    tenant: TenantResponse
    user: UserResponse
