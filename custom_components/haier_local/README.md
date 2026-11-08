# Haier Local

Local-only Home Assistant integration for the **Casarte CE AB13LWTUWCU1**
(Haier class `0501` washer). It talks directly to the appliance's uSS protocol
on **TCP 56800**, decrypts the status report with the per-device `localKey`, and
decodes it using Haier's published class-0501 byte map.

No cloud is used at runtime. See the [project README](../../README.md) for
installation, configuration and security, and
[`docs/protocol.md`](../../docs/protocol.md) for the protocol and verification
details.

## Entity layout

**Primary (visible, enabled)** — 20 entities:

- Remaining time, phase, program, running mode, message
- Wash temperature, spin speed, remaining main wash, remaining rinses
- Current/total water (L), current/total energy (kWh)
- Binary: power, running, door, door lock, remote control, child lock, problem

**Diagnostic (visible under Diagnostic, enabled)** — 21 entities:

- Current/total cycles, remaining standby, program started
- Detergent / softener / booster level
- Dry mode, dry status, dry time, dry level
- Detergent type/ratio, dirt level, stain type, fabric
- Inlet/drain/wash/spin/dry system problem sensors

**Diagnostic, disabled by default** — 18 entities:

- Detergent/softener dose, detergent B, dry type/flag/cleaning reminder
- Air wash time/level, cloud program id/source, default-settings/standby flags
- Set/measured weight, wash speed
- `Feature flags` (one entity with 22 optional flags as attributes)
- `Raw state` (one entity with all 93 decoded values as attributes)

**Never individual entities** (only in `Raw state`):

- Clothing-recognition raw words (`clothesInfo*`, `clothesRecog*`)
- Optional voice module (`voiceModule*`, `voiceStatus`)
- Factory/test flags (`forceDelete`, `testCmdReceiveStatus`)

## Languages

English is the source language; `translations/zh-Hans.json` provides Chinese.

- Entity names and enum states use Home Assistant's translation system:
  English HA shows `Phase` / `Standby / not started`; Chinese HA shows
  `洗涤阶段` / `待机/未启动`.
- Enum sensors use `SensorDeviceClass.ENUM` with stable tokens; the display
  label comes from `entity.sensor.<key>.state`.
- Numeric readings show the number with its unit; boolean features are binary
  sensors.
- Enum sensors expose `raw_value`, `label_en` and `label_zh` attributes for
  debugging. `Raw state` keeps the unmodified decoded values.

## Limits

- Read-only in this version. Controls (start/pause/cancel/settings) are not
  enabled.
- One uSS session at a time; do not run another local integration against the
  same washer while this one polls.
- The class-0501 map was verified on CE AB13LWTUWCU1; an unverified 0501 model
  may place some fields differently and asks for confirmation.

## Attribution

`vendor/haier_local_hrdp` is vendored from
[`enapt/haismart-local`](https://github.com/enapt/haismart-local), MIT licensed.
The protocol work and the class-0501 map originate there. This component is an
unofficial community project, not affiliated with Haier or Casarte.
