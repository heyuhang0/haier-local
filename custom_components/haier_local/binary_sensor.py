"""Binary sensors for the local washer, driven by specs.py."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import WasherCoordinator
from .profile import DEVICE
from .specs import BinarySpec, as_bool

_LOGGER = logging.getLogger(__name__)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    device_id = entry.data[CONF_DEVICE_ID]
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=entry.title,
        manufacturer=DEVICE.manufacturer,
        model=DEVICE.model,
        serial_number=device_id,
    )


class WasherBinarySensor(CoordinatorEntity[WasherCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCoordinator, entry: ConfigEntry,
                 description: BinarySpec) -> None:
        super().__init__(coordinator)
        self._spec = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_{description.key}"
        self._attr_icon = description.icon
        if description.device_class:
            self._attr_device_class = BinarySensorDeviceClass(description.device_class)
        self._attr_entity_category = (
            EntityCategory.DIAGNOSTIC if description.diagnostic else None
        )
        self._attr_entity_registry_enabled_default = description.enabled_default
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data or {}
        spec = self._spec
        if spec.value_fn is not None:
            return spec.value_fn(state)
        return as_bool(state.get(spec.source)) if spec.source else None

    @property
    def extra_state_attributes(self) -> dict | None:
        state = self.coordinator.data or {}
        if self._spec.attributes_fn is None:
            return None
        return self._spec.attributes_fn(state)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WasherCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("creating %d binary sensor entities", len(DEVICE.binary_sensors))
    async_add_entities(
        WasherBinarySensor(coordinator, entry, spec) for spec in DEVICE.binary_sensors
    )
