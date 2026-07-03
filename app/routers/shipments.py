from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models.enums import ShipmentStatus, UserRole
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.shipment import (
    ShipmentAssign,
    ShipmentCreate,
    ShipmentDetail,
    ShipmentRead,
)
from app.schemas.tracking import TrackingEventCreate, TrackingEventRead
from app.services import shipment_service

router = APIRouter(prefix="/shipments", tags=["shipments"])

_STAFF = {UserRole.ADMIN, UserRole.DISPATCHER}


def _can_view(user: User, shipment: Shipment) -> bool:
    if user.role in _STAFF:
        return True
    if user.role == UserRole.CUSTOMER:
        return shipment.customer_id == user.id
    if user.role == UserRole.DRIVER:
        return shipment.driver_id == user.id
    return False


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    data: ShipmentCreate, db: DbSession, current_user: CurrentUser
) -> Shipment:
    # Customers create shipments for themselves; staff may specify a customer_id.
    if current_user.role in _STAFF:
        customer_id = data.customer_id or current_user.id
    else:
        customer_id = current_user.id

    payload = data.model_dump(exclude={"customer_id"})
    return await shipment_service.create_shipment(
        db, data=payload, customer_id=customer_id
    )


@router.get("", response_model=list[ShipmentRead])
async def list_shipments(
    db: DbSession,
    current_user: CurrentUser,
    status_filter: ShipmentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Shipment]:
    stmt = select(Shipment).order_by(Shipment.created_at.desc())

    if current_user.role == UserRole.CUSTOMER:
        stmt = stmt.where(Shipment.customer_id == current_user.id)
    elif current_user.role == UserRole.DRIVER:
        stmt = stmt.where(Shipment.driver_id == current_user.id)

    if status_filter is not None:
        stmt = stmt.where(Shipment.status == status_filter)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{shipment_id}", response_model=ShipmentDetail)
async def get_shipment(
    shipment_id: int, db: DbSession, current_user: CurrentUser
) -> Shipment:
    result = await db.execute(
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(selectinload(Shipment.events))
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found"
        )
    if not _can_view(current_user, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this shipment",
        )
    return shipment


@router.patch("/{shipment_id}/assign", response_model=ShipmentRead)
async def assign_shipment(
    shipment_id: int,
    data: ShipmentAssign,
    db: DbSession,
    current_user: CurrentUser,
) -> Shipment:
    if current_user.role not in _STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatchers and admins can assign shipments",
        )
    shipment = await shipment_service.get_shipment_or_404(db, shipment_id)
    return await shipment_service.assign_shipment(
        db,
        shipment=shipment,
        driver_id=data.driver_id,
        vehicle_id=data.vehicle_id,
    )


@router.post(
    "/{shipment_id}/events",
    response_model=TrackingEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_event(
    shipment_id: int,
    data: TrackingEventCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> TrackingEventRead:
    shipment = await shipment_service.get_shipment_or_404(db, shipment_id)

    is_assigned_driver = (
        current_user.role == UserRole.DRIVER
        and shipment.driver_id == current_user.id
    )
    if current_user.role not in _STAFF and not is_assigned_driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff or the assigned driver can update this shipment",
        )

    return await shipment_service.add_tracking_event(
        db,
        shipment=shipment,
        new_status=data.status,
        location=data.location,
        note=data.note,
    )


@router.get("/{shipment_id}/events", response_model=list[TrackingEventRead])
async def list_events(
    shipment_id: int, db: DbSession, current_user: CurrentUser
) -> list[TrackingEventRead]:
    result = await db.execute(
        select(Shipment)
        .where(Shipment.id == shipment_id)
        .options(selectinload(Shipment.events))
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found"
        )
    if not _can_view(current_user, shipment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this shipment",
        )
    return shipment.events
