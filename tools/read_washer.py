#!/usr/bin/env python3
"""Read the supported washer locally and decode it with the integration's map.

It loads the same fixed class-0501 profile and calls the same decode function as
the Home Assistant integration. It is read-only and fully offline once
``local_key.json`` exists.

Usage:
    python3 -I tools/read_washer.py --host <washer-ip>
    python3 -I tools/read_washer.py --host <washer-ip> --out /tmp/state.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import types
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMPONENT = PROJECT / "custom_components/haier_local"
VENDOR = COMPONENT / "vendor"
sys.path.insert(0, str(VENDOR))

from haier_local_hrdp.uss import read_status  # noqa: E402

# Load decoder.py without executing the HA-dependent package __init__.
_pkg = types.ModuleType("haier_local")
_pkg.__path__ = [str(COMPONENT)]
sys.modules["haier_local"] = _pkg
from haier_local.decoder import decode_reports  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host",
                        help="washer LAN address; defaults to HAIER_WASHER_IP")
    parser.add_argument("--key-file", default="local_key.json")
    parser.add_argument("--attributes", help="optional JSON list of declared attribute names")
    parser.add_argument("--status-cmd", default="6D01")
    parser.add_argument("--out", default=str(PROJECT / "washer_status.json"))
    parser.add_argument("--raw-out", help="also save the decrypted report bytes")
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
    if args.raw_out:
        Path(args.raw_out).write_bytes(full)
        print(f"  raw report written to {args.raw_out}")
    decoded = decode_reports(
        blobs, status_cmd=args.status_cmd,
        only=frozenset(declared) if declared else None,
    )
    print(f"  decoded {len(decoded)} attributes")
    for name in sorted(decoded):
        print(f"  {name:42} {decoded[name]}")
    Path(args.out).write_text(json.dumps(decoded, indent=2, ensure_ascii=False, default=str))
    print(f"\nfull decoded state written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
