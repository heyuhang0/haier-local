#!/usr/bin/env python3
"""Generate strings.json, translations/en.json and translations/zh-Hans.json
from the entity specs and enum_defs (English is the source language)."""
from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
COMPONENT = PROJECT / "custom_components/haier_local"
sys.path.insert(0, str(COMPONENT.parent))

pkg = types.ModuleType("haier_local")
pkg.__path__ = [str(COMPONENT)]
sys.modules["haier_local"] = pkg

specs = importlib.import_module("haier_local.specs")
enum_defs = importlib.import_module("haier_local.enum_defs")

CONFIG_EN = {
    "config": {
        "step": {
            "user": {
                "title": "Haier Local",
                "description": "Connect to the washer over its local uSS protocol on TCP 56800. localKey accepts the 32-hex key or a pasted local_key.json.",
                "data": {
                    "host": "LAN address",
                    "local_key": "localKey (32 hex or local_key.json)",
                    "device_id": "Device ID (optional)",
                    "name": "Name",
                    "scan_interval": "Poll interval (seconds)",
                },
            },
        },
        "error": {
            "cannot_connect": "Could not decrypt a status report. Check the address and localKey.",
            "invalid_key": "localKey must be 32 hexadecimal characters (or a local_key.json document).",
            "device_id_required": "UDISCOVERY did not report a device ID. Enter the Wi-Fi module's MAC address.",
            "name_required": "Enter a name for the device.",
            "unsupported_class": "This appliance is not a class-0501 washer. This integration only supports class 0501.",
            "unsupported_model": "This appliance is not a supported device profile.",
        },
        "abort": {"already_configured": "This washer is already configured."},
    },
    "options": {
        "step": {
            "init": {
                "title": "Haier Local options",
                "description": "Update the address, localKey or poll interval.",
                "data": {
                    "host": "LAN address",
                    "local_key": "localKey (32 hex or local_key.json)",
                    "scan_interval": "Poll interval (seconds)",
                },
            }
        },
        "error": {
            "cannot_connect": "Could not decrypt a status report with these settings.",
            "invalid_key": "localKey must be 32 hexadecimal characters (or a local_key.json document).",
        },
    },
}

CONFIG_ZH = {
    "config": {
        "step": {
            "user": {
                "title": "海尔本地设备",
                "description": "通过本地 uSS 协议（TCP 56800）连接洗衣机。localKey 可以填 32 位十六进制，或直接粘贴 local_key.json。",
                "data": {
                    "host": "局域网地址",
                    "local_key": "localKey（32 位十六进制或 local_key.json）",
                    "device_id": "设备 ID（可选）",
                    "name": "名称",
                    "scan_interval": "轮询间隔（秒）",
                },
            },
        },
        "error": {
            "cannot_connect": "无法解密状态报文，请检查地址和 localKey。",
            "invalid_key": "localKey 必须是 32 位十六进制（或 local_key.json 文档）。",
            "device_id_required": "UDISCOVERY 没有返回设备 ID，请填写 Wi-Fi 模块的 MAC 地址。",
            "name_required": "请为设备填写名称。",
            "unsupported_class": "该设备不是 class 0501 洗衣机；本集成目前只支持 class 0501。",
            "unsupported_model": "该设备的型号配置尚未受支持。",
        },
        "abort": {"already_configured": "这台洗衣机已经配置过了。"},
    },
    "options": {
        "step": {
            "init": {
                "title": "海尔本地设备选项",
                "description": "修改地址、localKey 或轮询间隔。",
                "data": {
                    "host": "局域网地址",
                    "local_key": "localKey（32 位十六进制或 local_key.json）",
                    "scan_interval": "轮询间隔（秒）",
                },
            }
        },
        "error": {
            "cannot_connect": "用这些设置无法解密状态报文。",
            "invalid_key": "localKey 必须是 32 位十六进制（或 local_key.json 文档）。",
        },
    },
}

EXTRA_SENSORS = {
    "raw_state": ("Raw state", "原始状态"),
    "feature_flags": ("Feature flags", "功能开关"),
}


def _entity_blocks(language: str) -> dict:
    en = language == "en"
    sensors: dict = {}
    binary: dict = {}
    for spec in specs.ALL_SENSORS:
        block = {"name": spec.name_en if en else spec.name_zh}
        if spec.enum:
            block["state"] = {
                token: (label_en if en else label_zh)
                for token, label_en, label_zh in enum_defs.ENUM_DEFS[spec.enum].values()
            }
        sensors[spec.key] = block
    for key, (name_en, name_zh) in EXTRA_SENSORS.items():
        sensors[key] = {"name": name_en if en else name_zh}
    for spec in specs.ALL_BINARY:
        binary[spec.key] = {"name": spec.name_en if en else spec.name_zh}
    return {"sensor": sensors, "binary_sensor": binary}


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    en = {**CONFIG_EN, "entity": _entity_blocks("en")}
    zh = {**CONFIG_ZH, "entity": _entity_blocks("zh")}
    _write(COMPONENT / "strings.json", en)
    _write(COMPONENT / "translations/en.json", en)
    _write(COMPONENT / "translations/zh-Hans.json", zh)
    print(f"sensors={len(en['entity']['sensor'])}, "
          f"binary={len(en['entity']['binary_sensor'])}")
    print("wrote strings.json, translations/en.json, translations/zh-Hans.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
