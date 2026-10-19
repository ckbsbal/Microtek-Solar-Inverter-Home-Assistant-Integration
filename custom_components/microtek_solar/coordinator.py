"""DataUpdateCoordinator for Microtek Solar Inverter."""

from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MicrotekSolarApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MicrotekDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching Microtek solar inverter data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: MicrotekSolarApi,
        update_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the inverter via web API."""
        try:
            return await self.api.async_get_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Microtek inverter: {err}") from err
