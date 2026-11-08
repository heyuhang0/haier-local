"""Contract check against a real Home Assistant installation.

CI does not install Home Assistant (the static tests run without it), so this
file is skipped there. Run it in an environment with Home Assistant installed:

    pytest tests/test_ha_contract.py
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


def _coordinator() -> SimpleNamespace:
    return SimpleNamespace(data={}, hass=None)


def test_sensor_entities_satisfy_ha_description_contract() -> None:
    for spec in profile.DEVICE.sensors:
        entity = WasherSensor(_coordinator(), _Entry(), spec)
        assert entity.entity_registry_visible_default is True
        assert entity.entity_registry_enabled_default is spec.enabled_default
        assert entity.suggested_unit_of_measurement is None
        assert entity.native_value is None
        assert isinstance(entity.extra_state_attributes, (dict, type(None)))
        assert not hasattr(entity, "entity_description")


def test_binary_entities_satisfy_ha_description_contract() -> None:
    for spec in profile.DEVICE.binary_sensors:
        entity = WasherBinarySensor(_coordinator(), _Entry(), spec)
        assert entity.entity_registry_visible_default is True
        assert entity.entity_registry_enabled_default is spec.enabled_default
        assert entity.is_on is None
