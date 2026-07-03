from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ShipmentStatus
from app.schemas.tracking import TrackingEventRead


class ShipmentBase(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    weight_kg: float = Field(ge=0)
    origin_address: str = Field(min_length=1, max_length=500)
    destination_address: str = Field(min_length=1, max_length=500)
    recipient_name: str = Field(min_length=1, max_length=255)
    recipient_phone: str = Field(min_length=1, max_length=40)


class ShipmentCreate(ShipmentBase):
    # Optional: dispatchers/admins may create a shipment on behalf of a customer.
    customer_id: int | None = None


class ShipmentAssign(BaseModel):
    driver_id: int
    vehicle_id: int


class ShipmentRead(ShipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_number: str
    status: ShipmentStatus
    customer_id: int
    driver_id: int | None
    vehicle_id: int | None
    created_at: datetime
    updated_at: datetime


class ShipmentDetail(ShipmentRead):
    events: list[TrackingEventRead] = []


class PublicTracking(BaseModel):
    """Response for the unauthenticated public tracking endpoint."""

    tracking_number: str
    status: ShipmentStatus
    destination_address: str
    recipient_name: str
    events: list[TrackingEventRead] = []
