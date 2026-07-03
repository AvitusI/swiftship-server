# SwiftShip — Logistics & Delivery Tracking API

A production-style REST API for a courier / logistics company, built with **FastAPI**
and **async SQLAlchemy 2.0**. It models the real workflow of moving a parcel from
booking to delivery: customers book shipments, dispatchers assign a driver and
vehicle, drivers push status updates from the road, and anyone with the tracking
number can follow the parcel — no login required.

> Part of a two-project backend portfolio. See also **SpinQueue** (a real-time DJ
> song-request API) in the sibling folder.

---

## Highlights

- **Role-based access control** — `admin`, `dispatcher`, `driver`, `customer`, each
  with a different view of the data (customers see only their own shipments, drivers
  see only what's assigned to them, staff see everything).
- **Validated shipment lifecycle** — a state machine enforces legal transitions
  (`created → assigned → picked_up → in_transit → out_for_delivery → delivered`),
  so you can't mark an unassigned parcel "delivered".
- **JWT authentication** via the OAuth2 password flow.
- **Immutable tracking history** — every status change writes an audit event.
- **Public tracking endpoint** — unauthenticated lookup by tracking number, with
  sensitive fields stripped from the response.
- **Business rules that matter** — vehicle capacity is checked against parcel weight,
  vehicles flip to `in_use`/`available` automatically, etc.
- **13 passing async tests** covering auth, access control, and the full lifecycle.

## Tech stack

| Concern        | Choice                                   |
| -------------- | ---------------------------------------- |
| Framework      | FastAPI                                  |
| ORM            | SQLAlchemy 2.0 (async, typed `Mapped`)   |
| Database       | SQLite (via `aiosqlite`) — swap the URL for Postgres |
| Auth           | JWT (PyJWT) + bcrypt password hashing    |
| Validation     | Pydantic v2                              |
| Tests          | pytest + pytest-asyncio + httpx          |

## Architecture

Clean, layered separation — routers stay thin, business rules live in services:

```
app/
├── core/          # config, database engine, security (JWT/bcrypt), DI dependencies
├── models/        # SQLAlchemy ORM models + enums + the lifecycle state machine
├── schemas/       # Pydantic request/response models
├── services/      # business logic (shipment lifecycle, assignment, users)
├── routers/       # HTTP endpoints, grouped by resource
└── main.py        # app factory, lifespan (table creation + admin bootstrap)
tests/             # async test suite
scripts/seed.py    # demo data
```

## Quick start

```bash
# 1. install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. (optional) configure — defaults work out of the box
cp .env.example .env

# 3. run
uvicorn app.main:app --reload
```

Open the interactive docs at **http://127.0.0.1:8000/docs**.

On first boot an admin account is created automatically:
`admin@swiftship.io` / `admin12345` (override via `.env`).

Load demo data (a dispatcher, driver, customer and a sample shipment):

```bash
python -m scripts.seed
```

## Trying it out

```bash
# log in as the bootstrap admin
curl -X POST localhost:8000/api/v1/auth/login \
  -d "username=admin@swiftship.io&password=admin12345"

# ... then use the returned token:
curl localhost:8000/api/v1/shipments -H "Authorization: Bearer <TOKEN>"

# public tracking — no auth needed
curl localhost:8000/api/v1/track/SS-XXXXXXXX
```

## API overview

| Method & path                              | Who            | Purpose                                |
| ------------------------------------------ | -------------- | -------------------------------------- |
| `POST /auth/register`                      | public         | Register a customer account            |
| `POST /auth/login`                         | public         | Get a JWT (OAuth2 password flow)       |
| `GET  /auth/me`                            | any user       | Current user                           |
| `POST /users`                              | admin          | Create staff (dispatcher/driver/...)   |
| `GET  /users`                              | admin          | List users (filter by `role`)          |
| `POST /vehicles`                           | admin/dispatch | Add a vehicle                          |
| `GET  /vehicles`                           | admin/dispatch | List vehicles                          |
| `PATCH /vehicles/{id}`                     | admin/dispatch | Update vehicle / status                |
| `POST /shipments`                          | any user       | Book a shipment                        |
| `GET  /shipments`                          | any user       | List (scoped to your role)             |
| `GET  /shipments/{id}`                     | owner/driver/staff | Shipment + full tracking history   |
| `PATCH /shipments/{id}/assign`             | admin/dispatch | Assign driver + vehicle                |
| `POST /shipments/{id}/events`              | staff/driver   | Push a status update                   |
| `GET  /track/{tracking_number}`            | public         | Public parcel tracking                 |

All endpoints are prefixed with `/api/v1`.

## Tests

```bash
pytest
```

## Notes for reviewers

- Tables are auto-created on startup for zero-setup demoing. For a real deployment
  you'd add **Alembic** migrations — the models are already structured for it.
- SQLite keeps the project one-command-runnable. Because everything goes through
  async SQLAlchemy, switching to Postgres is just changing `DATABASE_URL` to a
  `postgresql+asyncpg://...` URL.
- The `Dockerfile` is optional; the app needs nothing but `uvicorn` to run locally.
