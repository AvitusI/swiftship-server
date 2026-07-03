from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ShipmentStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrackingEvent(Base):
    """An immutable audit record of a shipment status change / location ping."""

    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(back_populates="events")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrackingEvent shipment={self.shipment_id} status={self.status.value}>"
