from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def ensure_first_admin(
    db: AsyncSession, *, email: str, password: str
) -> None:
    """Create the bootstrap admin account if it doesn't already exist."""
    existing = await get_user_by_email(db, email)
    if existing is None:
        await create_user(
            db,
            email=email,
            password=password,
            full_name="SwiftShip Admin",
            role=UserRole.ADMIN,
        )
