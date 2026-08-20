"""
Health check endpoints.
Used by Docker healthcheck, load balancers, and Azure Container Apps.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health() -> HealthResponse:
    """Simple liveness check — returns 200 if the process is alive."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/health/ready", response_model=HealthResponse, include_in_schema=False)
async def readiness() -> HealthResponse:
    """
    Readiness check — verifies the app can handle traffic.
    In a full implementation this would check DB and Redis connectivity.
    """
    return HealthResponse(status="ready", version="0.1.0")
