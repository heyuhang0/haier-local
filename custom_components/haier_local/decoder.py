"""Local uSS reader + class-0501 decoder for this washer.

No cloud, no Home Assistant types: the coordinator runs this in an executor.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .profile import DEVICE

_VENDOR = Path(__file__).resolve().parent / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from haier_local_hrdp.device_model import model_for  # noqa: E402
from haier_local_hrdp.udiscovery import query as _udiscovery_query  # noqa: E402
from haier_local_hrdp.uss import parse_alarm_frame, read_status  # noqa: E402

_MODEL = model_for(DEVICE.map_typeid)
if _MODEL is None:
    raise RuntimeError(
        f"device map {DEVICE.map_typeid} is not in the vendored catalogue"
    )


def map_field_names() -> frozenset[str]:
    """Field names present in the selected catalogue map."""
    return frozenset(field.name for field in _MODEL.fields)


def discover_device(host: str):
    """Key-free UDISCOVERY: returns DeviceInfo or None."""
    return _udiscovery_query(host, timeout=2.0)


def decode_reports(
    blobs: list[bytes],
    *,
    status_cmd: str = "6D01",
    only: frozenset[str] | None = None,
) -> dict:
    """Decode a uSS status burst with the profile's fixed map.

    The integration and the standalone reader both call this function, so a
    successful reader run exercises the same decode path as setup.
    """
    decoded = [
        _MODEL.decode(blob, status_cmd=status_cmd, only=only)
        for blob in blobs
        if len(blob) > 20
    ]
    state = max(decoded, key=len) if decoded else {}
    if not state:
        raise RuntimeError("decrypted report but no class-0501 fields placed")
    state["_blob_lengths"] = [len(blob) for blob in blobs]
    state.update(parse_alarms(blobs))
    return state


def read_state(host: str, device_id: str, local_key: str) -> dict:
    """One read-only uSS session, decoded with the class 0501 map."""
    blobs = read_status(host, device_id, local_key, timeout=4.0)
    if not blobs:
        raise RuntimeError("no decrypted status report (wrong key or device unreachable)")
    return decode_reports(blobs)


def parse_alarms(blobs: list[bytes]) -> dict:
    """Collect fault positions using this washer's own alarm names.

    ``parse_alarm_frame`` defaults to an air-conditioner label table; using it
    for a washer would confidently name the wrong fault.
    """
    names = _MODEL.alarm_names()
    alarm_count = 0
    alarm_codes: list = []
    alarm_labels: list = []
    for blob in blobs:
        try:
            alarm = parse_alarm_frame(blob, names, shared_table=False)
        except Exception:  # noqa: BLE001 - a non-alarm frame is normal
            continue
        if not alarm:
            continue
        alarm_count += int(alarm.get("alarm_count") or 0)
        alarm_codes.extend(alarm.get("alarm_codes") or [])
        alarm_labels.extend(alarm.get("alarm_labels") or [])
    return {
        "_alarm_count": alarm_count,
        "_alarm_codes": alarm_codes,
        "_alarm_labels": alarm_labels,
    }
