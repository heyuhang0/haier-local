#!/usr/bin/env python3
"""Regenerate the profile's class-0501 map from the vendored catalogue.

Usage:
    python3 -I tools/refresh_model.py
    python3 -I tools/refresh_model.py --check
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMPONENT = PROJECT / "custom_components/haier_local"
BUNDLE = COMPONENT / "vendor/haier_local_hrdp/device_models.json.gz"

_profile_spec = importlib.util.spec_from_file_location(
    "haier_local_profile", COMPONENT / "profile.py"
)
_profile = importlib.util.module_from_spec(_profile_spec)
sys.modules["haier_local_profile"] = _profile
assert _profile_spec.loader is not None
_profile_spec.loader.exec_module(_profile)
DEVICE = _profile.CASARTE_CE_AB13LWTUWCU1


def build() -> dict:
    bundle = json.load(gzip.open(BUNDLE, "rt", encoding="utf-8"))
    record = bundle["models"].get(DEVICE.map_typeid)
    if record is None:
        raise SystemExit(f"map {DEVICE.map_typeid} is not in {BUNDLE}")
    return {
        "typeid": DEVICE.uplus_id,
        "source_typeid": DEVICE.map_typeid,
        "cls": record["cls"],
        "fields": record["fields"],
        "alarms": record.get("alarms", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(DEVICE.model_file))
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if the file is not up to date")
    args = parser.parse_args()

    built = build()
    out = Path(args.out)
    text = json.dumps(built, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = out.read_text() if out.exists() else ""
        if current != text:
            print(f"{out} is out of date", file=sys.stderr)
            return 1
        print(f"{out} is up to date")
        return 0
    out.write_text(text)
    print(f"wrote {out} ({len(built['fields'])} fields, "
          f"{len(built['alarms'])} alarms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
