from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import VehicleStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate_number: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus), default=VehicleStatus.AVAILABLE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        back_populates="vehicle"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle id={self.id} plate={self.plate_number!r}>"
