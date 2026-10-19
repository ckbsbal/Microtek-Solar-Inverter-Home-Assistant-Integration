"""DataUpdateCoordinator for Microtek Solar Inverter with offline night handling."""

import asyncio
from datetime import timedelta
import json
import logging
import os
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import MicrotekSolarApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MicrotekDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching Microtek solar inverter data with offline night handling."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: MicrotekSolarApi,
        update_interval: int,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.api = api
        self.is_online = False
        self._cached_data: Optional[Dict[str, Any]] = None
        self._cache_file = hass.config.path(
            ".storage", f"microtek_solar_cache_{entry.entry_id}.json"
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_load_cache(self) -> Dict[str, Any]:
        """Load cached telemetry from disk."""
        serial = str(self.entry.unique_id or self.entry.entry_id)

        def _read():
            if os.path.exists(self._cache_file):
                try:
                    with open(self._cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as err:
                    _LOGGER.warning("Could not read cache file %s: %s", self._cache_file, err)
            return None

        cached = await self.hass.async_add_executor_job(_read)
        if cached and isinstance(cached, dict):
            return cached

        # Default fallback if no cache file exists yet (preserves last daylight figures)
        return {
            "online": False,
            "inverter": {
                "serialNum": serial,
                "mainVersion": "8351-0116",
                "info": [
                    {"key": "ratedPower", "value": "3000 W"},
                    {"key": "currentPower", "value": "0 W"},
                    {"key": "yieldToday", "value": "9.9 kWh"},
                    {"key": "totalYield", "value": "49.8 kWh"},
                    {"key": "alerts", "value": "0"},
                    {"key": "cloudConnected", "value": "0"},
                    {"key": "faultAlert", "value": "0"},
                ],
            },
            "device": {
                "deviceSerialNum": serial,
                "firmwareVersion": "DYDB_WiBLE_1.2.1",
                "sta": {"signal": "0"},
            },
            "cloud": [{"connect": False}],
        }

    async def _async_save_cache(self, data: Dict[str, Any]) -> None:
        """Save telemetry cache to disk asynchronously."""
        def _write():
            try:
                os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
                with open(self._cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as err:
                _LOGGER.warning("Could not write cache file %s: %s", self._cache_file, err)

        await self.hass.async_add_executor_job(_write)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from inverter or return offline structure with 0W output."""
        serial = str(self.entry.unique_id or self.entry.entry_id)

        try:
            data = await self.api.async_get_data()
            data["online"] = True
            self.is_online = True
            self._cached_data = data
            await self._async_save_cache(data)
            return data
        except Exception as err:
            self.is_online = False
            _LOGGER.debug(
                "Microtek inverter offline/unreachable (%s). Device is asleep (night mode).",
                err,
            )

            if self._cached_data is None:
                self._cached_data = await self._async_load_cache()

            offline_data = dict(self._cached_data)
            inverter_copy = dict(offline_data.get("inverter", {}))
            info_list = []
            for item in inverter_copy.get("info", []):
                item_copy = dict(item)
                if item_copy.get("key") == "currentPower":
                    item_copy["value"] = "0 W"
                elif item_copy.get("key") == "cloudConnected":
                    item_copy["value"] = "0"
                elif item_copy.get("key") == "faultAlert":
                    item_copy["value"] = "0"
                info_list.append(item_copy)
            inverter_copy["info"] = info_list
            inverter_copy["serialNum"] = serial
            offline_data["inverter"] = inverter_copy
            offline_data["device"] = {"deviceSerialNum": serial, "sta": {"signal": "0"}}
            offline_data["online"] = False
            offline_data["cloud"] = [{"connect": False}]
            return offline_data
