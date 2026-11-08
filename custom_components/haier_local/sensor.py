"""Sensors for the local washer, driven by specs.py."""
from __future__ import annotations

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
from .enum_defs import labels_for, options_for, token_for
from .specs import (
    ALL_SENSORS,
    FEATURE_FLAGS,
    RAW_STATE_FIELDS,
    SensorSpec,
    as_bool,
)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    device_id = entry.data[CONF_DEVICE_ID]
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=entry.title,
        manufacturer="Haier / Casarte",
        model="CE AB13LWTUWCU1",
        serial_number=device_id,
    )


class WasherSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = None
    entity_description: SensorSpec

    def __init__(self, coordinator: WasherCoordinator, entry: ConfigEntry,
                 description: SensorSpec) -> None:
        super().__init__(coordinator)
        self.entity_description = description
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
            self._attr_options = options_for(description.enum)
        elif description.device_class:
            self._attr_device_class = SensorDeviceClass(description.device_class)
        self._attr_entity_category = (
            EntityCategory.DIAGNOSTIC if description.diagnostic else None
        )
        self._attr_entity_registry_enabled_default = description.enabled_default
        self._attr_device_info = _device_info(entry)

    def _raw_value(self):
        state = self.coordinator.data or {}
        spec = self.entity_description
        if spec.value_fn is not None:
            return spec.value_fn(state)
        return state.get(spec.source) if spec.source else None

    @property
    def native_value(self):
        raw = self._raw_value()
        if self.entity_description.enum:
            return token_for(self.entity_description.enum, raw)
        return raw

    @property
    def extra_state_attributes(self) -> dict | None:
        state = self.coordinator.data or {}
        spec = self.entity_description
        attrs: dict = {}
        if spec.enum:
            raw = self._raw_value()
            attrs["raw_value"] = raw
            attrs["label_en"] = labels_for(spec.enum, raw, "en")
            attrs["label_zh"] = labels_for(spec.enum, raw, "zh")
        if spec.attributes_fn is not None:
            attrs.update(spec.attributes_fn(state))
        return attrs or None


class RawStateSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    """All decoded values, diagnostic and disabled by default."""

    _attr_has_entity_name = True
    _attr_translation_key = "raw_state"
    _attr_name = None
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
        return sum(1 for key in RAW_STATE_FIELDS if state.get(key) is not None)

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data or {}
        attrs = {key: state.get(key) for key in RAW_STATE_FIELDS}
        for key, value in state.items():
            if key.startswith("_"):
                attrs[key.lstrip("_")] = value
        return attrs


class FeatureFlagsSensor(CoordinatorEntity[WasherCoordinator], SensorEntity):
    """Grouped optional feature flags, diagnostic and disabled by default."""

    _attr_has_entity_name = True
    _attr_translation_key = "feature_flags"
    _attr_name = None
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
        return sum(1 for field, _en, _zh in FEATURE_FLAGS if as_bool(state.get(field)))

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.data or {}
        return {english: as_bool(state.get(field)) for field, english, _zh in FEATURE_FLAGS}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WasherCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [WasherSensor(coordinator, entry, spec) for spec in ALL_SENSORS]
    entities.append(RawStateSensor(coordinator, entry))
    entities.append(FeatureFlagsSensor(coordinator, entry))
    async_add_entities(entities)
