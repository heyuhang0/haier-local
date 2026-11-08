"""Local uSS reader + class-0501 decoder for this washer.

No cloud, no Home Assistant types: the coordinator runs this in an executor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .const import MODEL_FILE, DIGITAL_MODEL_FILE

_VENDOR = Path(__file__).resolve().parent / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from haier_local_hrdp.device_model import model_from_record  # noqa: E402
from haier_local_hrdp.udiscovery import query as _udiscovery_query  # noqa: E402
from haier_local_hrdp.uss import parse_alarm_frame, read_status  # noqa: E402

_record = json.loads(MODEL_FILE.read_text())
_MODEL = model_from_record(
    _record["typeid"],
    {"cls": _record["cls"], "fields": _record["fields"], "alarms": _record.get("alarms", [])},
)
_DIGITAL = {
    a["name"]: a
    for a in json.loads(DIGITAL_MODEL_FILE.read_text())
    if a.get("name")
}


def digital_model() -> dict[str, dict]:
    return _DIGITAL


def friendly_name(attribute: str) -> str:
    return str(_DIGITAL.get(attribute, {}).get("desc") or attribute)


def enum_label(attribute: str, value):
    """Map a raw enum value using the cloud digital model's dataList, if it has one."""
    entry = _DIGITAL.get(attribute) or {}
    value_range = entry.get("valueRange") or {}
    for item in value_range.get("dataList") or []:
        if str(item.get("data")) == str(value):
            return item.get("desc") or str(value)
    return str(value)


def enum_options(attribute: str) -> dict[str, str]:
    entry = _DIGITAL.get(attribute) or {}
    return {
        str(item.get("data")): str(item.get("desc"))
        for item in (entry.get("valueRange") or {}).get("dataList") or []
    }


def discover_device(host: str):
    """Key-free UDISCOVERY: returns DeviceInfo or None."""
    return _udiscovery_query(host, timeout=2.0)


def read_state(host: str, device_id: str, local_key: str) -> dict:
    """One read-only uSS session, decoded with the class 0501 map."""
    blobs = read_status(host, device_id, local_key, timeout=4.0)
    if not blobs:
        raise RuntimeError("no decrypted status report (wrong key or device unreachable)")
    decoded = [_MODEL.decode(blob, status_cmd="6D01") for blob in blobs if len(blob) > 20]
    state = max(decoded, key=len) if decoded else {}
    if not state:
        raise RuntimeError("decrypted report but no class-0501 fields placed")
    state["_blob_lengths"] = [len(blob) for blob in blobs]

    alarm_count = 0
    alarm_codes: list = []
    alarm_labels: list = []
    for blob in blobs:
        try:
            alarm = parse_alarm_frame(blob)
        except Exception:  # noqa: BLE001 - a non-alarm frame is normal
            continue
        if not alarm:
            continue
        alarm_count += int(alarm.get("alarm_count") or 0)
        alarm_codes.extend(alarm.get("alarm_codes") or [])
        alarm_labels.extend(alarm.get("alarm_labels") or [])
    state["_alarm_count"] = alarm_count
    state["_alarm_codes"] = alarm_codes
    state["_alarm_labels"] = alarm_labels
    return state


def remaining_minutes(state: dict) -> int | None:
    hours = state.get("remainingTimeHH")
    minutes = state.get("remainingTimeMM")
    if hours is None and minutes is None:
        return None
    return int(hours or 0) * 60 + int(minutes or 0)


def is_running(state: dict) -> bool | None:
    phase = state.get("cyclePhase")
    if phase is None:
        return None
    try:
        return int(phase) not in {0, 14, 18, 19}
    except (TypeError, ValueError):
        return None
