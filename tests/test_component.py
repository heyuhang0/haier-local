"""Static checks for entity specs and translations (no Home Assistant needed)."""
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "haier_local"

sys.path.insert(0, str(COMPONENT.parent))

from haier_local import const, decoder, profile, specs  # noqa: E402
from haier_local.profile import DeviceProfile  # noqa: E402

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
        assert entries, spec.enum
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
    assert DEVICE.map_typeid == DEVICE.uplus_id
    assert len(fields) == 132
    assert len(decoder._MODEL.fields_for("6D01")) == 132
    assert fields <= catalogue
    for spec in (*DEVICE.sensors, *DEVICE.binary_sensors):
        if spec.source is not None:
            assert spec.source in fields, spec.key
    for field in DEVICE.raw_only:
        assert field in fields, field


def test_exact_map_places_the_previously_wrong_fields() -> None:
    detergent = decoder._MODEL.field("detergentType")
    softener = decoder._MODEL.field("softenerConcentrationType")
    plasma = decoder._MODEL.field("photoPlasmaStatus")
    assert (detergent.word, detergent.bit, detergent.length) == (15, 0, 4)
    assert (softener.word, softener.bit, softener.length) == (15, 4, 4)
    assert (plasma.word, plasma.bit, plasma.length) == (14, 9, 1)
    assert decoder._MODEL.field("clothesAnionStatus") is None


def test_exact_map_decodes_split_nibbles_and_photo_plasma() -> None:
    # 6D01's attribute block starts at byte 92. Word 15 carries detergent
    # type in bits 0-3 and softener concentration in bits 4-7; an 8-bit read
    # of detergentType would fold them into 0x11. Word 14 bit 9 is the
    # photo-plasma flag, not the old map's clothesAnionStatus.
    blob = bytearray(92 + 2 * 66)
    word15 = 92 + 2 * (15 - 1)
    blob[word15:word15 + 2] = (0x11).to_bytes(2, "big")
    word14 = 92 + 2 * (14 - 1)
    word14_value = int.from_bytes(blob[word14:word14 + 2], "big") | (1 << 9)
    blob[word14:word14 + 2] = word14_value.to_bytes(2, "big")
    state = decoder._MODEL.decode(bytes(blob), status_cmd="6D01")
    assert state["detergentType"] == 2
    assert state["softenerConcentrationType"] == 2
    assert state["photoPlasmaStatus"] is True
    assert "clothesAnionStatus" not in state


def test_profile_data_is_owned_by_the_instance() -> None:
    other = DeviceProfile(
        manufacturer="Other",
        model="Other",
        uplus_id="0" * 64,
        map_typeid="0" * 64,
        sensors=(),
        binary_sensors=(),
        raw_state_fields=(),
        raw_only=frozenset(),
        extra_sensor_names=(),
        enums={},
    )
    assert other.sensors == ()
    assert other.raw_state_fields == ()
    assert other.enums == {}
    try:
        other.token_for("phase", 0)
    except KeyError:
        pass
    else:
        raise AssertionError("an empty profile must not resolve enum values")
    assert DEVICE.sensors


def test_manifest_and_project_metadata() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == manifest["version"]
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


def test_cycle_totals_and_texture_coverage() -> None:
    by_key = {spec.key: spec for spec in DEVICE.sensors}
    assert by_key["current_water"].state_class is None
    assert by_key["current_energy"].state_class is None
    assert by_key["total_water"].state_class == "total_increasing"
    assert by_key["total_energy"].state_class == "total_increasing"
    assert len(DEVICE.enum_values("fabric")) == 106
    assert DEVICE.enum_values("diag_result")[False][0] == "not_passed"
    assert DEVICE.enum_values("diag_result")[True][0] == "passed"


def test_new_fields_follow_the_existing_category_rules() -> None:
    sensors = {spec.key: spec for spec in DEVICE.sensors}
    binary = {spec.key: spec for spec in DEVICE.binary_sensors}

    assert not sensors["softener_concentration"].diagnostic
    assert sensors["softener_concentration"].enabled_default
    assert not sensors["softener_ratio"].diagnostic
    assert sensors["softener_ratio"].enabled_default
    assert not sensors["water_hardness"].diagnostic
    assert not sensors["water_hardness"].enabled_default
    for key in ("box1_remaining", "box2_remaining", "box3_remaining", "box4_remaining"):
        assert not sensors[key].diagnostic
        assert not sensors[key].enabled_default

    for key in ("air_wash_level", "air_wash_time", "care", "wet_cleaning"):
        spec = sensors.get(key) or binary[key]
        assert not spec.diagnostic
        assert spec.enabled_default
    for key in ("anti_crease", "fresh_air", "photo_plasma", "spa_rinse_heat"):
        assert not binary[key].diagnostic
        assert not binary[key].enabled_default
    assert "clothesAnionStatus" not in DEVICE.raw_state_fields


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
