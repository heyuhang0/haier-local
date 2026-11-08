"""Metadata for the device profile used by the decoder and entities."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceProfile:
    manufacturer: str
    model: str
    uplus_id: str
    map_typeid: str


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
