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

### HACS

1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/heyuhang0/haier-local` with category
   **Integration**.
3. Install **Haier Local** and restart Home Assistant.

### Manual

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
| Local key | yes | 32-hex key, or paste the whole `local_key.json` |
| Device ID | no | UDISCOVERY fills it from the MAC |
| Name | yes | used as the config-entry title |
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

This version is read-only. It exposes primary status values, diagnostic
values and a grouped raw state; see the device page for the entity inventory.
One uSS session is allowed at a time.

## Development

```bash
python -m pip install -r requirements_test.txt
python -m pytest
```

The static tests cover enum behavior, alarm labels, translation coverage, and
the raw-field whitelist. `tests/test_ha_contract.py` additionally exercises the
entity classes against an installed Home Assistant; it is skipped when HA is not
available, so CI does not run it yet.

Entity names and enum labels are generated from `specs.py` and `enum_defs.py`:

```bash
python3 -I tools/generate_component_translations.py
```

## Documentation

- [`docs/protocol.md`](docs/protocol.md) — uSS, localKey, decoding and evidence
- [`docs/maintenance.md`](docs/maintenance.md) — vendor, translation and verification procedures
- [`docs/devices/`](docs/devices/) — device-specific profiles and results
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — vendored/adapted code and
  licenses
