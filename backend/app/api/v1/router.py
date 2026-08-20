"""
API v1 router — aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, dashboard, documents, health, workflow

api_router = APIRouter()

# Health (no auth)
api_router.include_router(health.router)

# Auth / onboarding
api_router.include_router(auth.router, prefix="/v1")

# Core resources
api_router.include_router(documents.router, prefix="/v1")
api_router.include_router(workflow.router, prefix="/v1")
api_router.include_router(dashboard.router, prefix="/v1")
