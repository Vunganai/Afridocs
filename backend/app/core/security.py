"""
Auth/security utilities.
Validates Supabase-issued JWTs and extracts the authenticated user context.

Supabase now uses ECC (P-256) / ES256 asymmetric signing.
Tokens are verified using the public key from Supabase's JWKS endpoint.
"""

from typing import Annotated
from uuid import UUID

import structlog
import jwt as pyjwt
from jwt.algorithms import ECAlgorithm
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=True)

# Supabase public key (EC P-256) from:
# https://godrwuupzfsertenreag.supabase.co/auth/v1/.well-known/jwks.json
_SUPABASE_PUBLIC_KEY_JWK = {
    "alg": "ES256",
    "crv": "P-256",
    "ext": True,
    "key_ops": ["verify"],
    "kid": "a9ab7c8e-9407-4678-a8a2-3abe258c1930",
    "kty": "EC",
    "use": "sig",
    "x": "4t2ZMzxYfJvRyWZoqs1fImV9y2s1sG0KRPoBmxZZcuw",
    "y": "jfzUW4QSFIvtnXfIn0IW4ATJRTBRS3e-f6RH0Dw3Wio",
}

import json

# Build the public key once at module load
_PUBLIC_KEY = ECAlgorithm.from_jwk(json.dumps(_SUPABASE_PUBLIC_KEY_JWK))


class AuthUser(BaseModel):
    """Parsed claims from a Supabase JWT."""
    user_id: UUID
    email: str
    tenant_id: UUID | None = None
    role: str = "viewer"


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT using ES256 (ECC P-256).
    Supabase migrated from HS256 shared secret to asymmetric ES256 signing.
    Verification uses the public key from Supabase's JWKS endpoint.
    """
    try:
        payload = pyjwt.decode(
            token,
            _PUBLIC_KEY,
            algorithms=["ES256"],
            audience="authenticated",
        )
        return payload
    except pyjwt.ExpiredSignatureError as exc:
        logger.warning("jwt_expired", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except pyjwt.PyJWTError as exc:
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
