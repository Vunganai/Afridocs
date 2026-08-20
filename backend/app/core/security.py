"""
Auth/security utilities.
Validates Supabase-issued JWTs and extracts the authenticated user context.
"""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)


class AuthUser(BaseModel):
    """Parsed claims from a Supabase JWT."""
    user_id: UUID
    email: str
    tenant_id: UUID | None = None
    role: str = "viewer"


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT.
    Supabase uses HS256 with the project JWT secret.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> AuthUser:
    """
    FastAPI dependency — extracts and validates the bearer token,
    returns a typed AuthUser from the JWT claims.
    """
    payload = decode_supabase_jwt(credentials.credentials)

    user_id_str = payload.get("sub")
    email = payload.get("email", "")

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )

    # Supabase stores custom claims in app_metadata
    app_metadata = payload.get("app_metadata", {})
    tenant_id_str = app_metadata.get("tenant_id")
    role = app_metadata.get("role", "viewer")

    return AuthUser(
        user_id=UUID(user_id_str),
        email=email,
        tenant_id=UUID(tenant_id_str) if tenant_id_str else None,
        role=role,
    )


def require_role(*allowed_roles: str):
    """
    Dependency factory — raises 403 if the authenticated user's role
    is not in the allowed list.

    Usage:
        @router.post("/approve", dependencies=[Depends(require_role("approver", "admin"))])
    """
    def _check(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted for this action.",
            )
        return user
    return _check


# Convenience aliases
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
AdminUser = Annotated[AuthUser, Depends(require_role("admin"))]
ReviewerUser = Annotated[AuthUser, Depends(require_role("admin", "reviewer"))]
ApproverUser = Annotated[AuthUser, Depends(require_role("admin", "approver"))]
