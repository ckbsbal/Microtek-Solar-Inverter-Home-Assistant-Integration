"""Config flow for Microtek Solar Inverter integration."""

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MicrotekSolarApi
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Clamp(min=10, max=300)
        ),
    }
)


class MicrotekSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Microtek Solar Inverter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD].strip()

            session = async_get_clientsession(self.hass)
            api = MicrotekSolarApi(
                host=host,
                username=username,
                password=password,
                session=session,
            )

            try:
                data = await api.async_get_data()
                inverter = data.get("inverter", {})
                device = data.get("device", {})
                unique_id = inverter.get("serialNum") or device.get("deviceSerialNum") or host

                await self.async_set_unique_id(str(unique_id))
                self._abort_if_unique_id_configured()

                model = inverter.get("model", "MTK GTI 3kW")
                title = f"Microtek Solar ({unique_id})"

                return self.async_create_entry(title=title, data=user_input)

            except PermissionError:
                errors["base"] = "invalid_auth"
            except (ConnectionError, aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Connection error connecting to Microtek inverter: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow: %s", ex)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
