from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VehicleStatus


class VehicleBase(BaseModel):
    plate_number: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=120)
    capacity_kg: float = Field(ge=0)


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=120)
    capacity_kg: float | None = Field(default=None, ge=0)
    status: VehicleStatus | None = None


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: VehicleStatus
    created_at: datetime
