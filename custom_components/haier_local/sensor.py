"""Sensors for the local washer, driven by specs.py."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import decoder
from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import WasherCoordinator
from .profile import DEVICE
from .specs import (
    SensorSpec,
    as_bool,
)

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


class WasherSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WasherCoordinator, entry: ConfigEntry,
                 description: SensorSpec) -> None:
        super().__init__(coordinator)
        self._spec = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_icon = description.icon
        self._attr_state_class = (
            SensorStateClass(description.state_class)
            if description.state_class else None
        )
        if description.enum:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = DEVICE.options_for(description.enum)
        elif description.device_class:
            self._attr_device_class = SensorDeviceClass(description.device_class)
        self._attr_entity_category = (
            EntityCategory.DIAGNOSTIC if description.diagnostic else None
        )
        self._attr_entity_registry_enabled_default = description.enabled_default
        self._attr_device_info = _device_info(entry)

    def _raw_value(self):
        state = self.coordinator.data or {}
        spec = self._spec
        if spec.value_fn is not None:
            return spec.value_fn(state)
        return state.get(spec.source) if spec.source else None

    @property
    def native_value(self):
        raw = self._raw_value()
        if self._spec.enum:
            return DEVICE.token_for(self._spec.enum, raw)
        return raw

    @property
    def extra_state_attributes(self) -> dict | None:
        state = self.coordinator.data or {}
        spec = self._spec
        attrs: dict = {}
        if spec.enum:
            raw = self._raw_value()
            attrs["raw_value"] = raw
            attrs["label_en"] = DEVICE.labels_for(spec.enum, raw, "en")
            attrs["label_zh"] = DEVICE.labels_for(spec.enum, raw, "zh")
        if spec.attributes_fn is not None:
            attrs.update(spec.attributes_fn(state))
        return attrs or None


class RawStateSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    """All decoded values, diagnostic and disabled by default."""

    _attr_has_entity_name = True
    _attr_translation_key = "raw_state"
    _attr_icon = "mdi:code-json"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: WasherCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_raw_state"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        state = self.coordinator.data or {}
        return sum(1 for key in DEVICE.raw_state_fields if state.get(key) is not None)

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data or {}
        attrs = {key: state.get(key) for key in DEVICE.raw_state_fields}
        for key, value in state.items():
            if key.startswith("_"):
                attrs[key.lstrip("_")] = value
        return attrs


class FeatureFlagsSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    """Grouped optional feature flags, diagnostic and disabled by default."""

    _attr_has_entity_name = True
    _attr_translation_key = "feature_flags"
    _attr_icon = "mdi:toggle-switch-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: WasherCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_DEVICE_ID]}_feature_flags"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self):
        state = self.coordinator.data or {}
        return sum(1 for field, _en, _zh in DEVICE.feature_flags if as_bool(state.get(field)))

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data or {}
        return {english: as_bool(state.get(field)) for field, english, _zh in DEVICE.feature_flags}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WasherCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("creating %d sensor entities", len(DEVICE.sensors) + 2)
    entities = [WasherSensor(coordinator, entry, spec) for spec in DEVICE.sensors]
    entities.append(RawStateSensor(coordinator, entry))
    entities.append(FeatureFlagsSensor(coordinator, entry))
    async_add_entities(entities)
