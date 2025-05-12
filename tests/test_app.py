import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from app.main import app
from app.db import users, events

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    # Clean out users and events before each test
    users.delete_many({})
    events.delete_many({})


@pytest.fixture
def new_user():
    return {
        "email": "user@example.com",
        "password": "Secret123!",
        "full_name": "Test User",
    }


@pytest.fixture
def register_and_login(new_user):
    # Register
    resp = client.post("/auth/register", json=new_user)
    assert resp.status_code == 201
    # Login
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": new_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return token


def test_register_success(new_user):
    resp = client.post("/auth/register", json=new_user)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == new_user["email"]
    assert "id" in body and "created_at" in body


def test_register_duplicate(new_user):
    client.post("/auth/register", json=new_user)
    resp = client.post("/auth/register", json=new_user)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(new_user):
    client.post("/auth/register", json=new_user)
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": new_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and data["token_type"] == "bearer"


def test_login_fail(new_user):
    client.post("/auth/register", json=new_user)
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": "WrongPass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


def test_recover_and_reset_password(monkeypatch, new_user):
    # Register user first
    client.post("/auth/register", json=new_user)
    sent = {}

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr("app.main.send_recovery_email", fake_send)

    resp = client.post("/auth/recover-password", json={"email": new_user["email"]})
    assert resp.status_code == 200
    assert sent["email"] == new_user["email"]
    assert "token" in sent

    # Reset using token
    new_pass = "NewSecret456!"
    resp = client.post(
        "/auth/reset-password",
        params={"token": sent["token"], "new_password": new_pass},
    )
    assert resp.status_code == 200
    assert "Password updated" in resp.json()["msg"]

    # Now login with new password
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": new_pass},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200


def test_profile_get_and_update(register_and_login):
    token = register_and_login
    headers = {"Authorization": f"Bearer {token}"}

    # Get profile
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["full_name"] == "Test User"

    # Update profile
    resp = client.put("/users/me", json={"full_name": "Updated Name"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


def test_change_password(register_and_login, new_user):
    token = register_and_login
    headers = {"Authorization": f"Bearer {token}"}

    # Change password with wrong old password
    resp = client.put(
        "/users/me/password",
        json={"old_password": "WrongOld", "new_password": "Whatever1!"},
        headers=headers,
    )
    assert resp.status_code == 400

    # Change with correct old password
    resp = client.put(
        "/users/me/password",
        json={"old_password": new_user["password"], "new_password": "Changed123!"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Password changed" in resp.json()["msg"]

    # Logout and login with new password
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": "Changed123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200


def test_booking_association(register_and_login):
    token = register_and_login
    headers = {"Authorization": f"Bearer {token}"}

    # Create two bookings
    slot1 = datetime.now(timezone.utc) + timedelta(days=1)
    slot2 = datetime.now(timezone.utc) + timedelta(days=2)
    resp1 = client.post(f"/bookings?slot={slot1.isoformat()}", headers=headers)
    resp2 = client.post(f"/bookings?slot={slot2.isoformat()}", headers=headers)
    assert resp1.status_code == 201
    assert resp2.status_code == 201

    # List bookings returns only these two
    resp = client.get("/bookings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["bookings"]
    assert len(data) == 2
    returned_slots = {b["slot"] for b in data}
    assert slot1.isoformat().replace("+00:00", " 00:00") in returned_slots
    assert slot2.isoformat().replace("+00:00", " 00:00") in returned_slots


def test_booking_not_visible_to_other_user(register_and_login, new_user):
    token1 = register_and_login
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Create a booking for user1
    slot = datetime.now(timezone.utc) + timedelta(days=3)
    client.post(f"/bookings?slot={slot.isoformat()}", headers=headers1)

    # Register and login a second user
    other = {
        "email": "other@example.com",
        "password": "OtherPass1!",
        "full_name": "Other",
    }
    client.post("/auth/register", json=other)
    resp = client.post(
        "/auth/token",
        data={"username": other["email"], "password": other["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token2 = resp.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Second user sees no bookings
    resp = client.get("/bookings", headers=headers2)
    assert resp.status_code == 200
    assert resp.json()["bookings"] == []
