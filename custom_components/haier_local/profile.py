"""The device profile used by the decoder and entities.

This module assembles the one verified device definition.  A second profile
would supply its own entity tuples, field whitelist and enum table; there is no
registry or selection framework until that device exists.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import enum_defs, specs


@dataclass(frozen=True)
class DeviceProfile:
    manufacturer: str
    model: str
    uplus_id: str
    map_typeid: str
    sensors: tuple
    binary_sensors: tuple
    raw_state_fields: tuple[str, ...]
    feature_flags: tuple[tuple[str, str, str], ...]
    raw_only: frozenset[str]
    extra_sensor_names: tuple[tuple[str, str, str], ...]
    enums: Mapping[str, Mapping[int, tuple[str, str, str]]]

    def token_for(self, enum: str, raw):
        entry = self.enums.get(enum, {}).get(raw)
        return entry[0] if entry else None

    def labels_for(self, enum: str, raw, language: str = "en") -> str:
        entry = self.enums.get(enum, {}).get(raw)
        if not entry:
            return str(raw)
        return entry[2] if language.startswith("zh") else entry[1]

    def options_for(self, enum: str) -> list[str]:
        return [entry[0] for entry in self.enums.get(enum, {}).values()]

    def enum_values(self, enum: str):
        return self.enums.get(enum, {})


CASARTE_CE_AB13LWTUWCU1 = DeviceProfile(
    manufacturer="Haier / Casarte",
    model="CE AB13LWTUWCU1",
    uplus_id=(
        "201c51890c31c308050100218006664300000000000000000000000000000040"
    ),
    map_typeid=(
        "201c51890c31c30805010021800239584d000000000000000000000000000140"
    ),
    sensors=specs.ALL_SENSORS,
    binary_sensors=specs.ALL_BINARY,
    raw_state_fields=specs.RAW_STATE_FIELDS,
    feature_flags=specs.FEATURE_FLAGS,
    raw_only=specs.RAW_ONLY,
    extra_sensor_names=(
        ("raw_state", "Raw state", "原始状态"),
        ("feature_flags", "Feature flags", "功能开关"),
    ),
    enums=enum_defs.ENUM_DEFS,
)

DEVICE = CASARTE_CE_AB13LWTUWCU1
