# Haier Local

Local-only Home Assistant integration for the **Casarte CE AB13LWTUWCU1**
(Haier class `0501` washer). It talks directly to the appliance's uSS protocol
on **TCP 56800**, decrypts the status report with the per-device `localKey`, and
decodes it using Haier's published class-0501 byte map.

No cloud is used at runtime. The decoded values were verified field-by-field
against Haier's own cloud shadow for this unit: **93/93 shared attributes
matched**.

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

**Never individual entities** (only in `Raw state` / the CSV):

- Clothing-recognition raw words (`clothesInfo*`, `clothesRecog*`)
- Optional voice module (`voiceModule*`, `voiceStatus`)
- Factory/test flags (`forceDelete`, `testCmdReceiveStatus`)

The primary set is intentionally small; the full 93-field dump stays available
in `Raw state` for debugging without cluttering the device page.

## Languages

English is the source language; `translations/zh-Hans.json` provides Chinese.

- Entity names and enum states use Home Assistant's translation system:
  English HA shows `Phase` / `Standby / not started`; Chinese HA shows
  `洗涤阶段` / `待机/未启动`.
- Enum sensors use `SensorDeviceClass.ENUM` with stable tokens; the display
  label comes from `entity.sensor.<key>.state`.
- Numeric readings show the number with its unit; boolean features are binary
  sensors.
- The `Raw state` entity keeps raw values and adds `label_en`/`label_zh` only
  where useful.

## Install

### HACS custom repository (public GitHub)

HACS installs custom repositories from a GitHub repository URL; a local
filesystem path is not supported.

1. Publish the repository on GitHub.
2. HACS → Integrations → ⋮ → Custom repositories.
3. URL: your repository; category: **Integration**.
4. Install **Haier Local**, restart Home Assistant.
5. HACS updates it when you publish a new tag/release.

`hacs.json` and the `custom_components/haier_local/` layout are already set up.

### Manual copy

From the repository root:

```bash
cp -r custom_components/haier_local /config/custom_components/
# restart Home Assistant
```

### Local git repository (no public host)

Home Assistant itself has no “install from Git URL” button, and HACS custom
repositories need a public GitHub URL (local filesystem paths are not
supported). For a local Git remote, keep a clone on the HA host and copy the
integration after `git pull`:

```bash
cd /config/haier_local_repo
git pull --ff-only
rm -rf /config/custom_components/haier_local
cp -r custom_components/haier_local /config/custom_components/haier_local
ha core restart   # or restart from the UI
```

Or symlink the checkout so `git pull` updates the live component directly:

```bash
rm -rf /config/custom_components/haier_local
ln -s /config/haier_local_repo/custom_components/haier_local \
      /config/custom_components/haier_local
# update later:
cd /config/haier_local_repo && git pull
# then restart Home Assistant
```

Use the **Advanced SSH & Web Terminal** add-on (it includes git), or run the
copy from Samba. Do not clone the whole project directly into
`/config/custom_components/haier_local` — that folder must contain
`manifest.json`, and this repo keeps the integration under
`custom_components/haier_local`.

## Configure

Settings → Devices & services → Add integration → **Haier Local**.

| Field | Required | Notes |
|---|---|---|
| LAN address | yes | e.g. `192.168.1.50` |
| localKey | yes | 32-hex key, or paste the whole `local_key.json` (auto-extracts key/device_id) |
| Device ID | no | UDISCOVERY fills it; manual MAC only if discovery fails |
| Name | no | no default; blank uses the LAN address as the config-entry title |
| Poll interval | no | default 30 s, minimum 15 s |

No device-type selection: UDISCOVERY returns `deviceId` + `uPlusId`, and the
`0501` class identifies a single-drum washer. If the class is not `0501` the
setup is refused; if it is `0501` but not the verified uPlusId, a confirmation
step asks before continuing.

## Getting the localKey

From the repository root:

```bash
python3 -I tools/china_key.py --mqtt-probe
```

It logs in with `.env`, fetches the key from the mainland uSDK gateway, writes
`local_key.json` (0600), and verifies it against the washer.

## Security

- `.env`, `.haier_token` and `local_key.json` contain credentials/key material.
  Keep them at mode `0600` and out of git.
- The localKey decrypts the appliance's LAN traffic. Treat it like a password.
- Home Assistant stores the key in its config entry (`.storage`).

## Limits

- Read-only in this version. Controls (start/pause/cancel/settings) are not
  enabled.
- One uSS session at a time; do not run another local integration against the
  same washer while this one polls.
- The class-0501 map was verified on CE AB13LWTUWCU1; an unverified 0501 model
  may place some fields differently.

## Attribution

`vendor/haier_local_hrdp` is vendored from
[`enapt/haismart-local`](https://github.com/enapt/haismart-local), MIT licensed.
The protocol work and the class-0501 map originate there. This component is an
unofficial community project, not affiliated with Haier or Casarte.
