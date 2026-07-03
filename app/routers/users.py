from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

AdminOnly = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
StaffOnly = Annotated[
    User, Depends(require_roles(UserRole.ADMIN, UserRole.DISPATCHER))
]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    data: UserCreate, db: DbSession, _admin: AdminOnly
) -> UserRead:
    """Admin-only: create a user with any role (dispatcher, driver, etc.)."""
    from fastapi import HTTPException

    if await user_service.get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    return await user_service.create_user(
        db,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=data.role,
    )


@router.get("", response_model=list[UserRead])
async def list_users(
    db: DbSession,
    _staff: StaffOnly,
    role: UserRole | None = Query(default=None),
) -> list[User]:
    """Admins and dispatchers can list users (e.g. drivers, for assignment)."""
    stmt = select(User).order_by(User.id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> User:
    return current_user
