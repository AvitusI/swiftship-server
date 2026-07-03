"""Populate the database with demo data so the API is fun to click around.

Run from the project root with the venv active:

    python -m scripts.seed
"""

import asyncio

from app.core.database import AsyncSessionLocal, init_db
from app.models.enums import UserRole
from app.services import shipment_service, user_service


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        # Staff
        await user_service.ensure_first_admin(
            db, email="admin@swiftship.io", password="admin12345"
        )
        dispatcher = await _get_or_create(
            db, "dispatch@swiftship.io", "dispatch12345", UserRole.DISPATCHER, "Dora Dispatcher"
        )
        driver = await _get_or_create(
            db, "driver@swiftship.io", "driver12345", UserRole.DRIVER, "Dan Driver"
        )
        customer = await _get_or_create(
            db, "customer@swiftship.io", "customer12345", UserRole.CUSTOMER, "Cara Customer"
        )

        # A demo shipment owned by the customer
        existing = await shipment_service.get_by_tracking_number(db, "SS-DEMO0001")
        if existing is None:
            await shipment_service.create_shipment(
                db,
                data={
                    "description": "Two crates of coffee beans",
                    "weight_kg": 40.0,
                    "origin_address": "Mabibo, Dar es Salaam",
                    "destination_address": "Mount Meru, Arusha",
                    "recipient_name": "Neema Recipient",
                    "recipient_phone": "+255700111222",
                },
                customer_id=customer.id,
            )

        print("Seeded demo data:")
        print("  admin@swiftship.io      / admin12345      (admin)")
        print(f"  {dispatcher.email} / dispatch12345   (dispatcher)")
        print(f"  {driver.email}   / driver12345     (driver, id={driver.id})")
        print(f"  {customer.email} / customer12345   (customer, id={customer.id})")


async def _get_or_create(db, email, password, role, full_name):
    user = await user_service.get_user_by_email(db, email)
    if user is None:
        user = await user_service.create_user(
            db, email=email, password=password, full_name=full_name, role=role
        )
    return user


if __name__ == "__main__":
    asyncio.run(main())
