from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import DbSession, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

StaffOnly = Annotated[
    User, Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER))
]


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate, db: DbSession, _staff: StaffOnly
) -> Vehicle:
    vehicle = Vehicle(**data.model_dump())
    db.add(vehicle)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A vehicle with this plate number already exists",
        )
    await db.refresh(vehicle)
    return vehicle


@router.get("", response_model=list[VehicleRead])
async def list_vehicles(db: DbSession, _staff: StaffOnly) -> list[Vehicle]:
    result = await db.execute(select(Vehicle).order_by(Vehicle.id))
    return list(result.scalars().all())


@router.get("/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(
    vehicle_id: int, db: DbSession, _staff: StaffOnly
) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleRead)
async def update_vehicle(
    vehicle_id: int, data: VehicleUpdate, db: DbSession, _staff: StaffOnly
) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle
