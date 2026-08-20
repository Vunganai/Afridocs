"""
Tenant model — one row per organisation using AfriDocs AI.
Multi-tenancy is enforced via tenant_id on all data tables + Supabase RLS.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    An organisation (tenant) that has subscribed to AfriDocs AI.
    All user data belongs to a tenant; no cross-tenant data access is permitted.
    """

    __tablename__ = "tenants"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Contact
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), default="ZA", nullable=False)

    # Plan / limits
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    monthly_document_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Settings
    approval_threshold_amount: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Invoices above this amount require manager approval. NULL = all require approval.",
    )
    default_currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="select")
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="tenant", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"
