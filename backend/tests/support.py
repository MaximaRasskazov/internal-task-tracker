"""Helpers for authenticated API integration tests; all credentials are test-only."""

from typing import TYPE_CHECKING

from httpx import AsyncClient

if TYPE_CHECKING:
    from app.db.domain import User

ORIGIN = "http://localhost:5173"
TEST_PASSWORD = "Integration-tests-only-password-42"


async def login(
    client: AsyncClient, user: "User | str", password: str = TEST_PASSWORD
) -> dict[str, str]:
    """Switch the client session and attach CSRF headers for subsequent writes."""
    client.headers.pop("X-CSRF-Token", None)
    client.headers["Origin"] = ORIGIN
    email = user if isinstance(user, str) else user.email
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    headers = {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}
    client.headers.update(headers)
    return headers
