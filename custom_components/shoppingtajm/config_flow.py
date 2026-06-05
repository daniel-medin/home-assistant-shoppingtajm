"""Config flow for ShoppingTajm."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientSession
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ShoppingTajmApiClient,
    ShoppingTajmAuthError,
    ShoppingTajmConnectionError,
    ShoppingTajmError,
    normalize_server_url,
    unique_id_for_config,
)
from .const import CONF_PAT, CONF_SERVER_URL, DEFAULT_SERVER_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERVER_URL, default=DEFAULT_SERVER_URL): str,
        vol.Required(CONF_PAT): str,
    }
)


async def validate_input(
    _hass: HomeAssistant,
    session: ClientSession,
    data: dict[str, str],
) -> dict[str, str]:
    """Validate user input by connecting to ShoppingTajm."""
    server_url = normalize_server_url(data[CONF_SERVER_URL])
    token = data[CONF_PAT].strip()
    api = ShoppingTajmApiClient(session, server_url, token)

    status = await api.async_validate_credentials()
    user_key = _extract_user_key(status) or api.token_fingerprint
    return {
        "title": "Shoppingtajm",
        "server_url": server_url,
        "unique_id": unique_id_for_config(server_url, user_key),
    }


class ShoppingTajmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for ShoppingTajm."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_input = {
                CONF_SERVER_URL: normalize_server_url(user_input[CONF_SERVER_URL]),
                CONF_PAT: str(user_input[CONF_PAT]).strip(),
            }
            try:
                info = await validate_input(
                    self.hass,
                    async_get_clientsession(self.hass),
                    normalized_input,
                )
            except ShoppingTajmAuthError:
                errors["base"] = "invalid_auth"
            except ShoppingTajmConnectionError:
                errors["base"] = "cannot_connect"
            except ShoppingTajmError:
                _LOGGER.exception("Unexpected ShoppingTajm validation error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data=normalized_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


def _extract_user_key(status: dict[str, Any] | None) -> str | None:
    """Extract a non-secret user/server identity from the status payload."""
    if not status:
        return None
    for key in ("userId", "UserId", "user_id", "email", "Email", "accountId"):
        value = status.get(key)
        if value:
            return str(value)
    return None
