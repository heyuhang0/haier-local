"""Entity specs: what to expose, how, and whether it is primary/diagnostic/off."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


def as_bool(raw) -> bool | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("true", "1", "on", "yes", "开", "是")
    return bool(raw)


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


def _bool(source: str, invert: bool = False):
    def value(state):
        parsed = as_bool(state.get(source))
        if parsed is None:
            return None
        return (not parsed) if invert else parsed
    return value


@dataclass(frozen=True)
class SensorSpec:
    key: str
    name_en: str
    name_zh: str
    source: str | None = None
    value_fn: Callable[[dict], Any] | None = None
    unit: str | None = None
    icon: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    enum: str | None = None
    diagnostic: bool = False
    enabled_default: bool = True
    attributes_fn: Callable[[dict], dict] | None = None


@dataclass(frozen=True)
class BinarySpec:
    key: str
    name_en: str
    name_zh: str
    source: str | None = None
    value_fn: Callable[[dict], bool | None] | None = None
    icon: str | None = None
    device_class: str | None = None
    diagnostic: bool = False
    enabled_default: bool = True
    attributes_fn: Callable[[dict], dict] | None = None


PRIMARY_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("remaining_time", "Remaining time", "剩余时间",
               value_fn=remaining_minutes, unit="min",
               icon="mdi:timer-outline", device_class="duration",
               state_class="measurement"),
    SensorSpec("phase", "Phase", "洗涤阶段", source="cyclePhase",
               enum="phase", icon="mdi:washing-machine"),
    SensorSpec("program", "Program", "洗衣程序", source="laundryCycle",
               enum="program", icon="mdi:format-list-bulleted"),
    SensorSpec("running_mode", "Running mode", "运行状态", source="runningMode",
               enum="running_mode", icon="mdi:play-pause"),
    SensorSpec("message", "Message", "提示信息", source="message",
               enum="message", icon="mdi:message-alert"),
    SensorSpec("wash_temp", "Wash temperature", "洗涤水温", source="washTemp",
               unit="°C", icon="mdi:thermometer-water",
               device_class="temperature", state_class="measurement"),
    SensorSpec("spin_speed", "Spin speed", "脱水转速", source="spinSpeed",
               unit="rpm", icon="mdi:rotate-right", state_class="measurement"),
    SensorSpec("remaining_main_wash", "Remaining main wash", "剩余主洗时间",
               source="remainingMainWashTime", unit="min", icon="mdi:timer-sand",
               device_class="duration", state_class="measurement"),
    SensorSpec("remaining_rinse", "Remaining rinses", "剩余漂洗次数",
               source="remainingRinseTimes", icon="mdi:water-sync",
               state_class="measurement"),
    SensorSpec("remaining_standby", "Remaining standby", "剩余待机时间",
               source="remainingStandbyTime", unit="min", icon="mdi:timer-sand",
               device_class="duration", state_class="measurement"),
    SensorSpec("detergent_level", "Detergent level", "洗涤剂余量",
               source="remainingDetergentStatus", enum="remaining_status",
               icon="mdi:cup-water"),
    SensorSpec("softener_level", "Softener level", "柔顺剂余量",
               source="remainingSoftenerStatus", enum="remaining_status",
               icon="mdi:flask-outline"),
    SensorSpec("dispersant_level", "Booster level", "助洗剂余量",
               source="remainingDispersantStatus", enum="remaining_status",
               icon="mdi:flask"),
    SensorSpec("dry_mode", "Dry mode", "烘干程序", source="dryMode",
               enum="dry_mode", icon="mdi:tumble-dryer"),
    SensorSpec("dry_time", "Dry time", "烘干时间", source="dryTime",
               unit="min", icon="mdi:timer", device_class="duration",
               state_class="measurement"),
    SensorSpec("dry_level", "Dry level", "烘干强度", source="washerDryLevel",
               enum="dry_level", icon="mdi:tumble-dryer"),
    SensorSpec("dry_type", "Dry type", "烘干方式", source="dryType",
               enum="dry_type", icon="mdi:tumble-dryer"),
    SensorSpec("detergent_type", "Detergent type", "洗涤剂类型",
               source="detergentType", enum="detergent_type",
               icon="mdi:cup-water"),
    SensorSpec("detergent_ratio", "Detergent ratio", "洗涤剂投放比例",
               source="detergentPercent", unit="%", icon="mdi:cup-water"),
    SensorSpec("softener_concentration", "Softener concentration", "柔顺剂浓度",
               source="softenerConcentrationType", enum="softener_concentration",
               icon="mdi:flask-outline"),
    SensorSpec("softener_ratio", "Softener ratio", "柔顺剂投放比例",
               source="softenerPercent", unit="%", icon="mdi:flask-outline"),
    SensorSpec("air_wash_time", "Air wash time", "空气洗时间",
               source="airWashTime", unit="min", icon="mdi:air-filter",
               device_class="duration", state_class="measurement"),
    SensorSpec("air_wash_level", "Air wash level", "空气洗温度档位",
               source="airWashTempLevel", enum="air_wash_level",
               icon="mdi:air-filter"),
    SensorSpec("weight_actual", "Measured clothes weight", "实测衣物重量",
               source="actualWeight", unit="kg", icon="mdi:weight"),
    SensorSpec("haier_detergent_weight", "Detergent dose", "洗涤剂投放量",
               source="haier_DetergentWeight", unit="g", icon="mdi:cup-water"),
    SensorSpec("haier_softener_weight", "Softener dose", "柔顺剂投放量",
               source="haier_SoftenerWeight", unit="g", icon="mdi:flask-outline"),
    SensorSpec("total_water", "Total water", "累计用水量",
               source="totalWaterUsed", unit="L", icon="mdi:water",
               device_class="water", state_class="total_increasing"),
    SensorSpec("total_energy", "Total energy", "累计用电量",
               source="totalElectricityUsed", unit="kWh",
               icon="mdi:lightning-bolt", device_class="energy",
               state_class="total_increasing"),
)

PRIMARY_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("power", "Power", "电源", source="onOffStatus",
               device_class="power", icon="mdi:power", value_fn=_bool("onOffStatus")),
    BinarySpec("running", "Running", "运行中", value_fn=is_running,
               device_class="running", icon="mdi:washing-machine"),
    BinarySpec("door", "Door", "筒门", source="doorStatus",
               device_class="door", icon="mdi:door", value_fn=_bool("doorStatus")),
    BinarySpec("door_lock", "Door lock", "门锁", source="doorLockStatus",
               device_class="lock", icon="mdi:lock",
               value_fn=_bool("doorLockStatus", invert=True)),
    BinarySpec("child_lock", "Child lock", "童锁", source="childLockStatus",
               icon="mdi:lock-alert", value_fn=_bool("childLockStatus")),
    BinarySpec("dry_status", "Drying", "烘干中", source="dryStatus",
               icon="mdi:tumble-dryer", device_class="running",
               value_fn=_bool("dryStatus")),
    BinarySpec("anti_allergy", "Anti-allergy", "防过敏",
               source="antiAllergyStatus", icon="mdi:shield-check",
               value_fn=_bool("antiAllergyStatus")),
    BinarySpec("uv_sterilization", "UV sterilization", "紫外杀菌",
               source="uvSterilizationStatus", icon="mdi:weather-sunny",
               value_fn=_bool("uvSterilizationStatus")),
    BinarySpec("scheduled", "Scheduled", "预约",
               source="resnStatus", icon="mdi:calendar-clock",
               value_fn=_bool("resnStatus")),
    BinarySpec("care", "Care", "护理", source="careSwitch",
               icon="mdi:heart-outline", value_fn=_bool("careSwitch")),
    BinarySpec("wet_cleaning", "Wet cleaning", "湿洗",
               source="wetcleaningProgram", icon="mdi:water",
               value_fn=_bool("wetcleaningProgram")),
)

DIAGNOSTIC_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("current_cycle", "Current cycles", "周期内洗涤次数",
               source="currentWashCycle", icon="mdi:counter", diagnostic=True),
    SensorSpec("total_cycles", "Total cycles", "累计洗涤次数",
               source="totalWashCycle", icon="mdi:counter", diagnostic=True,
               state_class="total_increasing"),
    SensorSpec("drain_diagnostic", "Drain diagnostic result", "排水系统诊断结果",
               source="drainSysDiagResult", enum="diag_result",
               icon="mdi:pipe-valve", diagnostic=True),
    SensorSpec("inlet_diagnostic", "Inlet diagnostic result", "进水系统诊断结果",
               source="inWaterSysDiagResult", enum="diag_result",
               icon="mdi:water-pump", diagnostic=True),
    SensorSpec("spin_diagnostic", "Spin diagnostic result", "脱水系统诊断结果",
               source="spinSysDiagResult", enum="diag_result",
               icon="mdi:rotate-right", diagnostic=True),
    SensorSpec("wash_diagnostic", "Wash diagnostic result", "洗涤系统诊断结果",
               source="washSysDiagResult", enum="diag_result",
               icon="mdi:washing-machine", diagnostic=True),
    SensorSpec("dry_diagnostic", "Dry diagnostic result", "烘干系统诊断结果",
               source="drySysDiagResult", enum="diag_result",
               icon="mdi:tumble-dryer", diagnostic=True),
    # Per-cycle counters reset without a reliable last_reset; leaving
    # state_class unset keeps them out of long-term statistics.
    SensorSpec("current_water", "Current water", "本次用水量",
               source="currentWaterUsed", unit="L", icon="mdi:water",
               device_class="water", diagnostic=True, enabled_default=False),
    SensorSpec("current_energy", "Current energy", "本次用电量",
               source="currentElectricityUsed", unit="kWh",
               icon="mdi:lightning-bolt", device_class="energy",
               diagnostic=True, enabled_default=False),
    SensorSpec("cloud_prog_id", "Cloud program ID", "云程序编号",
               source="cloudProgId", icon="mdi:cloud",
               diagnostic=True, enabled_default=False),
    SensorSpec("cloud_prog_src", "Cloud program source", "云程序启动来源",
               source="cloudProgSrc", enum="cloud_prog_src",
               icon="mdi:cloud", diagnostic=True, enabled_default=False),
)

DIAGNOSTIC_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("problem", "Problem", "故障",
               value_fn=lambda s: (s.get("_alarm_count") or 0) > 0,
               device_class="problem", icon="mdi:alert-circle", diagnostic=True,
               attributes_fn=lambda s: {
                   "alarm_count": s.get("_alarm_count", 0),
                   "alarm_codes": s.get("_alarm_codes", []),
                   "alarm_labels": s.get("_alarm_labels", []),
               }),
    BinarySpec("remote_control", "Remote control", "远程控制",
               source="remoteCtrValid", icon="mdi:remote", diagnostic=True,
               value_fn=_bool("remoteCtrValid")),
    BinarySpec("remote_control_enabled", "Remote control enabled", "远程控制使能",
               source="remoteCtrEnabled", icon="mdi:remote", diagnostic=True,
               value_fn=_bool("remoteCtrEnabled")),
    BinarySpec("remote_power_on", "Remote power-on", "远程开机",
               source="remotePowerOn", icon="mdi:power-plug", diagnostic=True,
               value_fn=_bool("remotePowerOn")),
    BinarySpec("long_term_authorization", "Long-term authorization", "长期授权",
               source="longTimeAuthorizationStatus", icon="mdi:shield-key",
               diagnostic=True,
               value_fn=_bool("longTimeAuthorizationStatus")),
    BinarySpec("standby_extended", "Standby extended", "延时待机",
               source="standbyTimeExtended", icon="mdi:timer-pause",
               diagnostic=True, value_fn=_bool("standbyTimeExtended")),
    BinarySpec("dry_prog_flag", "Dry program flag", "烘干程序标志",
               source="dryProgFlag", icon="mdi:tumble-dryer", diagnostic=True,
               enabled_default=False, value_fn=_bool("dryProgFlag")),
    BinarySpec("def_set_allowed", "Default settings allowed", "允许设置默认参数",
               source="defSetAllowed", icon="mdi:cog", diagnostic=True,
               enabled_default=False, value_fn=_bool("defSetAllowed")),
)

DISABLED_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("dirt_level", "Dirt level", "脏污度", source="dirtyLevel",
               enum="dirt_level", icon="mdi:liquid-spot",
               enabled_default=False),
    SensorSpec("stain_type", "Stain type", "特渍种类", source="stainType",
               enum="stain_type", icon="mdi:liquid-spot",
               enabled_default=False),
    SensorSpec("fabric", "Fabric", "衣物材质", source="texture",
               enum="fabric", icon="mdi:tshirt-crew",
               enabled_default=False),
    SensorSpec("water_hardness", "Water hardness", "水硬度",
               source="hardnessValue", icon="mdi:water-percent",
               enabled_default=False),
    SensorSpec("box1_remaining", "Cartridge 1 level", "墨盒1余量",
               source="box1RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", enabled_default=False),
    SensorSpec("box2_remaining", "Cartridge 2 level", "墨盒2余量",
               source="box2RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", enabled_default=False),
    SensorSpec("box3_remaining", "Cartridge 3 level", "墨盒3余量",
               source="box3RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", enabled_default=False),
    SensorSpec("box4_remaining", "Cartridge 4 level", "墨盒4余量",
               source="box4RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", enabled_default=False),
    SensorSpec("detergent_b_ratio", "Detergent B ratio", "洗涤剂B投放比例",
               source="detergentBPercent", unit="%", icon="mdi:cup-water",
               enabled_default=False),
    SensorSpec("weight_set", "Set clothes weight", "设定衣物重量",
               source="weight", icon="mdi:weight-kilogram",
               enabled_default=False),
    SensorSpec("wash_speed", "Wash speed", "设定洗涤转速",
               source="washSpeed", icon="mdi:speedometer",
               enabled_default=False),
    SensorSpec("photo_plasma_care_time", "Photo plasma care time",
               "光等离子护理时间", source="photoPlasmaCareTime", unit="min",
               icon="mdi:lightning-bolt", enabled_default=False),
)

DISABLED_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("detergent_b_status", "Detergent B dosing", "洗涤剂B投放",
               source="detergentBStatus", icon="mdi:cup-water",
               value_fn=_bool("detergentBStatus"), enabled_default=False),
    BinarySpec("dry_cleaning_needed", "Dry cleaning needed", "需要干洗",
               source="dryCleaningNeeded", icon="mdi:tshirt-crew",
               value_fn=_bool("dryCleaningNeeded"), enabled_default=False),
    BinarySpec("program_started", "Program started", "程序已运行",
               source="laundryCycleStatus", icon="mdi:play-circle",
               value_fn=_bool("laundryCycleStatus"), enabled_default=False),
    BinarySpec("anti_crease", "Anti-crease", "抗皱",
               source="antiCrease", icon="mdi:iron",
               value_fn=_bool("antiCrease"), enabled_default=False),
    BinarySpec("fresh_air", "Fresh air", "新风",
               source="freshAir", icon="mdi:air-filter",
               value_fn=_bool("freshAir"), enabled_default=False),
    BinarySpec("photo_plasma", "Photo plasma", "光等离子",
               source="photoPlasmaStatus", icon="mdi:lightning-bolt",
               value_fn=_bool("photoPlasmaStatus"), enabled_default=False),
    BinarySpec("spa_rinse_heat", "SPA rinse heat", "SPA漂洗加热",
               source="spaRinseHeatStatus", icon="mdi:hot-tub",
               value_fn=_bool("spaRinseHeatStatus"), enabled_default=False),
)

# This profile keeps these fields in Raw state rather than as entities.
RAW_ONLY: frozenset[str] = frozenset({
    "box1Concentration", "box1LiquidType", "box1Volume",
    "box2Concentration", "box2LiquidType", "box2Volume",
    "box3Concentration", "box3LiquidType", "box3Volume",
    "box4Concentration", "box4LiquidType", "box4Volume",
    "clothesIdIndex", "clothesInfoHW", "clothesInfoLW", "clothesInfoMW",
    "clothesRecogNum", "clothesRecogResult", "clothesRecogStatus",
    "localProgName1", "localProgName2",
    "serverModeStatus", "targetLaundryProcedure",
    "voiceModuleDataDef", "voiceModuleOnOffStatus", "voiceModuleVolume",
    "voiceModuleWakeStatus", "voiceModuleWakeUp", "voiceStatus",
    "forceDelete", "testCmdReceiveStatus",
})

ALL_SENSORS = PRIMARY_SENSORS + DIAGNOSTIC_SENSORS + DISABLED_SENSORS
ALL_BINARY = PRIMARY_BINARY + DIAGNOSTIC_BINARY + DISABLED_BINARY

# The 132 `6D01` attributes this profile exposes in the grouped Raw state entity.
RAW_STATE_FIELDS = (
    "actualWeight",
    "airWashTempLevel",
    "airWashTime",
    "antiAllergyStatus",
    "antiCrease",
    "autoDetergentStatus",
    "autoDisinfectantStatus",
    "autoSoftenerStatus",
    "box1Concentration",
    "box1InjectStatus",
    "box1LiquidType",
    "box1RemainingStatus",
    "box1Volume",
    "box2Concentration",
    "box2InjectStatus",
    "box2LiquidType",
    "box2RemainingStatus",
    "box2Volume",
    "box3Concentration",
    "box3InjectStatus",
    "box3LiquidType",
    "box3RemainingStatus",
    "box3Volume",
    "box4Concentration",
    "box4InjectStatus",
    "box4LiquidType",
    "box4RemainingStatus",
    "box4Volume",
    "buzzerDisabled",
    "buzzerDisabledCurrent",
    "careSwitch",
    "childLockStatus",
    "clothesIdIndex",
    "clothesInfoHW",
    "clothesInfoLW",
    "clothesInfoMW",
    "clothesRecogNum",
    "clothesRecogResult",
    "clothesRecogStatus",
    "cloudProgId",
    "cloudProgSrc",
    "creaseResistSoakStatus",
    "currentElectricityUsed",
    "currentWashCycle",
    "currentWaterUsed",
    "cyclePhase",
    "defSetAllowed",
    "detergentBPercent",
    "detergentBStatus",
    "detergentPercent",
    "detergentType",
    "dirtyLevel",
    "doorLockStatus",
    "doorStatus",
    "drainSysDiagResult",
    "dryCleaningNeeded",
    "dryMode",
    "dryProgFlag",
    "dryStatus",
    "drySysDiagResult",
    "dryTime",
    "dryType",
    "energySavingStatus",
    "forceDelete",
    "freshAir",
    "haier_DetergentWeight",
    "haier_SoftenerWeight",
    "hardnessValue",
    "highWaterLevelStatus",
    "inWaterSysDiagResult",
    "intelligenceStatus",
    "laundryCycle",
    "laundryCycleStatus",
    "localProgName1",
    "localProgName2",
    "localSelectAndStartCloudProg",
    "longTimeAuthorizationStatus",
    "loosenStatus",
    "message",
    "nightWashStatus",
    "onOffStatus",
    "permanentPressStatus",
    "photoPlasmaCareTime",
    "photoPlasmaStatus",
    "purifiedWashStatus",
    "remainingDetergentStatus",
    "remainingDispersantStatus",
    "remainingMainWashTime",
    "remainingRinseTimes",
    "remainingSoftenerStatus",
    "remainingStandbyTime",
    "remainingTimeHH",
    "remainingTimeMM",
    "remoteCtrEnabled",
    "remoteCtrValid",
    "remotePowerOn",
    "resnStatus",
    "runningMode",
    "serverModeStatus",
    "shoesAnionStatus",
    "soakWashStatus",
    "softenerConcentrationType",
    "softenerPercent",
    "spaRinseHeatStatus",
    "speedUpStatus",
    "spinSpeed",
    "spinSysDiagResult",
    "stainType",
    "standbyTimeExtended",
    "steamWashStatus",
    "strongStatus",
    "targetLaundryProcedure",
    "testCmdReceiveStatus",
    "texture",
    "totalElectricityUsed",
    "totalWashCycle",
    "totalWaterUsed",
    "uvSterilizationStatus",
    "voiceModuleDataDef",
    "voiceModuleOnOffStatus",
    "voiceModuleVolume",
    "voiceModuleWakeStatus",
    "voiceModuleWakeUp",
    "voiceStatus",
    "washSpeed",
    "washSysDiagResult",
    "washTemp",
    "washerDryLevel",
    "wdLinkageEnable",
    "wdLinkageStatus",
    "weight",
    "wetcleaningProgram",
)
