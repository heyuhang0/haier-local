"""The verified device profile: identity plus entity, field and enum data."""
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
    raw_only: frozenset[str]
    extra_sensor_names: tuple[tuple[str, str, str], ...]
    enums: Mapping[str, Mapping[int, tuple[str, str, str]]]

    def enum_values(self, enum: str):
        try:
            values = self.enums[enum]
        except KeyError:
            raise KeyError(f"profile has no enum definition for {enum!r}") from None
        if not values:
            raise ValueError(f"profile enum {enum!r} is empty")
        return values

    def token_for(self, enum: str, raw):
        entry = self.enum_values(enum).get(raw)
        return entry[0] if entry else None

    def labels_for(self, enum: str, raw, language: str = "en") -> str:
        entry = self.enum_values(enum).get(raw)
        if not entry:
            return str(raw)
        return entry[2] if language.startswith("zh") else entry[1]

    def options_for(self, enum: str) -> list[str]:
        return [entry[0] for entry in self.enum_values(enum).values()]


UPLUS_ID = "201c51890c31c308050100218006664300000000000000000000000000000040"

CASARTE_CE_AB13LWTUWCU1 = DeviceProfile(
    manufacturer="Haier / Casarte",
    model="CE AB13LWTUWCU1",
    uplus_id=UPLUS_ID,
    map_typeid=UPLUS_ID,
    sensors=specs.ALL_SENSORS,
    binary_sensors=specs.ALL_BINARY,
    raw_state_fields=specs.RAW_STATE_FIELDS,
    raw_only=specs.RAW_ONLY,
    extra_sensor_names=(
        ("raw_state", "Raw state", "原始状态"),
    ),
    enums=enum_defs.ENUM_DEFS,
)

DEVICE = CASARTE_CE_AB13LWTUWCU1
