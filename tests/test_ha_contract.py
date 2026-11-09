"""Entity construction/property contract against a real Home Assistant.

The `ha-contract` CI job installs Home Assistant 2026.11.0 and runs this file.
Locally it is skipped when Home Assistant is not installed:

    pytest tests/test_ha_contract.py

This checks construction and entity-description/property access, not full
EntityPlatform registration.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "haier_local"
sys.path.insert(0, str(ROOT / "custom_components"))

from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.entity_platform import PlatformData  # noqa: E402
from homeassistant.loader import async_setup as loader_setup  # noqa: E402
from haier_local import profile  # noqa: E402
from haier_local.binary_sensor import WasherBinarySensor  # noqa: E402
from haier_local.const import CONF_DEVICE_ID  # noqa: E402
from haier_local.sensor import (  # noqa: E402
    FeatureFlagsSensor,
    RawStateSensor,
    WasherSensor,
)


class _Entry:
    title = "Washer"
    data = {CONF_DEVICE_ID: "AABBCCDDEEFF"}


def _coordinator(data: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(data=data or {}, hass=None)


async def _check_translated_names(tmp_path: Path) -> None:
    # Load the integration through HA's real loader rather than rebuilding its
    # translation key format by hand.
    custom_components = tmp_path / "custom_components"
    custom_components.mkdir()
    os.symlink(COMPONENT, custom_components / "haier_local")
    hass = HomeAssistant(str(tmp_path))
    loader_setup(hass)

    expected = {
        "en": ("Remaining time", "Problem", "Raw state", "Feature flags"),
        "zh-Hans": ("剩余时间", "故障", "原始状态", "功能开关"),
    }
    remaining_time = next(
        spec for spec in profile.DEVICE.sensors if spec.key == "remaining_time"
    )
    problem = next(
        spec for spec in profile.DEVICE.binary_sensors if spec.key == "problem"
    )
    for language, names in expected.items():
        hass.config.language = language
        sensor_data = PlatformData(hass, domain="sensor", platform_name="haier_local")
        binary_data = PlatformData(
            hass, domain="binary_sensor", platform_name="haier_local"
        )
        await sensor_data.async_load_translations()
        await binary_data.async_load_translations()

        sensor = WasherSensor(_coordinator(), _Entry(), remaining_time)
        binary = WasherBinarySensor(_coordinator(), _Entry(), problem)
        raw = RawStateSensor(_coordinator(), _Entry())
        flags = FeatureFlagsSensor(_coordinator(), _Entry())
        sensor.platform_data = sensor_data
        binary.platform_data = binary_data
        raw.platform_data = sensor_data
        flags.platform_data = sensor_data
        assert (sensor.name, binary.name, raw.name, flags.name) == names


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


def test_translated_names_for_all_entity_classes(tmp_path: Path) -> None:
    asyncio.run(_check_translated_names(tmp_path))


def test_problem_binary_semantics() -> None:
    spec = next(spec for spec in profile.DEVICE.binary_sensors if spec.key == "problem")
    coordinator = _coordinator({"_alarm_count": 0})
    entity = WasherBinarySensor(coordinator, _Entry(), spec)
    assert entity.is_on is False
    coordinator.data = {"_alarm_count": 1}
    assert entity.is_on is True
