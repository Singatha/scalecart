from uuid import UUID

import jwt
from app.models import Role, User
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def register(client, email: str = "ada@example.com") -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "CorrectHorse9",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_registration_login_profile_and_duplicate_email(client) -> None:
    weak_password = await client.post(
        "/auth/register",
        json={
            "email": "weak@example.com",
            "password": "alllowercase",
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    )
    assert weak_password.status_code == 422
    assert weak_password.json()["error"]["code"] == "validation_error"

    authentication = await register(client, "Ada@Example.com")
    assert authentication["user"]["email"] == "ada@example.com"
    assert authentication["user"]["roles"] == ["customer"]
    assert authentication["expires_in"] == 900
    claims = jwt.decode(
        authentication["access_token"],
        "development-only-change-me-use-32-bytes",
        algorithms=["HS256"],
        audience="scalecart-storefront",
        issuer="scalecart",
    )
    assert claims["roles"] == ["customer"]

    duplicate = await client.post(
        "/auth/register",
        json={
            "email": "ada@example.com",
            "password": "AnotherStrong9",
            "first_name": "Ada",
            "last_name": "Byron",
        },
    )
    assert duplicate.status_code == 409

    invalid_login = await client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "wrong"}
    )
    assert invalid_login.status_code == 401

    login = await client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "CorrectHorse9"}
    )
    assert login.status_code == 200
    access_token = login.json()["access_token"]

    profile = await client.patch(
        "/users/me",
        headers=bearer(access_token),
        json={"first_name": "Augusta", "phone": "+27 11 555 0199"},
    )
    assert profile.status_code == 200
    assert profile.json()["first_name"] == "Augusta"
    assert profile.json()["phone"] == "+27 11 555 0199"


async def test_refresh_tokens_are_rotated_and_cannot_be_replayed(client) -> None:
    authentication = await register(client)
    original = authentication["refresh_token"]

    rotated = await client.post("/auth/refresh", json={"refresh_token": original})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != original

    replay = await client.post("/auth/refresh", json={"refresh_token": original})
    assert replay.status_code == 401

    current = rotated.json()["refresh_token"]
    logout = await client.post("/auth/logout", json={"refresh_token": current})
    assert logout.status_code == 204
    after_logout = await client.post("/auth/refresh", json={"refresh_token": current})
    assert after_logout.status_code == 401


async def test_address_crud_enforces_ownership_and_one_default(client) -> None:
    first_user = await register(client)
    first_headers = bearer(first_user["access_token"])
    second_user = await register(client, "grace@example.com")
    second_headers = bearer(second_user["access_token"])

    home = await client.post(
        "/users/me/addresses",
        headers=first_headers,
        json={
            "label": "Home",
            "recipient_name": "Ada Lovelace",
            "line1": "12 Computing Lane",
            "city": "Cape Town",
            "region": "Western Cape",
            "postal_code": "8001",
            "country_code": "za",
        },
    )
    assert home.status_code == 201
    assert home.json()["is_default"] is True
    assert home.json()["country_code"] == "ZA"

    office = await client.post(
        "/users/me/addresses",
        headers=first_headers,
        json={
            "label": "Office",
            "recipient_name": "Ada Lovelace",
            "line1": "1 Logic Road",
            "city": "Johannesburg",
            "region": "Gauteng",
            "postal_code": "2000",
            "country_code": "ZA",
            "is_default": True,
        },
    )
    assert office.status_code == 201
    addresses = (await client.get("/users/me/addresses", headers=first_headers)).json()
    assert [address["label"] for address in addresses if address["is_default"]] == ["Office"]

    cannot_edit = await client.patch(
        f"/users/me/addresses/{home.json()['id']}",
        headers=second_headers,
        json={"city": "Pretoria"},
    )
    assert cannot_edit.status_code == 404

    deleted = await client.delete(
        f"/users/me/addresses/{office.json()['id']}", headers=first_headers
    )
    assert deleted.status_code == 204
    addresses = (await client.get("/users/me/addresses", headers=first_headers)).json()
    assert addresses[0]["label"] == "Home"
    assert addresses[0]["is_default"] is True


async def test_only_admins_can_assign_known_roles(client, session_factory) -> None:
    admin_auth = await register(client, "admin@example.com")
    customer_auth = await register(client, "customer@example.com")
    customer_id = customer_auth["user"]["id"]

    forbidden = await client.put(
        f"/users/{customer_id}/roles",
        headers=bearer(customer_auth["access_token"]),
        json={"roles": ["admin"]},
    )
    assert forbidden.status_code == 403

    async with session_factory() as session:
        admin = await session.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == UUID(admin_auth["user"]["id"]))
        )
        admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
        assert admin is not None and admin_role is not None
        admin.roles = [admin_role]
        await session.commit()

    assigned = await client.put(
        f"/users/{customer_id}/roles",
        headers=bearer(admin_auth["access_token"]),
        json={"roles": ["customer", "admin"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["roles"] == ["admin", "customer"]

    unknown = await client.put(
        f"/users/{customer_id}/roles",
        headers=bearer(admin_auth["access_token"]),
        json={"roles": ["owner"]},
    )
    assert unknown.status_code == 422
