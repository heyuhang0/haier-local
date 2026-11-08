"""Entity construction/property contract against a real Home Assistant.

The `ha-contract` CI job installs Home Assistant 2026.11.0 and runs this file.
Locally it is skipped when Home Assistant is not installed:

    pytest tests/test_ha_contract.py

This checks construction and entity-description/property access, not full
EntityPlatform registration.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "custom_components"))

from haier_local import profile  # noqa: E402
from haier_local.binary_sensor import WasherBinarySensor  # noqa: E402
from haier_local.const import CONF_DEVICE_ID  # noqa: E402
from haier_local.sensor import WasherSensor  # noqa: E402


class _Entry:
    title = "Washer"
    data = {CONF_DEVICE_ID: "AABBCCDDEEFF"}


def _coordinator(data: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(data=data or {}, hass=None)


def test_sensor_entities_satisfy_ha_description_contract() -> None:
    for spec in profile.DEVICE.sensors:
        entity = WasherSensor(_coordinator(), _Entry(), spec)
        assert entity.entity_registry_visible_default is True
        assert entity.entity_registry_enabled_default is spec.enabled_default
        assert entity.translation_key == spec.key
        assert not hasattr(entity, "_attr_name")
        assert entity.suggested_unit_of_measurement is None
        assert entity.force_update is False
        assert entity.translation_placeholders == {}
        assert isinstance(entity.extra_state_attributes, (dict, type(None)))
        assert not hasattr(entity, "entity_description")


def test_binary_entities_satisfy_ha_description_contract() -> None:
    for spec in profile.DEVICE.binary_sensors:
        entity = WasherBinarySensor(_coordinator(), _Entry(), spec)
        assert entity.entity_registry_visible_default is True
        assert entity.entity_registry_enabled_default is spec.enabled_default
        assert entity.translation_key == spec.key
        assert not hasattr(entity, "_attr_name")
        assert entity.force_update is False
        assert entity.translation_placeholders == {}
        assert not hasattr(entity, "entity_description")


def test_problem_binary_semantics() -> None:
    spec = next(spec for spec in profile.DEVICE.binary_sensors if spec.key == "problem")
    coordinator = _coordinator({"_alarm_count": 0})
    entity = WasherBinarySensor(coordinator, _Entry(), spec)
    assert entity.is_on is False
    coordinator.data = {"_alarm_count": 1}
    assert entity.is_on is True
