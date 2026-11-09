#!/usr/bin/env python3
"""Fetch Haier's published configFile for one device type id.

The App does not hard-code a model's byte map. It asks this service for the
file selected by the device's 64-hex uPlusId, and reads the ``Property`` and
``Bigdata`` sections from the result. This tool performs the same public,
unauthenticated fetch and verifies the service's published MD5 before writing
the file.

Usage:
    python3 -I tools/fetch_device_config.py --typeid <64-hex-uPlusId>
    python3 -I tools/fetch_device_config.py --typeid <64-hex-uPlusId> \
        --out /tmp/device_config.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_HOST = "https://standardcfm.haigeek.com"
CONFIG_PATH = "/hardwareconfig/config/getDownUrlByFormat"
# The SDK service key is a constant shipped in Haier's own App, not a secret.
SERVICE_KEY = "1234567890abcdefghigklmnopqrstuv"
FORMATS = ("V3", "V2")


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "haier-local/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body)


def _get_bytes(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "haier-local/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_config(typeid: str, *, formatver: str, timeout: float) -> dict | None:
    query = urllib.parse.urlencode({
        "typeid": typeid,
        "formatver": formatver,
        "servicename": "SDK",
        "servicekey": SERVICE_KEY,
    })
    listing = _get_json(f"{CONFIG_HOST}{CONFIG_PATH}?{query}", timeout)
    entries = listing.get("data") or []
    if not entries:
        return None
    entry = entries[0]
    body = _get_bytes(entry["f_url"], timeout)
    expected = entry.get("f_md5")
    actual = hashlib.md5(body, usedforsecurity=False).hexdigest()
    if expected and actual != expected:
        raise RuntimeError(
            f"{formatver} config failed its published MD5: expected {expected}, got {actual}"
        )
    return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--typeid", required=True,
                        help="full 64-hex uPlusId announced by the appliance")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent
                                             / "device_config.json"))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    if len(args.typeid) != 64 or any(c not in "0123456789abcdefABCDEF" for c in args.typeid):
        parser.error("--typeid must be a 64-character hex uPlusId")

    config = None
    for formatver in FORMATS:
        try:
            config = fetch_config(args.typeid, formatver=formatver, timeout=args.timeout)
        except Exception as err:  # noqa: BLE001 - report the service failure and try the next form
            print(f"{formatver}: {err}", file=sys.stderr)
            continue
        if config is not None:
            print(f"{formatver}: found config")
            break
    if config is None:
        raise SystemExit(f"no configFile for {args.typeid}")

    out = Path(args.out)
    out.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    basic = config.get("BasicInfo") or {}
    print(f"name={basic.get('name')!r} deviceType={basic.get('deviceType')!r}")
    print(f"Version={config.get('Version')!r} "
          f"Property={len(config.get('Property') or [])} "
          f"Bigdata={len(config.get('Bigdata') or [])} "
          f"Operation={len(config.get('Operation') or [])}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
