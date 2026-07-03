from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession
from app.models.shipment import Shipment
from app.schemas.shipment import PublicTracking

router = APIRouter(prefix="/track", tags=["public-tracking"])


@router.get("/{tracking_number}", response_model=PublicTracking)
async def public_track(tracking_number: str, db: DbSession) -> Shipment:
    """Unauthenticated tracking lookup — the endpoint a recipient would hit."""
    result = await db.execute(
        select(Shipment)
        .where(Shipment.tracking_number == tracking_number.upper())
        .options(selectinload(Shipment.events))
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No shipment found for this tracking number",
        )
    return shipment
