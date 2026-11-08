"""Static checks for entity specs and translations (no Home Assistant needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "haier_local"

sys.path.insert(0, str(COMPONENT.parent))

from haier_local import const, decoder, profile, specs  # noqa: E402

DEVICE = profile.DEVICE


def _translations(name: str) -> dict:
    return json.loads((COMPONENT / "translations" / name).read_text())


STRINGS = json.loads((COMPONENT / "strings.json").read_text())
EN = _translations("en.json")
ZH = _translations("zh-Hans.json")


def test_entity_specs_are_unique_and_have_translation_keys() -> None:
    sensor_keys = [spec.key for spec in DEVICE.sensors]
    binary_keys = [spec.key for spec in DEVICE.binary_sensors]
    assert len(sensor_keys) == len(set(sensor_keys))
    assert len(binary_keys) == len(set(binary_keys))
    assert set(sensor_keys).isdisjoint(binary_keys)
    assert all(spec.key and spec.name_en and spec.name_zh
               for spec in (*DEVICE.sensors, *DEVICE.binary_sensors))


def test_translation_key_coverage() -> None:
    sensor_keys = {spec.key for spec in DEVICE.sensors} | {
        key for key, _en, _zh in DEVICE.extra_sensor_names
    }
    binary_keys = {spec.key for spec in DEVICE.binary_sensors}
    for document in (STRINGS, EN, ZH):
        assert set(document["entity"]["sensor"]) == sensor_keys
        assert set(document["entity"]["binary_sensor"]) == binary_keys
        assert document["config"]
        assert document["options"]


def test_spec_names_match_translations() -> None:
    for spec in DEVICE.sensors:
        assert STRINGS["entity"]["sensor"][spec.key]["name"] == spec.name_en
        assert ZH["entity"]["sensor"][spec.key]["name"] == spec.name_zh
    for spec in DEVICE.binary_sensors:
        assert STRINGS["entity"]["binary_sensor"][spec.key]["name"] == spec.name_en
        assert ZH["entity"]["binary_sensor"][spec.key]["name"] == spec.name_zh


def test_enum_translations_and_tokens() -> None:
    for spec in DEVICE.sensors:
        if not spec.enum:
            continue
        entries = DEVICE.enum_values(spec.enum)
        tokens = [entry[0] for entry in entries.values()]
        assert len(tokens) == len(set(tokens)), spec.enum

        for document, language in ((STRINGS, "en"), (EN, "en"), (ZH, "zh")):
            state = document["entity"]["sensor"][spec.key].get("state")
            assert state is not None, f"{spec.key} has no state translations"
            assert set(state) == set(tokens), spec.key
            for raw, entry in entries.items():
                token, _english, _chinese = entry
                assert state[token] == entry[1 if language == "en" else 2]


def test_enum_helpers() -> None:
    assert DEVICE.token_for("phase", 0) == "standby"
    assert DEVICE.labels_for("phase", 0, "en") == "Standby / not started"
    assert DEVICE.labels_for("phase", 0, "zh-Hans") == "待机/未启动"
    assert DEVICE.token_for("phase", 9999) is None
    assert DEVICE.labels_for("phase", 9999) == "9999"
    assert len(DEVICE.options_for("phase")) == len(DEVICE.enum_values("phase"))


def test_spec_sources_exist_in_raw_state_fields_and_catalogue() -> None:
    fields = set(DEVICE.raw_state_fields)
    catalogue = decoder.map_field_names()
    assert len(fields) == 93
    assert fields <= catalogue
    for spec in (*DEVICE.sensors, *DEVICE.binary_sensors):
        if spec.source is not None:
            assert spec.source in fields, spec.key
    for field in (*DEVICE.raw_only, *(row[0] for row in DEVICE.feature_flags)):
        assert field in fields, field


def test_manifest_and_project_metadata() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == "haier_local"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_polling"
    assert manifest["version"] == const.VERSION
    device = profile.DEVICE
    assert len(device.uplus_id) > 32
    assert not device.uplus_id.startswith("0x")

    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["name"] == "Haier Local"
    assert hacs["render_readme"] is True


def test_washer_alarm_labels_are_not_air_conditioner_labels() -> None:
    # Fault position 22. The shared AC table calls this an indoor PM2.5 sensor
    # failure; the washer model calls it doorLockFail.
    frame = (
        b"\xff\xff" + bytes([13]) + b"\x00" * 7
        + b"\x0f\x5a" + b"\x40\x00\x00"
    )
    alarms = decoder.parse_alarms([frame])
    assert alarms["_alarm_count"] == 1
    assert alarms["_alarm_codes"] == [22]
    assert alarms["_alarm_labels"] == ["doorLockFail"]


def test_decoder_value_helpers() -> None:
    assert specs.remaining_minutes({}) is None
    assert specs.remaining_minutes({"remainingTimeHH": 1, "remainingTimeMM": 8}) == 68
    assert specs.remaining_minutes({"remainingTimeHH": 0, "remainingTimeMM": 5}) == 5

    assert specs.is_running({"cyclePhase": 0}) is False
    assert specs.is_running({"cyclePhase": 14}) is False
    assert specs.is_running({"cyclePhase": 18}) is False
    assert specs.is_running({"cyclePhase": 19}) is False
    assert specs.is_running({"cyclePhase": 5}) is True
    assert specs.is_running({}) is None

    assert specs.as_bool(None) is None
    assert specs.as_bool(True) is True
    assert specs.as_bool("false") is False
    assert specs.as_bool("开") is True
