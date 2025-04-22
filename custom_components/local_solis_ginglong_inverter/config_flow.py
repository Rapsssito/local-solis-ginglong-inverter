"""Config flow for the integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, LISTENING_PORT

if TYPE_CHECKING:
    from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(LISTENING_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }
)


async def validate_input(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # Could test if the port is available here, but not necessary for now.
    return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        errors = {}

        try:
            await validate_input(user_input)
        except CannotCreateServerError:
            errors["base"] = "cannot_create_server"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title="Solis/Ginlong Local Logger Server", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)


class CannotCreateServerError(HomeAssistantError):
    """Error to indicate we cannot create a server."""
