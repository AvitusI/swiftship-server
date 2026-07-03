from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ShipmentStatus


class TrackingEventCreate(BaseModel):
    status: ShipmentStatus
    location: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=500)


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ShipmentStatus
    location: str | None
    note: str | None
    created_at: datetime
