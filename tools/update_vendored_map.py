#!/usr/bin/env python3
"""Project a fetched configFile into the vendored device map.

The vendored bundle stores only the positions and enum tables the decoder
needs, not the full vendor file. This tool applies the same projection used by
the runtime and adds/replaces one model in
``custom_components/haier_local/vendor/haier_local_hrdp/device_models.json.gz``.

Usage:
    python3 -I tools/fetch_device_config.py --typeid <64-hex-uPlusId>
    python3 -I tools/update_vendored_map.py \
        --typeid <64-hex-uPlusId> --config device_config.json
    python3 -I tools/update_vendored_map.py \
        --typeid <64-hex-uPlusId> --config device_config.json --check
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
BUNDLE = (PROJECT / "custom_components/haier_local/vendor/"
          "haier_local_hrdp/device_models.json.gz")
sys.path.insert(0, str(PROJECT / "custom_components/haier_local/vendor"))

from haier_local_hrdp.device_model import project_config  # noqa: E402


def _load_bundle() -> dict:
    with gzip.open(BUNDLE, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _write_bundle(bundle: dict) -> None:
    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode()
    tmp = BUNDLE.with_suffix(BUNDLE.suffix + ".tmp")
    with tmp.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as handle:
            handle.write(payload)
    os.replace(tmp, BUNDLE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--typeid", required=True,
                        help="full 64-hex uPlusId used as the bundle key")
    parser.add_argument("--config", required=True,
                        help="configFile JSON written by fetch_device_config.py")
    parser.add_argument("--check", action="store_true",
                        help="compare the projected record with the bundle; do not write")
    args = parser.parse_args()

    if len(args.typeid) != 64 or any(c not in "0123456789abcdefABCDEF" for c in args.typeid):
        parser.error("--typeid must be a 64-character hex uPlusId")

    config = json.loads(Path(args.config).read_text())
    record = project_config(config, args.typeid)
    if record is None:
        raise SystemExit("the config has no positioned fields")

    bundle = _load_bundle()
    key = args.typeid.lower()
    old = bundle["models"].get(key)
    changed = old != record
    if args.check:
        if changed:
            print(f"{key}: bundle record is out of date", file=sys.stderr)
            return 1
        print(f"{key}: bundle record is up to date")
        return 0

    bundle["models"][key] = record
    _write_bundle(bundle)
    fields = record["fields"]
    by_cmd: dict[str, int] = {}
    for row in fields:
        by_cmd[row[5]] = by_cmd.get(row[5], 0) + 1
    print(f"{'updated' if changed else 'unchanged'} {key}")
    print(f"name={record.get('name')!r} version={record.get('ver')!r} "
          f"fields={len(fields)} alarms={len(record['alarms'])} ops={len(record['ops'])}")
    print("fields by report: " + ", ".join(
        f"{cmd}={count}" for cmd, count in sorted(by_cmd.items(), key=lambda item: str(item[0]))
    ))
    print(f"wrote {BUNDLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
