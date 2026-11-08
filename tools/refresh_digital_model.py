#!/usr/bin/env python3
"""Refresh the 93 cloud descriptions used by the supported profile.

Requires a valid `.haier_token` and `local_key.json` from the one-time setup.
The script keeps only attributes present in the profile's fixed local map.

Usage:
    python3 -I tools/refresh_digital_model.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
COMPONENT = PROJECT / "custom_components/haier_local"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(COMPONENT / "vendor"))

from china_key import get_digital_model  # noqa: E402
from haier_local_hrdp.device_model import model_for  # noqa: E402

_profile_spec = importlib.util.spec_from_file_location(
    "haier_local_profile", COMPONENT / "profile.py"
)
_profile = importlib.util.module_from_spec(_profile_spec)
sys.modules["haier_local_profile"] = _profile
assert _profile_spec.loader is not None
_profile_spec.loader.exec_module(_profile)
DEVICE = _profile.CASARTE_CE_AB13LWTUWCU1


def select_attributes(attributes: list[dict], wanted: set[str]) -> tuple[list[dict], list[str]]:
    selected = [a for a in attributes if a.get("name") in wanted]
    missing = sorted(wanted - {a.get("name") for a in selected})
    return selected, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(DEVICE.digital_model_file))
    args = parser.parse_args()

    token = json.loads((PROJECT / ".haier_token").read_text())
    key = json.loads((PROJECT / "local_key.json").read_text())
    model = model_for(DEVICE.map_typeid)
    if model is None:
        raise SystemExit(f"map {DEVICE.map_typeid} is not in the vendored catalogue")
    # The catalogue contains the class-wide field list; the device's current
    # cloud document is the authoritative list of attributes it declares.
    current = json.loads(DEVICE.digital_model_file.read_text())
    wanted = {a["name"] for a in current if a.get("name")}
    attributes = get_digital_model(
        token["access_token"],
        token["client_id"],
        token.get("app_source", "app"),
        key["device_id"],
    )
    selected, missing = select_attributes(attributes, wanted)
    if missing:
        print(f"cloud model is missing {len(missing)} fields: {missing[:10]}",
              file=sys.stderr)
        return 1

    out = Path(args.out)
    out.write_text(json.dumps(selected, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out} ({len(selected)} attributes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
