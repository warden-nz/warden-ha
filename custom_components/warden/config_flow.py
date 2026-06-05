"""Config flow for Warden Electricity.

Step 1 — user enters their wardenz.com username and password.
         The flow calls /auth/login to get a token, then /auth/me
         to fetch the node (NZ) or region (AU) associated with their account.
Step 2 — confirmation screen showing the account details before saving.

If the token ever expires after setup, HA will call async_step_reauth
so the user can log in again without removing the integration.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import async_login, async_get_account, WardenAuthError, WardenConnectionError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_NODE,
    CONF_COUNTRY,
    CONF_REGION,
)

_LOGGER = logging.getLogger(__name__)

LOGIN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class WardenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles the Add Integration wizard for Warden."""

    VERSION = 1

    def __init__(self) -> None:
        # Stored between steps
        self._token: str | None = None
        self._username: str | None = None
        self._node: str | None = None
        self._tier: str | None = None
        self._country: str | None = None
        self._region: str | None = None

    # ------------------------------------------------------------------
    # Step 1: ask for username and password
    # ------------------------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                token = await async_login(
                    session,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                account = await async_get_account(session, token)
            except WardenAuthError:
                errors["base"] = "invalid_auth"
            except WardenConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Warden login")
                errors["base"] = "unknown"
            else:
                # Login succeeded — stash details and move to confirmation
                self._token = token
                self._username = account.get("username", user_input[CONF_USERNAME])
                self._node = account.get("node")
                self._tier = account.get("tier", "free")
                self._country = account.get("country", "NZ")
                self._region = account.get("region")
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=LOGIN_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2: show what we found on the account, user confirms
    # ------------------------------------------------------------------
    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Prevent duplicate entries for the same wardenz.com account
            await self.async_set_unique_id(self._username)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Warden — {self._username}",
                data={
                    CONF_TOKEN:    self._token,
                    CONF_USERNAME: self._username,
                    CONF_NODE:     self._node,
                    CONF_COUNTRY:  self._country,
                    CONF_REGION:   self._region,
                },
            )

        # Show a summary so the user can see what account + node/region was found
        # before they click Submit
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "username": self._username,
                "node":     self._node or "—",
                "tier":     self._tier,
                "country":  self._country,
                "region":   self._region or "—",
            },
            data_schema=vol.Schema({}),  # no fields — just a confirm button
        )

    # ------------------------------------------------------------------
    # Re-auth: called by HA when the coordinator gets a 401
    # Shows the login form again without removing the integration
    # ------------------------------------------------------------------
    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                token = await async_login(
                    session,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                account = await async_get_account(session, token)
            except WardenAuthError:
                errors["base"] = "invalid_auth"
            except WardenConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Warden re-auth")
                errors["base"] = "unknown"
            else:
                # Update the existing config entry with the new token
                existing_entry = await self.async_set_unique_id(
                    account.get("username")
                )
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            CONF_TOKEN:    token,
                            CONF_USERNAME: account.get("username"),
                            CONF_NODE:     account.get("node"),
                            CONF_COUNTRY:  account.get("country", "NZ"),
                            CONF_REGION:   account.get("region"),
                        },
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=LOGIN_SCHEMA,
            errors=errors,
        )