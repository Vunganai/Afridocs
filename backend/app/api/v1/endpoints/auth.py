"""
Auth & onboarding endpoints.
Supabase handles the actual sign-in flow; these endpoints handle the
post-auth provisioning of Tenant and User records in our database.
"""

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import (
    OnboardingRequest,
    OnboardingResponse,
    TenantResponse,
    UserResponse,
)
from app.services.audit import AuditEventType, AuditService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/onboard", response_model=OnboardingResponse, status_code=201)
async def onboard(
    body: OnboardingRequest,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> OnboardingResponse:
    """
    Called by the frontend immediately after a user signs up via Supabase Auth.
    Creates the Tenant and User records in one atomic transaction.

    The caller must be authenticated (Supabase JWT required).
    """
    # Check slug is not already taken
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.tenant_slug))
    if existing.scalar_one_or_none():
        raise ConflictError(f"Tenant slug '{body.tenant_slug}' is already taken.")

    # Check this Supabase user hasn't already been onboarded
    existing_user = await db.execute(
        select(User).where(User.supabase_user_id == current_user.user_id)
    )
    if existing_user.scalar_one_or_none():
        raise ConflictError("This account has already been onboarded.")

    # Create tenant
    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_slug,
        contact_email=str(body.contact_email),
        country_code=body.country_code,
        default_currency=body.default_currency,
    )
    db.add(tenant)
    await db.flush()  # Get tenant.id without committing

    # Create user (admin role — first user in a tenant is always admin)
    user = User(
        supabase_user_id=current_user.user_id,
        tenant_id=tenant.id,
        email=current_user.email,
        full_name=body.full_name,
        role="admin",
    )
    db.add(user)

    # Flush to get DB-generated values (id, created_at, is_active defaults)
    await db.flush()
    await db.refresh(tenant)
    await db.refresh(user)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.TENANT_CREATED,
        tenant_id=tenant.id,
        actor_id=current_user.user_id,
        actor_email=current_user.email,
        resource_type="tenant",
        resource_id=tenant.id,
        metadata={"tenant_name": tenant.name, "slug": tenant.slug},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await audit.log(
        event_type=AuditEventType.USER_CREATED,
        tenant_id=tenant.id,
        actor_id=current_user.user_id,
        actor_email=current_user.email,
        resource_type="user",
        resource_id=user.id,
        metadata={"role": "admin"},
    )

    # Commit handled by session dependency
    return OnboardingResponse(
        tenant=TenantResponse.model_validate(tenant),
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser,
    db: DbSession,
) -> UserResponse:
    """Return the authenticated user's profile from our database."""
    result = await db.execute(
        select(User).where(User.supabase_user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User profile not found. Please complete onboarding.")
    return UserResponse.model_validate(user)
