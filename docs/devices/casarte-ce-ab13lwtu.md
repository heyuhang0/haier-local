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
| Decoder map | Exact uPlusId, projected from Haier's configFile (227 properties, 132 `6D01` fields) |

The map is now the device's exact configFile rather than the neighbouring
`0501` catalogue record. The file also contains 312 `Bigdata` fields for the
`7D01`-`7D10` reports, which the integration does not query yet. The public
fetch and projection commands are in
[`docs/maintenance.md`](../maintenance.md#update-the-device-map).

## Verification

One local status report observed during initial development (2026-11-08,
firmware `e_4.6.38 / R_6.0.01`) decoded to 93 attributes with the then-selected
neighbouring map. The exact configFile now used by the profile carries 132
`6D01` fields; the earlier cloud comparison still supports the shared positions
(92 non-null cloud values matched, `clothesAnionStatus` was null).

The repository does not currently contain the raw report or the original cloud
response, so those numbers are development observations rather than an
independently reproducible fixture. `tools/read_washer.py --raw-out` can capture
a decrypted report for a future regression test; see
[`docs/maintenance.md`](../maintenance.md).

## Entity presentation

The integration exposes this profile as:

- 20 primary entities: remaining time, phase, program, running mode, message,
  wash temperature, spin speed, remaining main wash/rinse, current and total
  water/energy, plus power, running, door, door lock, remote control, child lock
  and problem.
- 23 enabled diagnostic entities: cycle counters, standby time, program state,
  detergent/softener/booster levels, drying fields, detergent type/ratio,
  softener concentration/ratio, dirt/stain/fabric, and the five subsystem
  diagnostic-result sensors.
- 21 disabled-by-default diagnostic entities: dosing weights, detergent B, dry
  type/flag/cleaning reminder, air wash, cloud program fields, weights, wash
  speed, water hardness, four cartridge levels, and the grouped
  `Feature flags` and `Raw state` entities.

The primary list is small because those are the values useful in automations;
diagnostic values stay available without crowding the device page. Clothing
recognition, voice-module, cartridge detail and factory/test fields are exposed
only through `Raw state`; the 37 optional booleans are grouped in
`Feature flags`. `Raw state` now carries all 132 `6D01` fields from the exact
configFile.

Category rules for the optional fields:

- **Primary:** none added; the existing core status set is unchanged.
- **Diagnostic, enabled:** softener concentration and softener ratio, parallel
  to the existing detergent type/ratio.
- **Diagnostic, disabled:** water hardness and the four optional cartridge
  levels. They are useful when the matching hardware is fitted, but not common.
- **Feature flags:** new booleans such as anti-crease, fresh air, photo plasma,
  remote-control enable, linkage and cartridge dosing stay in the grouped
  diagnostic entity rather than becoming individual entities.
- **Raw only:** cartridge concentration/liquid type/volume, local program
  names, service mode, photo-plasma care time and the program-storage index.

## Behavior

- Read-only: no start, pause, cancel or settings writes are implemented.
- One uSS session at a time. Do not run another local poller against this
  washer while the integration is active.
- The profile map is specific to class `0501`; do not apply it to another class.
