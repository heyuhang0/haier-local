#!/usr/bin/env python3
"""Read the Casarte washer locally over uSS and decode class 0501 fields.

Fully offline once local_key.json exists. Uses the manufacturer's class-0501
byte maps bundled with haismart-local; our exact uPlusId is not in that bundle,
so each class map is tried against the live report and the one that places the
most fields is printed.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
VENDOR = PROJECT / "custom_components/haier_local/vendor"
sys.path.insert(0, str(VENDOR))

from haier_local_hrdp.device_model import ModelField, model_from_record  # noqa: E402
from haier_local_hrdp.uss import read_status  # noqa: E402

MODELS = VENDOR / "haier_local_hrdp/device_models.json.gz"
INTERESTING = (
    "remainingTime", "remaining", "cyclePhase", "cycle", "laundryCycle",
    "currentWashCycle", "washTemp", "spinSpeed", "weight", "loadWeight",
    "door", "remote", "childLock", "onOff", "power", "runningMode",
    "program", "procedure", "water", "electric", "energy", "message",
    "fault", "alarm", "error", "dirty", "detergent", "softener",
)


def load_models() -> list[tuple[str, object]]:
    bundle = json.load(gzip.open(MODELS, "rt", encoding="utf-8"))
    out = []
    for typeid, record in bundle["models"].items():
        if record.get("cls") != "0501":
            continue
        out.append((typeid, model_from_record(typeid, record)))
    return out


def interesting(name: str) -> bool:
    lower = name.lower()
    return any(word.lower() in lower for word in INTERESTING)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host",
                        help="washer LAN address; defaults to HAIER_WASHER_IP")
    parser.add_argument("--key-file", default="local_key.json")
    parser.add_argument("--attributes", help="optional JSON list of declared attribute names")
    parser.add_argument("--status-cmd", default="6D01")
    parser.add_argument("--out", default=str(PROJECT / "washer_status.json"))
    args = parser.parse_args()
    host = args.host or os.environ.get("HAIER_WASHER_IP", "")
    if not host:
        parser.error("--host or HAIER_WASHER_IP is required")

    key_doc = json.loads(Path(args.key_file).read_text())
    device_id = key_doc["device_id"]
    local_key = key_doc["local_key"]
    declared = None
    if args.attributes:
        declared = set(json.loads(Path(args.attributes).read_text()))

    print(f"reading {host} ({device_id}) locally...")
    blobs = read_status(host, device_id, local_key, timeout=4.0)
    print(f"  {len(blobs)} decrypted blob(s): {[len(b) for b in blobs]}")
    if not blobs:
        print("no status blobs")
        return 1

    full = max(blobs, key=len)
    print(f"  decoding {len(full)}-byte blob as {args.status_cmd}")
    best = None
    for typeid, model in load_models():
        decoded = model.decode(
            full, status_cmd=args.status_cmd,
            only=frozenset(declared) if declared else None,
        )
        score = sum(1 for name in decoded if interesting(name))
        if best is None or score > best[0]:
            best = (score, typeid, model, decoded)
        print(f"    {typeid[:24]}… fields={len(model.fields):3d} "
              f"decoded={len(decoded):3d} interesting={score:2d}")

    score, typeid, model, decoded = best
    print(f"\nbest map: {typeid} (score {score})")
    print("interesting values:")
    for name in sorted(decoded):
        if interesting(name):
            print(f"  {name:42} {decoded[name]}")
    Path(args.out).write_text(json.dumps(decoded, indent=2, ensure_ascii=False, default=str))
    print(f"\nfull decoded state written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
