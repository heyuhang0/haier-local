# Haier Local

A local Home Assistant integration for Haier/Casarte appliances that speak the
uSS protocol on TCP 56800. It reads status directly from the appliance and uses
the cloud only once, to obtain the per-device `localKey`.

## Supported devices

| Device | Class | Status | Details |
|---|---|---|---|
| Casarte CE AB13LWTUWCU1 | `0501` | verified | [`docs/devices/casarte-ce-ab13lwtu.md`](docs/devices/casarte-ce-ab13lwtu.md) |

When UDISCOVERY reports a class other than `0501`, setup is refused. A
class-0501 appliance whose uPlusId is not the verified profile is also refused.

## Install

Copy the integration into Home Assistant:

```bash
cp -r custom_components/haier_local /config/custom_components/
```

Restart Home Assistant, then add **Haier Local** from
**Settings → Devices & services → Add integration**.

## Configure

| Field | Required | Notes |
|---|---|---|
| LAN address | yes | e.g. `192.168.1.50` |
| localKey | yes | 32-hex key, or paste the whole `local_key.json` |
| Device ID | no | UDISCOVERY fills it from the MAC |
| Name | no | no default; blank uses the LAN address as the entry title |
| Poll interval | no | default 30 s, minimum 15 s |

The config flow performs UDISCOVERY, identifies the device and validates the
key with one real status read.

## Obtaining the localKey

The helper needs Python 3.11+ and `cryptography`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
$EDITOR .env          # account and washer IP; device ID may be left blank
chmod 600 .env
python3 -I tools/china_key.py --mqtt-probe
```

The helper logs in, finds the device (using UDISCOVERY if `HAIER_DEVICE_ID` is
blank), fetches `devLocalkey` from the uSDK gateway, writes `local_key.json`
with mode `0600`, and verifies it with one read-only uSS session. A verification
failure returns exit status `5` after saving the key. `.env`,
`.haier_token`, `local_key.json` and `washer_status.json` are gitignored.

For a local read without Home Assistant:

```bash
python3 -I tools/read_washer.py --host <washer-ip>
```

It writes the decoded state to `washer_status.json` (gitignored). Both the
reader and the integration use the same fixed device profile.

## Capabilities

This version is read-only. It exposes the primary controls/status, diagnostic
values and a grouped raw state; see the device page for the entity inventory.
One uSS session is allowed at a time.

## Development

```bash
python -m pip install -r requirements_test.txt
python -m pytest
```

The tests cover enum behavior, alarm labels, translation coverage, the
historical cloud comparison, and the device profile files. They do not boot
Home Assistant; runtime setup/options flows are not covered by CI yet.

Entity names and enum labels are generated from `specs.py` and `enum_defs.py`:

```bash
python3 -I tools/generate_component_translations.py
```

## Documentation

- [`docs/protocol.md`](docs/protocol.md) — uSS, localKey, decoding and evidence
- [`docs/maintenance.md`](docs/maintenance.md) — vendor, model and verification procedures
- [`docs/devices/`](docs/devices/) — device-specific profiles and results
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — vendored/adapted code and
  licenses
