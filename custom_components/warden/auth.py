"""Warden authentication helpers.

Handles the login call and token validation separately from the
price-polling coordinator so config_flow can use them without
spinning up a full coordinator first.
"""
from __future__ import annotations

import aiohttp

from .const import API_BASE_URL, ENDPOINT_LOGIN, ENDPOINT_ME


class WardenAuthError(Exception):
    """Raised when login fails or the token is rejected."""


class WardenConnectionError(Exception):
    """Raised when we can't reach api.wardenz.com at all."""


async def async_login(session: aiohttp.ClientSession, username: str, password: str) -> str:
    """POST credentials to /auth/login and return the access token string.

    Raises WardenAuthError if the credentials are wrong.
    Raises WardenConnectionError if the server can't be reached.
    """
    try:
        async with session.post(
            f"{API_BASE_URL}{ENDPOINT_LOGIN}",
            json={"username": username, "password": password},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise WardenAuthError("Invalid username or password")
            resp.raise_for_status()
            data = await resp.json()
            return data["access_token"]

    except WardenAuthError:
        raise
    except aiohttp.ClientConnectorError as err:
        raise WardenConnectionError(f"Cannot reach api.wardenz.com: {err}") from err
    except Exception as err:
        raise WardenConnectionError(f"Unexpected error during login: {err}") from err


async def async_get_account(session: aiohttp.ClientSession, token: str) -> dict:
    """GET /auth/me using the token and return the account dict.

    Returns something like: {"username": "benj", "node": "OTA2201", "tier": "free"}

    Raises WardenAuthError if the token has expired or been revoked.
    Raises WardenConnectionError if the server can't be reached.
    """
    try:
        async with session.get(
            f"{API_BASE_URL}{ENDPOINT_ME}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 401:
                raise WardenAuthError("Token expired or revoked — please log in again")
            resp.raise_for_status()
            return await resp.json()

    except WardenAuthError:
        raise
    except aiohttp.ClientConnectorError as err:
        raise WardenConnectionError(f"Cannot reach api.wardenz.com: {err}") from err
    except Exception as err:
        raise WardenConnectionError(f"Unexpected error fetching account: {err}") from err
