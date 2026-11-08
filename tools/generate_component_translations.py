#!/usr/bin/env python3
"""Expand entity and enum translations from specs.py and enum_defs.py.

The static config/options strings stay in the translation JSON files; this
script only replaces the ``entity`` section.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import types
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMPONENT = PROJECT / "custom_components/haier_local"
sys.path.insert(0, str(COMPONENT.parent))

pkg = types.ModuleType("haier_local")
pkg.__path__ = [str(COMPONENT)]
sys.modules["haier_local"] = pkg

specs = importlib.import_module("haier_local.specs")
enum_defs = importlib.import_module("haier_local.enum_defs")

EXTRA_SENSORS = {
    "raw_state": ("Raw state", "原始状态"),
    "feature_flags": ("Feature flags", "功能开关"),
}


def _entity_blocks(language: str) -> dict:
    en = language == "en"
    sensors: dict = {}
    binary: dict = {}
    for spec in specs.ALL_SENSORS:
        block = {"name": spec.name_en if en else spec.name_zh}
        if spec.enum:
            block["state"] = {
                token: (label_en if en else label_zh)
                for token, label_en, label_zh in enum_defs.ENUM_DEFS[spec.enum].values()
            }
        sensors[spec.key] = block
    for key, (name_en, name_zh) in EXTRA_SENSORS.items():
        sensors[key] = {"name": name_en if en else name_zh}
    for spec in specs.ALL_BINARY:
        binary[spec.key] = {"name": spec.name_en if en else spec.name_zh}
    return {"sensor": sensors, "binary_sensor": binary}


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _rendered() -> dict[Path, str]:
    strings = _load(COMPONENT / "strings.json")
    en = _load(COMPONENT / "translations/en.json")
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
