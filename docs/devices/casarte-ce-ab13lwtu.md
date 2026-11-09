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

- 39 Sensors, enabled by default: live state, current run settings, care and
  air-wash parameters, consumable levels, and lifetime water/energy totals.
- 13 Diagnostics, enabled by default: cycle counters, fault/problem, remote and
  authorization flags, standby state and the five subsystem diagnostic results.
- 26 disabled entities: current-cycle telemetry, cloud/internal fields,
  optional cartridges and Fabric/Dirt/Stain/advanced care fields, plus
  `Raw state`.
- `Raw state` carries all 132 `6D01` fields from the exact configFile.

`Raw state` is diagnostic and disabled by default. It is the only place for
protocol fields without a dedicated entity; clothing recognition, voice-module,
cartridge detail and factory/test fields stay there.

## Behavior

- Read-only: no start, pause, cancel or settings writes are implemented.
- One uSS session at a time. Do not run another local poller against this
  washer while the integration is active.
- The profile map is specific to class `0501`; do not apply it to another class.
