import pytest

from tests.conftest import _auth

pytestmark = pytest.mark.asyncio


async def test_register_and_login(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "jane@test.io",
            "full_name": "Jane Doe",
            "password": "supersecret",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "jane@test.io"
    assert body["role"] == "customer"
    assert "id" in body

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "jane@test.io", "password": "supersecret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "jane@test.io"


async def test_duplicate_email_rejected(client):
    payload = {
        "email": "dup@test.io",
        "full_name": "Dup",
        "password": "supersecret",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "x@test.io", "full_name": "X", "password": "rightpass1"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "x@test.io", "password": "wrongpass"},
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_short_password_rejected(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@test.io", "full_name": "S", "password": "abc"},
    )
    assert resp.status_code == 422
