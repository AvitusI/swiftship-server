from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ShipmentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    origin_address: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_address: Mapped[str] = mapped_column(String(500), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(40), nullable=False)

    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus),
        default=ShipmentStatus.CREATED,
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicles.id"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    customer: Mapped["User"] = relationship(  # noqa: F821
        back_populates="owned_shipments", foreign_keys=[customer_id]
    )
    driver: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="driven_shipments", foreign_keys=[driver_id]
    )
    vehicle: Mapped["Vehicle | None"] = relationship(  # noqa: F821
        back_populates="shipments"
    )
    events: Mapped[list["TrackingEvent"]] = relationship(  # noqa: F821
        back_populates="shipment",
        cascade="all, delete-orphan",
        order_by="TrackingEvent.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Shipment {self.tracking_number} status={self.status.value}>"
