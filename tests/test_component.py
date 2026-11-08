"""Static checks for entity specs and translations (no Home Assistant needed)."""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "haier_local"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Load the integration as a package without executing its HA-dependent
# __init__.py. specs.py and enum_defs.py are deliberately HA-free.
_pkg = types.ModuleType("haier_local")
_pkg.__path__ = [str(COMPONENT)]
sys.modules["haier_local"] = _pkg

specs = importlib.import_module("haier_local.specs")
enum_defs = importlib.import_module("haier_local.enum_defs")
decoder = importlib.import_module("haier_local.decoder")
const = importlib.import_module("haier_local.const")
profile = importlib.import_module("haier_local.profile")


def _translations(name: str) -> dict:
    return json.loads((COMPONENT / "translations" / name).read_text())


STRINGS = json.loads((COMPONENT / "strings.json").read_text())
EN = _translations("en.json")
ZH = _translations("zh-Hans.json")


def test_entity_specs_are_unique_and_have_translation_keys() -> None:
    sensor_keys = [spec.key for spec in specs.ALL_SENSORS]
    binary_keys = [spec.key for spec in specs.ALL_BINARY]
    assert len(sensor_keys) == len(set(sensor_keys))
    assert len(binary_keys) == len(set(binary_keys))
    assert set(sensor_keys).isdisjoint(binary_keys)
    assert all(spec.key and spec.name_en and spec.name_zh
               for spec in (*specs.ALL_SENSORS, *specs.ALL_BINARY))


def test_translation_key_coverage() -> None:
    sensor_keys = {spec.key for spec in specs.ALL_SENSORS} | {
        "raw_state",
        "feature_flags",
    }
    binary_keys = {spec.key for spec in specs.ALL_BINARY}
    for document in (STRINGS, EN, ZH):
        assert set(document["entity"]["sensor"]) == sensor_keys
        assert set(document["entity"]["binary_sensor"]) == binary_keys
        assert document["config"]
        assert document["options"]


def test_spec_names_match_translations() -> None:
    for spec in specs.ALL_SENSORS:
        assert STRINGS["entity"]["sensor"][spec.key]["name"] == spec.name_en
        assert ZH["entity"]["sensor"][spec.key]["name"] == spec.name_zh
    for spec in specs.ALL_BINARY:
        assert STRINGS["entity"]["binary_sensor"][spec.key]["name"] == spec.name_en
        assert ZH["entity"]["binary_sensor"][spec.key]["name"] == spec.name_zh


def test_enum_translations_and_tokens() -> None:
    for spec in specs.ALL_SENSORS:
        if not spec.enum:
            continue
        assert spec.enum in enum_defs.ENUM_DEFS
        entries = enum_defs.ENUM_DEFS[spec.enum]
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
    assert enum_defs.token_for("phase", 0) == "standby"
    assert enum_defs.labels_for("phase", 0, "en") == "Standby / not started"
    assert enum_defs.labels_for("phase", 0, "zh-Hans") == "待机/未启动"
    assert enum_defs.token_for("phase", 9999) is None
    assert enum_defs.labels_for("phase", 9999) == "9999"
    assert len(enum_defs.options_for("phase")) == len(enum_defs.ENUM_DEFS["phase"])


def test_spec_sources_exist_in_digital_model() -> None:
    fields = set(decoder.digital_model())
    assert len(fields) == 93
    assert len(specs.RAW_STATE_FIELDS) == 93
    for spec in (*specs.ALL_SENSORS, *specs.ALL_BINARY):
        if spec.source is not None:
            assert spec.source in fields, spec.key
    for field in (*specs.RAW_ONLY, *(row[0] for row in specs.FEATURE_FLAGS)):
        assert field in fields, field


def test_manifest_and_project_metadata() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == "haier_local"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "local_polling"
    assert manifest["version"] == const.VERSION
    device = profile.CASARTE_CE_AB13LWTUWCU1
    assert device.model_file.is_file()
    assert device.digital_model_file.is_file()
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


def _normalise(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value).strip().lower()
    try:
        return f"{float(text):.6f}"
    except ValueError:
        return text


def test_historical_local_values_match_cloud_shadow() -> None:
    """Historical evidence, not a decoder test: both sides are saved outputs."""
    local = json.loads((FIXTURES / "local_status_93.json").read_text())
    cloud = json.loads((FIXTURES / "cloud_values_93.json").read_text())
    assert len(local) == 93
    assert set(local) == set(cloud)
    assert set(local) == set(decoder.digital_model())

    # The cloud shadow had a null value for this one attribute; it is a
    # mapping check, not a value comparison.
    assert cloud["clothesAnionStatus"] is None
    comparable = [name for name in local if cloud[name] is not None]
    assert len(comparable) == 92
    mismatches = [
        (name, local[name], cloud[name])
        for name in comparable
        if _normalise(local[name]) != _normalise(cloud[name])
    ]
    assert not mismatches, mismatches


def test_decoder_value_helpers() -> None:
    assert decoder.remaining_minutes({}) is None
    assert decoder.remaining_minutes({"remainingTimeHH": 1, "remainingTimeMM": 8}) == 68
    assert decoder.remaining_minutes({"remainingTimeHH": 0, "remainingTimeMM": 5}) == 5

    assert decoder.is_running({"cyclePhase": 0}) is False
    assert decoder.is_running({"cyclePhase": 14}) is False
    assert decoder.is_running({"cyclePhase": 18}) is False
    assert decoder.is_running({"cyclePhase": 19}) is False
    assert decoder.is_running({"cyclePhase": 5}) is True
    assert decoder.is_running({}) is None

    assert specs.as_bool(None) is None
    assert specs.as_bool(True) is True
    assert specs.as_bool("false") is False
    assert specs.as_bool("开") is True
