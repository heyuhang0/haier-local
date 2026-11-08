"""The device profile this integration currently supports.

There is deliberately no plugin framework here: one verified appliance defines
the data files and identity used by the decoder and entities.  Add a second
profile only when its map and entity behavior have been verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class DeviceProfile:
    manufacturer: str
    model: str
    uplus_id: str
    map_typeid: str
    model_file: Path
    digital_model_file: Path


CASARTE_CE_AB13LWTUWCU1 = DeviceProfile(
    manufacturer="Haier / Casarte",
    model="CE AB13LWTUWCU1",
    uplus_id=(
        "201c51890c31c308050100218006664300000000000000000000000000000040"
    ),
    map_typeid=(
        "201c51890c31c30805010021800239584d000000000000000000000000000140"
    ),
    model_file=DATA_DIR / "model_0501.json",
    digital_model_file=DATA_DIR / "digital_model.json",
)
