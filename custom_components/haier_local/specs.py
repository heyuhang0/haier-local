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
    # Per-cycle counters reset without a reliable last_reset; leaving
    # state_class unset keeps them out of long-term statistics.
    SensorSpec("current_water", "Current water", "本次用水量",
               source="currentWaterUsed", unit="L", icon="mdi:water",
               device_class="water"),
    SensorSpec("total_water", "Total water", "累计用水量",
               source="totalWaterUsed", unit="L", icon="mdi:water",
               device_class="water", state_class="total_increasing"),
    SensorSpec("current_energy", "Current energy", "本次用电量",
               source="currentElectricityUsed", unit="kWh",
               icon="mdi:lightning-bolt", device_class="energy"),
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
    SensorSpec("softener_concentration", "Softener concentration", "柔顺剂浓度",
               source="softenerConcentrationType", enum="softener_concentration",
               icon="mdi:flask-outline", diagnostic=True),
    SensorSpec("softener_ratio", "Softener ratio", "柔顺剂投放比例",
               source="softenerPercent", unit="%", icon="mdi:flask-outline",
               diagnostic=True),
    SensorSpec("dirt_level", "Dirt level", "脏污度", source="dirtyLevel",
               enum="dirt_level", icon="mdi:liquid-spot", diagnostic=True),
    SensorSpec("stain_type", "Stain type", "特渍种类", source="stainType",
               enum="stain_type", icon="mdi:liquid-spot", diagnostic=True),
    SensorSpec("fabric", "Fabric", "衣物材质", source="texture",
               enum="fabric", icon="mdi:tshirt-crew", diagnostic=True),
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
)

DIAGNOSTIC_BINARY: tuple[BinarySpec, ...] = (
    BinarySpec("program_started", "Program started", "程序已运行",
               source="laundryCycleStatus", icon="mdi:play-circle",
               value_fn=_bool("laundryCycleStatus"), diagnostic=True),
    BinarySpec("dry_status", "Drying", "烘干中", source="dryStatus",
               icon="mdi:tumble-dryer", device_class="running",
               value_fn=_bool("dryStatus"), diagnostic=True),
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
    SensorSpec("water_hardness", "Water hardness", "水硬度",
               source="hardnessValue", icon="mdi:water-percent",
               diagnostic=True, enabled_default=False),
    SensorSpec("box1_remaining", "Cartridge 1 level", "墨盒1余量",
               source="box1RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", diagnostic=True, enabled_default=False),
    SensorSpec("box2_remaining", "Cartridge 2 level", "墨盒2余量",
               source="box2RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", diagnostic=True, enabled_default=False),
    SensorSpec("box3_remaining", "Cartridge 3 level", "墨盒3余量",
               source="box3RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", diagnostic=True, enabled_default=False),
    SensorSpec("box4_remaining", "Cartridge 4 level", "墨盒4余量",
               source="box4RemainingStatus", enum="box_remaining",
               icon="mdi:cup-water", diagnostic=True, enabled_default=False),
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
    "box1Concentration", "box1LiquidType", "box1Volume",
    "box2Concentration", "box2LiquidType", "box2Volume",
    "box3Concentration", "box3LiquidType", "box3Volume",
    "box4Concentration", "box4LiquidType", "box4Volume",
    "clothesIdIndex", "clothesInfoHW", "clothesInfoLW", "clothesInfoMW",
    "clothesRecogNum", "clothesRecogResult", "clothesRecogStatus",
    "localProgName1", "localProgName2",
    "photoPlasmaCareTime", "serverModeStatus", "targetLaundryProcedure",
    "voiceModuleDataDef", "voiceModuleOnOffStatus", "voiceModuleVolume",
    "voiceModuleWakeStatus", "voiceModuleWakeUp", "voiceStatus",
    "forceDelete", "testCmdReceiveStatus",
})

# Grouped feature flags (diagnostic, disabled by default).
FEATURE_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("antiAllergyStatus", "Anti-allergy", "防过敏"),
    ("antiCrease", "Anti-crease", "抗皱"),
    ("autoDetergentStatus", "Auto detergent", "洗涤剂自动投放"),
    ("autoDisinfectantStatus", "Auto disinfectant", "消毒剂自动投放"),
    ("autoSoftenerStatus", "Auto softener", "柔顺剂自动投放"),
    ("box1InjectStatus", "Cartridge 1 dosing", "墨盒1投放"),
    ("box2InjectStatus", "Cartridge 2 dosing", "墨盒2投放"),
    ("box3InjectStatus", "Cartridge 3 dosing", "墨盒3投放"),
    ("box4InjectStatus", "Cartridge 4 dosing", "墨盒4投放"),
    ("buzzerDisabled", "Buzzer muted", "蜂鸣静音"),
    ("buzzerDisabledCurrent", "Buzzer muted this cycle", "本周期蜂鸣关闭"),
    ("careSwitch", "Care", "护理"),
    ("creaseResistSoakStatus", "Crease-resistant soak", "防皱浸泡"),
    ("energySavingStatus", "Energy saving", "节能洗"),
    ("freshAir", "Fresh air", "新风"),
    ("highWaterLevelStatus", "High water level", "高水位"),
    ("intelligenceStatus", "Smart program", "智慧洗"),
    ("localSelectAndStartCloudProg", "Local cloud-program start", "本机启动云程序"),
    ("longTimeAuthorizationStatus", "Long-term authorisation", "长期授权"),
    ("loosenStatus", "Post-wash tumbling", "抖散"),
    ("nightWashStatus", "Night wash", "夜间洗"),
    ("permanentPressStatus", "Permanent press", "免熨烫"),
    ("photoPlasmaStatus", "Photo plasma", "光等离子"),
    ("purifiedWashStatus", "Purified wash", "净水洗"),
    ("remoteCtrEnabled", "Remote control enabled", "远程控制使能"),
    ("remotePowerOn", "Remote power-on", "远程开机"),
    ("resnStatus", "Scheduled", "预约"),
    ("shoesAnionStatus", "Shoe anion", "运动鞋负离子"),
    ("soakWashStatus", "Soak wash", "浸泡洗"),
    ("spaRinseHeatStatus", "SPA rinse heat", "SPA漂洗加热"),
    ("speedUpStatus", "Speed up", "加速洗"),
    ("steamWashStatus", "Steam wash", "蒸汽洗"),
    ("strongStatus", "Strong wash", "强力去污"),
    ("uvSterilizationStatus", "UV sterilization", "紫外杀菌"),
    ("wdLinkageEnable", "Washer-dryer linkage enabled", "洗烘联动使能"),
    ("wdLinkageStatus", "Washer-dryer linkage", "洗烘联动"),
    ("wetcleaningProgram", "Wet cleaning", "湿洗"),
)

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
