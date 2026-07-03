from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.routers import auth, shipments, tracking, users, vehicles
from app.services.user_service import ensure_first_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and bootstrap the first admin.
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_first_admin(
            db,
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD,
        )
    yield
    # Shutdown: nothing to clean up for SQLite.


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "SwiftShip — a logistics & delivery tracking API. "
        "Role-based access for admins, dispatchers, drivers and customers, "
        "with a validated shipment lifecycle and public tracking."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}


for r in (auth.router, users.router, vehicles.router, shipments.router, tracking.router):
    app.include_router(r, prefix=settings.API_V1_PREFIX)
