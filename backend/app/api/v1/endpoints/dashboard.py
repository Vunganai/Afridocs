"""
Dashboard / reporting endpoints.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.document import Document, DocumentStatus
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DocumentStatusCount(BaseModel):
    status: str
    count: int


class DashboardMetrics(BaseModel):
    total_documents: int
    processed_last_7_days: int
    processed_last_30_days: int
    pending_review: int
    approved: int
    rejected: int
    duplicates_caught: int
    status_breakdown: list[DocumentStatusCount]


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    current_user: CurrentUser,
    db: DbSession,
) -> DashboardMetrics:
    """Return document processing metrics for the tenant dashboard."""
    result = await db.execute(
        select(User).where(User.supabase_user_id == current_user.user_id)
    )
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise NotFoundError("User profile not found.")

    tenant_id = db_user.tenant_id
    today = date.today()

    # Total documents
    total = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == tenant_id,
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Processed in last 7 days
    last_7 = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == tenant_id,
                Document.created_at >= today - timedelta(days=7),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Processed in last 30 days
    last_30 = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.tenant_id == tenant_id,
                Document.created_at >= today - timedelta(days=30),
                Document.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    # Status counts
    status_rows = (
        await db.execute(
            select(Document.status, func.count(Document.id))
            .where(
                Document.tenant_id == tenant_id,
                Document.deleted_at.is_(None),
            )
            .group_by(Document.status)
        )
    ).all()

    status_map = {row[0]: row[1] for row in status_rows}

    return DashboardMetrics(
        total_documents=total,
        processed_last_7_days=last_7,
        processed_last_30_days=last_30,
        pending_review=status_map.get(DocumentStatus.REVIEW_REQUIRED, 0),
        approved=status_map.get(DocumentStatus.APPROVED, 0),
        rejected=status_map.get(DocumentStatus.REJECTED, 0),
        duplicates_caught=status_map.get(DocumentStatus.DUPLICATE, 0),
        status_breakdown=[
            DocumentStatusCount(status=s, count=c) for s, c in status_map.items()
        ],
    )
