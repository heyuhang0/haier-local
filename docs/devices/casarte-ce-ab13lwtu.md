# Casarte CE AB13LWTUWCU1

This is the only device profile currently verified for Haier Local.

| Field | Value |
|---|---|
| Product | 卡萨帝揽光 W13 热泵洗烘一体 |
| Model | CE AB13LWTUWCU1 |
| Haier class | `0501` |
| uPlusId | `201c51890c31c308050100218006664300000000000000000000000000000040` |
| Local transport | uSS over TCP `56800` |
| Firmware observed | `e_4.6.38 / R_6.0.01` |
| Decoder map | `201c51890c31c30805010021800239584d000000000000000000000000000140` (219 fields) |

The map is selected from the MIT-licensed `haismart-local` catalogue. The
device's exact uPlusId is not in that catalogue, but this map placed every
observed field correctly.

## Verification

One local status report captured on 2026-11-08 decoded to **93 attributes**.
The same 93 names were present in Haier's cloud digital model for the device.
All **92 non-null cloud values matched** after normalizing booleans and decimal
formatting; `clothesAnionStatus` was null in the cloud snapshot.

The sanitized paired values and capture conditions are in
[`tests/fixtures/`](../../tests/fixtures/). That test is historical evidence for
this observation, not a decoder regression test: the raw report is not kept
because it requires the per-device key.

## Entity presentation

The integration exposes this profile as:

- 20 primary entities: remaining time, phase, program, running mode, message,
  wash temperature, spin speed, remaining main wash/rinse, current and total
  water/energy, plus power, running, door, door lock, remote control, child lock
  and problem.
- 21 enabled diagnostic entities: cycle counters, standby time, program state,
  detergent/softener/booster levels, drying fields, detergent type/ratio,
  dirt/stain/fabric, and subsystem problem sensors.
- 18 disabled-by-default diagnostic entities: dosing weights, detergent B, dry
  type/flag/cleaning reminder, air wash, cloud program fields, weights, wash
  speed, and the grouped `Feature flags` and `Raw state` entities.

The primary list is small because those are the values useful in automations;
diagnostic values stay available without crowding the device page. Clothing
recognition, voice-module and factory/test fields are exposed only through
`Raw state` for this profile.

## Behavior

- Read-only: no start, pause, cancel or settings writes are implemented.
- One uSS session at a time. Do not run another local poller against this
  washer while the integration is active.
- The profile map is specific to class `0501`; do not apply it to another class.
