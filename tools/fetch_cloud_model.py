#!/usr/bin/env python3
"""Fetch the cloud digital model for the saved device.

This is the maintenance path that produced the historical cloud model used to
curate enum labels. It contacts Haier's mainland cloud and requires the access
token and device id already produced by ``china_key.py``.

Usage:
    python3 -I tools/fetch_cloud_model.py
    python3 -I tools/fetch_cloud_model.py --out /tmp/cloud_model.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from china_key import (  # noqa: E402
    APP_SOURCES,
    _assert_ok,
    _headers,
    _http_json,
    _load_token,
)

DIGITAL_URL = "https://uws.haier.net/shadow/v1/devdigitalmodels"
TOKEN_FILE = PROJECT / ".haier_token"
KEY_FILE = PROJECT / "local_key.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--device-id", help="defaults to local_key.json")
    parser.add_argument("--out", default=str(PROJECT / "cloud_model.json"))
    args = parser.parse_args()

    if not TOKEN_FILE.exists():
        raise SystemExit(f"missing {TOKEN_FILE}; run tools/china_key.py first")
    access_token, client_id, app_source = _load_token(TOKEN_FILE)
    if not access_token:
        raise SystemExit(f"no access token in {TOKEN_FILE}")
    app_source = app_source or "app"
    if app_source not in APP_SOURCES:
        raise SystemExit(f"unsupported app source {app_source!r}")

    device_id = args.device_id
    if not device_id:
        if not KEY_FILE.exists():
            raise SystemExit("pass --device-id or create local_key.json")
        device_id = str(json.loads(KEY_FILE.read_text())["device_id"])

    app_id, app_key = APP_SOURCES[app_source]
    payload = {"deviceInfoList": [{"deviceId": device_id}]}
    body = json.dumps(payload)
    headers = _headers(app_id, app_key, client_id, access_token, body, DIGITAL_URL)
    content = _assert_ok(
        _http_json(DIGITAL_URL, method="POST", payload=payload, headers=headers),
        "digital model",
    )
    detail = (content.get("detailInfo") or {}).get(device_id)
    if not detail:
        raise SystemExit(f"no digital model for {device_id}")
    attributes = json.loads(detail).get("attributes") or []
    Path(args.out).write_text(json.dumps(attributes, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(attributes)} attributes to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
