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


def _value(source: str):
    return lambda state: state.get(source)


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
    SensorSpec("current_water", "Current water", "本次用水量",
               source="currentWaterUsed", unit="L", icon="mdi:water",
               device_class="water", state_class="measurement"),
    SensorSpec("total_water", "Total water", "累计用水量",
               source="totalWaterUsed", unit="L", icon="mdi:water",
               device_class="water", state_class="total_increasing"),
    SensorSpec("current_energy", "Current energy", "本次用电量",
               source="currentElectricityUsed", unit="kWh",
               icon="mdi:lightning-bolt", device_class="energy",
               state_class="measurement"),
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
    BinarySpec("remote_control", "Remote control", "远程控制",
               source="remoteCtrValid", icon="mdi:remote",
               value_fn=_bool("remoteCtrValid")),
    BinarySpec("child_lock", "Child lock", "童锁", source="childLockStatus",
               icon="mdi:lock-alert", value_fn=_bool("childLockStatus")),
    BinarySpec("problem", "Problem", "故障",
               value_fn=lambda s: (s.get("_alarm_count") or 0) > 0,
               device_class="problem", icon="mdi:alert-circle",
               attributes_fn=lambda s: {
                   "alarm_count": s.get("_alarm_count", 0),
                   "alarm_codes": s.get("_alarm_codes", []),
                   "alarm_labels": s.get("_alarm_labels", []),
               }),
)

DIAGNOSTIC_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("current_cycle", "Current cycles", "周期内洗涤次数",
               source="currentWashCycle", icon="mdi:counter", diagnostic=True),
    SensorSpec("total_cycles", "Total cycles", "累计洗涤次数",
               source="totalWashCycle", icon="mdi:counter", diagnostic=True,
               state_class="total_increasing"),
    SensorSpec("remaining_standby", "Remaining standby", "剩余待机时间",
               source="remainingStandbyTime", unit="min", icon="mdi:timer-sand",
               device_class="duration", state_class="measurement", diagnostic=True),
    SensorSpec("detergent_level", "Detergent level", "洗涤剂余量",
               source="remainingDetergentStatus", enum="remaining_status",
               icon="mdi:cup-water", diagnostic=True),
    SensorSpec("softener_level", "Softener level", "柔顺剂余量",
               source="remainingSoftenerStatus", enum="remaining_status",
               icon="mdi:flask-outline", diagnostic=True),
    SensorSpec("dispersant_level", "Booster level", "助洗剂余量",
               source="remainingDispersantStatus", enum="remaining_status",
               icon="mdi:flask", diagnostic=True),
    SensorSpec("dry_mode", "Dry mode", "烘干程序", source="dryMode",
               enum="dry_mode", icon="mdi:tumble-dryer", diagnostic=True),
    SensorSpec("dry_time", "Dry time", "烘干时间", source="dryTime",
               unit="min", icon="mdi:timer", device_class="duration",
               state_class="measurement", diagnostic=True),
    SensorSpec("dry_level", "Dry level", "烘干强度", source="washerDryLevel",
               enum="dry_level", icon="mdi:tumble-dryer", diagnostic=True),
    SensorSpec("detergent_type", "Detergent type", "洗涤剂类型",
               source="detergentType", enum="detergent_type",
               icon="mdi:cup-water", diagnostic=True),
    SensorSpec("detergent_ratio", "Detergent ratio", "洗涤剂投放比例",
               source="detergentPercent", unit="%", icon="mdi:cup-water",
               diagnostic=True),
    SensorSpec("dirt_level", "Dirt level", "脏污度", source="dirtyLevel",
               enum="dirt_level", icon="mdi:liquid-spot", diagnostic=True),
    SensorSpec("stain_type", "Stain type", "特渍种类", source="stainType",
               enum="stain_type", icon="mdi:liquid-spot", diagnostic=True),
    SensorSpec("fabric", "Fabric", "衣物材质", source="texture",
               enum="fabric", icon="mdi:tshirt-crew", diagnostic=True),
)

DIAGNOSTIC_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("program_started", "Program started", "程序已运行",
               source="laundryCycleStatus", icon="mdi:play-circle",
               value_fn=_bool("laundryCycleStatus"), diagnostic=True),
    BinarySpec("dry_status", "Drying", "烘干中", source="dryStatus",
               icon="mdi:tumble-dryer", device_class="running",
               value_fn=_bool("dryStatus"), diagnostic=True),
    BinarySpec("drain_problem", "Drain problem", "排水系统异常",
               source="drainSysDiagResult", icon="mdi:pipe-valve",
               device_class="problem",
               value_fn=_bool("drainSysDiagResult", invert=True), diagnostic=True),
    BinarySpec("inlet_problem", "Inlet problem", "进水系统异常",
               source="inWaterSysDiagResult", icon="mdi:water-pump",
               device_class="problem",
               value_fn=_bool("inWaterSysDiagResult", invert=True), diagnostic=True),
    BinarySpec("spin_problem", "Spin problem", "脱水系统异常",
               source="spinSysDiagResult", icon="mdi:rotate-right",
               device_class="problem",
               value_fn=_bool("spinSysDiagResult", invert=True), diagnostic=True),
    BinarySpec("wash_problem", "Wash problem", "洗涤系统异常",
               source="washSysDiagResult", icon="mdi:washing-machine",
               device_class="problem",
               value_fn=_bool("washSysDiagResult", invert=True), diagnostic=True),
    BinarySpec("dry_problem", "Dry problem", "烘干系统异常",
               source="drySysDiagResult", icon="mdi:tumble-dryer",
               device_class="problem",
               value_fn=_bool("drySysDiagResult", invert=True), diagnostic=True),
)

DISABLED_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("haier_detergent_weight", "Detergent dose", "洗涤剂投放量",
               source="haier_DetergentWeight", icon="mdi:cup-water",
               diagnostic=True, enabled_default=False),
    SensorSpec("haier_softener_weight", "Softener dose", "柔顺剂投放量",
               source="haier_SoftenerWeight", icon="mdi:flask-outline",
               diagnostic=True, enabled_default=False),
    SensorSpec("detergent_b_ratio", "Detergent B ratio", "洗涤剂B投放比例",
               source="detergentBPercent", unit="%", icon="mdi:cup-water",
               diagnostic=True, enabled_default=False),
    SensorSpec("dry_type", "Dry type", "烘干方式", source="dryType",
               enum="dry_type", icon="mdi:tumble-dryer",
               diagnostic=True, enabled_default=False),
    SensorSpec("air_wash_time", "Air wash time", "空气洗时间",
               source="airWashTime", unit="min", icon="mdi:air-filter",
               device_class="duration", state_class="measurement",
               diagnostic=True, enabled_default=False),
    SensorSpec("air_wash_level", "Air wash level", "空气洗温度档位",
               source="airWashTempLevel", enum="air_wash_level",
               icon="mdi:air-filter", diagnostic=True, enabled_default=False),
    SensorSpec("cloud_prog_id", "Cloud program ID", "云程序编号",
               source="cloudProgId", icon="mdi:cloud",
               diagnostic=True, enabled_default=False),
    SensorSpec("cloud_prog_src", "Cloud program source", "云程序启动来源",
               source="cloudProgSrc", enum="cloud_prog_src",
               icon="mdi:cloud", diagnostic=True, enabled_default=False),
    SensorSpec("weight_set", "Set clothes weight", "设定衣物重量",
               source="weight", icon="mdi:weight-kilogram",
               diagnostic=True, enabled_default=False),
    SensorSpec("weight_actual", "Measured clothes weight", "实测衣物重量",
               source="actualWeight", icon="mdi:weight",
               diagnostic=True, enabled_default=False),
    SensorSpec("wash_speed", "Wash speed", "设定洗涤转速",
               source="washSpeed", icon="mdi:speedometer",
               diagnostic=True, enabled_default=False),
)

DISABLED_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("detergent_b_status", "Detergent B dosing", "洗涤剂B投放",
               source="detergentBStatus", icon="mdi:cup-water",
               value_fn=_bool("detergentBStatus"),
               diagnostic=True, enabled_default=False),
    BinarySpec("dry_prog_flag", "Dry program flag", "烘干程序标志",
               source="dryProgFlag", icon="mdi:tumble-dryer",
               value_fn=_bool("dryProgFlag"),
               diagnostic=True, enabled_default=False),
    BinarySpec("dry_cleaning_needed", "Dry cleaning needed", "需要干洗",
               source="dryCleaningNeeded", icon="mdi:tshirt-crew",
               value_fn=_bool("dryCleaningNeeded"),
               diagnostic=True, enabled_default=False),
    BinarySpec("def_set_allowed", "Default settings allowed", "允许设置默认参数",
               source="defSetAllowed", icon="mdi:cog",
               value_fn=_bool("defSetAllowed"),
               diagnostic=True, enabled_default=False),
    BinarySpec("standby_extended", "Standby extended", "延时待机",
               source="standbyTimeExtended", icon="mdi:timer-pause",
               value_fn=_bool("standbyTimeExtended"),
               diagnostic=True, enabled_default=False),
)

# This profile keeps these fields in Raw state rather than as entities.
RAW_ONLY: frozenset[str] = frozenset({
    "clothesIdIndex", "clothesInfoHW", "clothesInfoLW", "clothesInfoMW",
    "clothesRecogNum", "clothesRecogResult", "clothesRecogStatus",
    "voiceModuleDataDef", "voiceModuleOnOffStatus", "voiceModuleVolume",
    "voiceModuleWakeStatus", "voiceModuleWakeUp", "voiceStatus",
    "forceDelete", "testCmdReceiveStatus",
})

# Grouped feature flags (diagnostic, disabled by default).
FEATURE_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("antiAllergyStatus", "Anti-allergy", "防过敏"),
    ("autoDetergentStatus", "Auto detergent", "洗涤剂自动投放"),
    ("autoDisinfectantStatus", "Auto disinfectant", "消毒剂自动投放"),
    ("autoSoftenerStatus", "Auto softener", "柔顺剂自动投放"),
    ("buzzerDisabled", "Buzzer muted", "蜂鸣静音"),
    ("buzzerDisabledCurrent", "Buzzer muted this cycle", "本周期蜂鸣关闭"),
    ("clothesAnionStatus", "Clothes anion", "衣物负离子"),
    ("creaseResistSoakStatus", "Crease-resistant soak", "防皱浸泡"),
    ("energySavingStatus", "Energy saving", "节能洗"),
    ("highWaterLevelStatus", "High water level", "高水位"),
    ("intelligenceStatus", "Smart program", "智慧洗"),
    ("loosenStatus", "Post-wash tumbling", "抖散"),
    ("nightWashStatus", "Night wash", "夜间洗"),
    ("permanentPressStatus", "Permanent press", "免熨烫"),
    ("purifiedWashStatus", "Purified wash", "净水洗"),
    ("resnStatus", "Scheduled", "预约"),
    ("shoesAnionStatus", "Shoe anion", "运动鞋负离子"),
    ("soakWashStatus", "Soak wash", "浸泡洗"),
    ("speedUpStatus", "Speed up", "加速洗"),
    ("steamWashStatus", "Steam wash", "蒸汽洗"),
    ("strongStatus", "Strong wash", "强力去污"),
    ("uvSterilizationStatus", "UV sterilization", "紫外杀菌"),
)

ALL_SENSORS = PRIMARY_SENSORS + DIAGNOSTIC_SENSORS + DISABLED_SENSORS
ALL_BINARY = PRIMARY_BINARY + DIAGNOSTIC_BINARY + DISABLED_BINARY

# The 93 attributes this profile exposes in the grouped Raw state entity.
RAW_STATE_FIELDS = (
    "actualWeight",
    "airWashTempLevel",
    "airWashTime",
    "antiAllergyStatus",
    "autoDetergentStatus",
    "autoDisinfectantStatus",
    "autoSoftenerStatus",
    "buzzerDisabled",
    "buzzerDisabledCurrent",
    "childLockStatus",
    "clothesAnionStatus",
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
    "haier_DetergentWeight",
    "haier_SoftenerWeight",
    "highWaterLevelStatus",
    "inWaterSysDiagResult",
    "intelligenceStatus",
    "laundryCycle",
    "laundryCycleStatus",
    "loosenStatus",
    "message",
    "nightWashStatus",
    "onOffStatus",
    "permanentPressStatus",
    "purifiedWashStatus",
    "remainingDetergentStatus",
    "remainingDispersantStatus",
    "remainingMainWashTime",
    "remainingRinseTimes",
    "remainingSoftenerStatus",
    "remainingStandbyTime",
    "remainingTimeHH",
    "remainingTimeMM",
    "remoteCtrValid",
    "resnStatus",
    "runningMode",
    "shoesAnionStatus",
    "soakWashStatus",
    "speedUpStatus",
    "spinSpeed",
    "spinSysDiagResult",
    "stainType",
    "standbyTimeExtended",
    "steamWashStatus",
    "strongStatus",
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
    "weight",
)
