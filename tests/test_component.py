"""Static checks for entity specs and translations (no Home Assistant needed)."""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "haier_local"

# Load the integration as a package without executing its HA-dependent
# __init__.py. specs.py and enum_defs.py are deliberately HA-free.
_pkg = types.ModuleType("haier_local")
_pkg.__path__ = [str(COMPONENT)]
sys.modules["haier_local"] = _pkg

specs = importlib.import_module("haier_local.specs")
enum_defs = importlib.import_module("haier_local.enum_defs")
decoder = importlib.import_module("haier_local.decoder")
const = importlib.import_module("haier_local.const")


def _translations(name: str) -> dict:
    return json.loads((COMPONENT / "translations" / name).read_text())


STRINGS = json.loads((COMPONENT / "strings.json").read_text())
EN = _translations("en.json")
ZH = _translations("zh-Hans.json")


def test_entity_tiers() -> None:
    assert len(specs.PRIMARY_SENSORS) == 13
    assert len(specs.PRIMARY_BINARY) == 7
    assert len(specs.DIAGNOSTIC_SENSORS) == 14
    assert len(specs.DIAGNOSTIC_BINARY) == 7
    assert len(specs.DISABLED_SENSORS) == 11
    assert len(specs.DISABLED_BINARY) == 5
    assert len(specs.ALL_SENSORS) + 2 == 40
    assert len(specs.ALL_BINARY) == 19


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
    assert manifest["codeowners"] == ["@hyh0"]
    assert const.MODEL_FILE.is_file()
    assert const.DIGITAL_MODEL_FILE.is_file()
    assert len(const.MODEL_UPIUS_ID) > 32
    assert not const.MODEL_UPIUS_ID.startswith("0x")

    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs["name"] == "Haier Local"
    assert hacs["render_readme"] is True


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
