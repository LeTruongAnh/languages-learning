import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_me(client):
    res = await client.post(
        "/auth/register",
        json={"email": "phong@example.com", "password": "sup3rsecret", "displayName": "Phong"},
    )
    assert res.status_code == 201
    assert res.json()["email"] == "phong@example.com"

    res = await client.post(
        "/auth/login", json={"email": "phong@example.com", "password": "sup3rsecret"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["accessToken"] and body["refreshToken"]

    res = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['accessToken']}"}
    )
    assert res.status_code == 200
    assert res.json()["displayName"] == "Phong"


async def test_login_wrong_password_generic_error(client):
    await client.post(
        "/auth/register", json={"email": "a@example.com", "password": "sup3rsecret"}
    )
    res = await client.post(
        "/auth/login", json={"email": "a@example.com", "password": "wrong-pass1"}
    )
    assert res.status_code == 401
    # Same message whether email exists or not — no user enumeration.
    res2 = await client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}
    )
    assert res2.status_code == 401
    assert res.json()["detail"] == res2.json()["detail"]


async def test_weak_password_rejected(client):
    res = await client.post(
        "/auth/register", json={"email": "weak@example.com", "password": "12345678"}
    )
    assert res.status_code == 422


async def test_refresh_rotation_and_reuse_detection(client):
    await client.post(
        "/auth/register", json={"email": "rot@example.com", "password": "sup3rsecret"}
    )
    login = (await client.post(
        "/auth/login", json={"email": "rot@example.com", "password": "sup3rsecret"}
    )).json()
    old_refresh = login["refreshToken"]

    # Rotate: old refresh -> new pair
    res = await client.post("/auth/refresh", json={"refreshToken": old_refresh})
    assert res.status_code == 200
    new_refresh = res.json()["refreshToken"]
    assert new_refresh != old_refresh

    # Reuse of the rotated (revoked) token => 401 and family revoked
    res = await client.post("/auth/refresh", json={"refreshToken": old_refresh})
    assert res.status_code == 401

    # The new token was revoked too (same family)
    res = await client.post("/auth/refresh", json={"refreshToken": new_refresh})
    assert res.status_code == 401


async def test_protected_route_requires_token(client):
    res = await client.get("/languages")
    assert res.status_code == 401
