from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    tracking_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    current_status: Mapped[str] = mapped_column(String(64), nullable=False, default="created", index=True)
    estimated_delivery: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_delayed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delay_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delay_seconds: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    company = relationship("Company", back_populates="shipments")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    status_history = relationship(
        "ShipmentStatusHistory",
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="ShipmentStatusHistory.visible_at",
    )
