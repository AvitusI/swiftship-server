import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    SHIPMENT_TRANSITIONS,
    ShipmentStatus,
    UserRole,
    VehicleStatus,
)
from app.models.shipment import Shipment
from app.models.tracking import TrackingEvent
from app.models.user import User
from app.models.vehicle import Vehicle


def generate_tracking_number() -> str:
    """Human-friendly, collision-resistant tracking code, e.g. SS-8F3A1C7B."""
    return f"SS-{secrets.token_hex(4).upper()}"


async def create_shipment(
    db: AsyncSession,
    *,
    data: dict,
    customer_id: int,
) -> Shipment:
    shipment = Shipment(
        **data,
        customer_id=customer_id,
        tracking_number=generate_tracking_number(),
        status=ShipmentStatus.CREATED,
    )
    db.add(shipment)
    await db.flush()

    db.add(
        TrackingEvent(
            shipment_id=shipment.id,
            status=ShipmentStatus.CREATED,
            note="Shipment created",
        )
    )
    await db.commit()
    await db.refresh(shipment)
    return shipment


async def assign_shipment(
    db: AsyncSession,
    *,
    shipment: Shipment,
    driver_id: int,
    vehicle_id: int,
) -> Shipment:
    if shipment.status != ShipmentStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only shipments in '{ShipmentStatus.CREATED.value}' state can be assigned",
        )

    driver = await db.get(User, driver_id)
    if driver is None or driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found"
        )

    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    if vehicle.status != VehicleStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Vehicle is not available"
        )
    if vehicle.capacity_kg < shipment.weight_kg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle capacity is below the shipment weight",
        )

    shipment.driver_id = driver_id
    shipment.vehicle_id = vehicle_id
    shipment.status = ShipmentStatus.ASSIGNED
    vehicle.status = VehicleStatus.IN_USE

    db.add(
        TrackingEvent(
            shipment_id=shipment.id,
            status=ShipmentStatus.ASSIGNED,
            note=f"Assigned to driver #{driver_id} on vehicle {vehicle.plate_number}",
        )
    )
    await db.commit()
    await db.refresh(shipment)
    return shipment


async def add_tracking_event(
    db: AsyncSession,
    *,
    shipment: Shipment,
    new_status: ShipmentStatus,
    location: str | None,
    note: str | None,
) -> TrackingEvent:
    allowed = SHIPMENT_TRANSITIONS[shipment.status]
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Illegal transition {shipment.status.value} -> {new_status.value}. "
                f"Allowed: {sorted(s.value for s in allowed) or 'none (terminal state)'}"
            ),
        )

    event = TrackingEvent(
        shipment_id=shipment.id,
        status=new_status,
        location=location,
        note=note,
    )
    db.add(event)
    shipment.status = new_status

    # Free the vehicle once the shipment reaches a terminal state.
    if new_status in (ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED):
        if shipment.vehicle_id is not None:
            vehicle = await db.get(Vehicle, shipment.vehicle_id)
            if vehicle is not None:
                vehicle.status = VehicleStatus.AVAILABLE

    await db.commit()
    await db.refresh(event)
    return event


async def get_shipment_or_404(db: AsyncSession, shipment_id: int) -> Shipment:
    shipment = await db.get(Shipment, shipment_id)
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found"
        )
    return shipment


async def get_by_tracking_number(
    db: AsyncSession, tracking_number: str
) -> Shipment | None:
    result = await db.execute(
        select(Shipment).where(Shipment.tracking_number == tracking_number)
    )
    return result.scalar_one_or_none()
