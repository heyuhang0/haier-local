"""DataUpdateCoordinator for the local washer."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import decoder
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class WasherCoordinator(DataUpdateCoordinator[dict]):
    """Polls the washer over TCP 56800 and decodes the class-0501 report."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
        self.device_id = entry.data[CONF_DEVICE_ID]
        self.local_key = entry.options.get(
            CONF_LOCAL_KEY, entry.data[CONF_LOCAL_KEY]
        )
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        interval = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, int(interval)))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(
                decoder.read_state, self.host, self.device_id, self.local_key
            )
        except Exception as err:  # noqa: BLE001 - surface every transport/decode failure
            raise UpdateFailed(f"local washer read failed: {err}") from err
