import pytest

from tests.conftest import _auth

pytestmark = pytest.mark.asyncio

SHIPMENT_PAYLOAD = {
    "description": "Box of spare parts",
    "weight_kg": 12.5,
    "origin_address": "Mabibo, Dar es Salaam",
    "destination_address": "Arusha CBD",
    "recipient_name": "John Recipient",
    "recipient_phone": "+255700000000",
}


async def _create_shipment(client, customer):
    resp = await client.post(
        "/api/v1/shipments", json=SHIPMENT_PAYLOAD, headers=_auth(customer["token"])
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_vehicle(client, admin_token, capacity=1000.0):
    resp = await client.post(
        "/api/v1/vehicles",
        json={"plate_number": "T123ABC", "model": "Isuzu NPR", "capacity_kg": capacity},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_customer_creates_and_sees_own_shipment(client, customer):
    created = await _create_shipment(client, customer)
    assert created["status"] == "created"
    assert created["tracking_number"].startswith("SS-")
    assert created["customer_id"] == customer["id"]

    listing = await client.get(
        "/api/v1/shipments", headers=_auth(customer["token"])
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_customer_cannot_view_others_shipment(client, customer, admin_token):
    created = await _create_shipment(client, customer)
    # Register a second, unrelated customer.
    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@test.io", "full_name": "Other", "password": "password1"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "other@test.io", "password": "password1"},
    )
    other_token = login.json()["access_token"]

    resp = await client.get(
        f"/api/v1/shipments/{created['id']}", headers=_auth(other_token)
    )
    assert resp.status_code == 403


async def test_full_lifecycle(client, customer, dispatcher_token, driver, admin_token):
    shipment = await _create_shipment(client, customer)
    sid = shipment["id"]
    await _create_vehicle(client, admin_token)

    # Assign driver + vehicle (dispatcher).
    assign = await client.patch(
        f"/api/v1/shipments/{sid}/assign",
        json={"driver_id": driver["id"], "vehicle_id": 1},
        headers=_auth(dispatcher_token),
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["status"] == "assigned"

    # Driver walks the shipment through its lifecycle.
    for new_status in ["picked_up", "in_transit", "out_for_delivery", "delivered"]:
        resp = await client.post(
            f"/api/v1/shipments/{sid}/events",
            json={"status": new_status, "location": "en route"},
            headers=_auth(driver["token"]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == new_status

    detail = await client.get(
        f"/api/v1/shipments/{sid}", headers=_auth(customer["token"])
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "delivered"
    # created + assigned + 4 transitions = 6 tracking events
    assert len(body["events"]) == 6


async def test_illegal_transition_rejected(client, customer, dispatcher_token, driver, admin_token):
    shipment = await _create_shipment(client, customer)
    sid = shipment["id"]
    await _create_vehicle(client, admin_token)
    await client.patch(
        f"/api/v1/shipments/{sid}/assign",
        json={"driver_id": driver["id"], "vehicle_id": 1},
        headers=_auth(dispatcher_token),
    )
    # assigned -> delivered is not allowed (must go through the chain).
    resp = await client.post(
        f"/api/v1/shipments/{sid}/events",
        json={"status": "delivered"},
        headers=_auth(driver["token"]),
    )
    assert resp.status_code == 409


async def test_assign_requires_available_capacity(
    client, customer, dispatcher_token, driver, admin_token
):
    shipment = await _create_shipment(client, customer)
    sid = shipment["id"]
    await _create_vehicle(client, admin_token, capacity=1.0)  # too small for 12.5kg
    resp = await client.patch(
        f"/api/v1/shipments/{sid}/assign",
        json={"driver_id": driver["id"], "vehicle_id": 1},
        headers=_auth(dispatcher_token),
    )
    assert resp.status_code == 409


async def test_customer_cannot_assign(client, customer, driver, admin_token):
    shipment = await _create_shipment(client, customer)
    await _create_vehicle(client, admin_token)
    resp = await client.patch(
        f"/api/v1/shipments/{shipment['id']}/assign",
        json={"driver_id": driver["id"], "vehicle_id": 1},
        headers=_auth(customer["token"]),
    )
    assert resp.status_code == 403


async def test_public_tracking(client, customer):
    created = await _create_shipment(client, customer)
    # No auth header here — public endpoint.
    resp = await client.get(f"/api/v1/track/{created['tracking_number']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracking_number"] == created["tracking_number"]
    assert body["status"] == "created"
    assert "recipient_phone" not in body  # public view omits sensitive fields


async def test_public_tracking_not_found(client):
    resp = await client.get("/api/v1/track/SS-DOESNOTEXIST")
    assert resp.status_code == 404
