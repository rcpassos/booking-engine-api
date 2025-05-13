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
def register_and_login(new_user, api_key_header):
    # Register
    resp = client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    assert resp.status_code == 201
    # Login
    resp = client.post(
        "/auth/token",
        data={
            "username": new_user["email"],
            "password": new_user["password"],
        },
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return token


def test_register_success(new_user, api_key_header):
    resp = client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == new_user["email"]
    assert "id" in body and "created_at" in body


def test_register_duplicate(new_user, api_key_header):
    client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    resp = client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(new_user, api_key_header):
    client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    resp = client.post(
        "/auth/token",
        data={"username": new_user["email"], "password": new_user["password"]},
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and data["token_type"] == "bearer"


def test_login_fail(new_user, api_key_header):
    client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    resp = client.post(
        "/auth/token",
        data={
            "username": new_user["email"],
            "password": "WrongPass",
        },
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 401


def test_recover_and_reset_password(monkeypatch, new_user, api_key_header):
    # Register user first
    client.post(
        "/auth/register",
        json=new_user,
        headers=api_key_header,
    )
    sent = {}

    def fake_send(email, token):
        sent["email"] = email
        sent["token"] = token

    monkeypatch.setattr("app.main.send_recovery_email", fake_send)

    resp = client.post(
        "/auth/recover-password",
        json={"email": new_user["email"]},
        headers=api_key_header,
    )
    assert resp.status_code == 200
    assert sent["email"] == new_user["email"]
    assert "token" in sent

    # Reset using token
    new_pass = "NewSecret456!"
    resp = client.post(
        "/auth/reset-password",
        params={
            "token": sent["token"],
            "new_password": new_pass,
        },
        headers=api_key_header,
    )
    assert resp.status_code == 200
    assert "Password updated" in resp.json()["msg"]

    # Now login with new password
    resp = client.post(
        "/auth/token",
        data={
            "username": new_user["email"],
            "password": new_pass,
        },
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200


def test_profile_get_and_update(register_and_login, api_key_header):
    token = register_and_login
    headers = {
        **api_key_header,
        "Authorization": f"Bearer {token}",
    }

    # Get profile
    resp = client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["full_name"] == "Test User"

    # Update profile
    resp = client.put(
        "/users/me",
        json={"full_name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


def test_change_password(register_and_login, new_user, api_key_header):
    token = register_and_login
    headers = {
        **api_key_header,
        "Authorization": f"Bearer {token}",
    }

    # Change password with wrong old password
    resp = client.put(
        "/users/me/password",
        json={
            "old_password": "WrongOld",
            "new_password": "Whatever1!",
        },
        headers=headers,
    )
    assert resp.status_code == 400

    # Change with correct old password
    resp = client.put(
        "/users/me/password",
        json={
            "old_password": new_user["password"],
            "new_password": "Changed123!",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Password changed" in resp.json()["msg"]

    # Logout and login with new password
    resp = client.post(
        "/auth/token",
        data={
            "username": new_user["email"],
            "password": "Changed123!",
        },
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200


def test_booking_association(register_and_login, api_key_header):
    token = register_and_login
    headers = {
        **api_key_header,
        "Authorization": f"Bearer {token}",
    }

    # Create two bookings
    slot1 = datetime.now(timezone.utc) + timedelta(days=1)
    slot2 = datetime.now(timezone.utc) + timedelta(days=2)
    resp1 = client.post(
        f"/bookings?slot={slot1.isoformat()}",
        headers=headers,
    )
    resp2 = client.post(
        f"/bookings?slot={slot2.isoformat()}",
        headers=headers,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201

    # List bookings returns only these two
    resp = client.get(
        "/bookings",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["bookings"]
    assert len(data) == 2
    returned_slots = {b["slot"] for b in data}
    assert slot1.isoformat().replace("+00:00", " 00:00") in returned_slots
    assert slot2.isoformat().replace("+00:00", " 00:00") in returned_slots


def test_booking_not_visible_to_other_user(register_and_login, api_key_header):
    token1 = register_and_login
    headers1 = {
        **api_key_header,
        "Authorization": f"Bearer {token1}",
    }

    # Create a booking for user1
    slot = datetime.now(timezone.utc) + timedelta(days=3)
    client.post(
        f"/bookings?slot={slot.isoformat()}",
        headers=headers1,
    )

    # Register the second user (include API key)
    other = {
        "email": "other@example.com",
        "password": "OtherPass1!",
        "full_name": "Other",
    }
    client.post(
        "/auth/register",
        json=other,
        headers=api_key_header,  # <<< add this
    )

    # Login the second user (also include API key + content type)
    resp = client.post(
        "/auth/token",
        data={
            "username": other["email"],
            "password": other["password"],
        },
        headers={
            **api_key_header,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200  # sanity check
    token2 = resp.json()["access_token"]

    headers2 = {
        **api_key_header,
        "Authorization": f"Bearer {token2}",
    }

    # Second user should see no bookings
    resp = client.get("/bookings", headers=headers2)
    assert resp.status_code == 200
    assert resp.json()["bookings"] == []
