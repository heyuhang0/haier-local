"""The device profile used by the decoder and entities.

This is the only verified profile.  It owns the identity and the entity/enum
definitions used by the integration; selecting a different profile is deferred
until a second appliance has been verified.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import enum_defs, specs


@dataclass(frozen=True)
class DeviceProfile:
    manufacturer: str
    model: str
    uplus_id: str
    map_typeid: str

    @property
    def sensors(self):
        return specs.ALL_SENSORS

    @property
    def binary_sensors(self):
        return specs.ALL_BINARY

    @property
    def raw_state_fields(self) -> tuple[str, ...]:
        return specs.RAW_STATE_FIELDS

    @property
    def feature_flags(self):
        return specs.FEATURE_FLAGS

    @property
    def raw_only(self):
        return specs.RAW_ONLY

    @property
    def extra_sensor_names(self) -> tuple[tuple[str, str, str], ...]:
        return (
            ("raw_state", "Raw state", "原始状态"),
            ("feature_flags", "Feature flags", "功能开关"),
        )

    def token_for(self, enum: str, raw):
        return enum_defs.token_for(enum, raw)

    def labels_for(self, enum: str, raw, language: str = "en") -> str:
        return enum_defs.labels_for(enum, raw, language)

    def options_for(self, enum: str) -> list[str]:
        return enum_defs.options_for(enum)

    def enum_values(self, enum: str):
        return enum_defs.ENUM_DEFS[enum]


CASARTE_CE_AB13LWTUWCU1 = DeviceProfile(
    manufacturer="Haier / Casarte",
    model="CE AB13LWTUWCU1",
    uplus_id=(
        "201c51890c31c308050100218006664300000000000000000000000000000040"
    ),
    map_typeid=(
        "201c51890c31c30805010021800239584d000000000000000000000000000140"
    ),
)

DEVICE = CASARTE_CE_AB13LWTUWCU1
