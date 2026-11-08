#!/usr/bin/env python3
"""Expand entity and enum translations from specs.py and enum_defs.py.

The static config/options strings stay in the translation JSON files; this
script only replaces the ``entity`` section.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMPONENT = PROJECT / "custom_components/haier_local"
sys.path.insert(0, str(COMPONENT.parent))

from haier_local.profile import DEVICE  # noqa: E402


def _entity_blocks(language: str) -> dict:
    en = language == "en"
    sensors: dict = {}
    binary: dict = {}
    for spec in DEVICE.sensors:
        block = {"name": spec.name_en if en else spec.name_zh}
        if spec.enum:
            block["state"] = {
                token: (label_en if en else label_zh)
                for token, label_en, label_zh in DEVICE.enum_values(spec.enum).values()
            }
        sensors[spec.key] = block
    for key, name_en, name_zh in DEVICE.extra_sensor_names:
        sensors[key] = {"name": name_en if en else name_zh}
    for spec in DEVICE.binary_sensors:
        binary[spec.key] = {"name": spec.name_en if en else spec.name_zh}
    return {"sensor": sensors, "binary_sensor": binary}


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _rendered() -> dict[Path, str]:
    strings = _load(COMPONENT / "strings.json")
    en = copy.deepcopy(strings)
    zh = _load(COMPONENT / "translations/zh-Hans.json")
    strings["entity"] = _entity_blocks("en")
    en["entity"] = _entity_blocks("en")
    zh["entity"] = _entity_blocks("zh")
    return {
        COMPONENT / "strings.json": json.dumps(strings, indent=2, ensure_ascii=False) + "\n",
        COMPONENT / "translations/en.json": json.dumps(en, indent=2, ensure_ascii=False) + "\n",
        COMPONENT / "translations/zh-Hans.json": json.dumps(zh, indent=2, ensure_ascii=False) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if the files are not up to date")
    args = parser.parse_args()

    rendered = _rendered()
    if args.check:
        stale = [str(path) for path, text in rendered.items()
                 if path.read_text() != text]
        if stale:
            print("out of date: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("translation files are up to date")
        return 0

    for path, text in rendered.items():
        path.write_text(text)
    blocks = _entity_blocks("en")
    print(f"sensors={len(blocks['sensor'])}, binary={len(blocks['binary_sensor'])}")
    print("wrote " + ", ".join(str(path.relative_to(PROJECT)) for path in rendered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
