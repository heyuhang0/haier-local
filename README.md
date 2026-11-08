# Casarte CE AB13LWTUWCU1 — local Home Assistant

Fully local status reading for the China-market **Casarte CE AB13LWTUWCU1**
(Haier class `0501` washer), with **no cloud at runtime**.

The integration speaks the appliance's uSS protocol on TCP 56800, decrypts the
status report with the per-device `localKey`, and decodes it with Haier's
class-0501 byte map. The cloud is contacted only once, by the helper that
obtains the key.

## Status

- ✅ Local uSS protocol on TCP `56800` discovered and verified
- ✅ `localKey` obtained from the mainland uSDK gateway and verified locally
- ✅ Class-0501 decode covers **93 shared attributes**; all 92 non-null cloud values matched
- ✅ Standalone reader works (`tools/read_washer.py`)
- ✅ HA custom component: `custom_components/haier_local/`
- ✅ English source + `zh-Hans` translations
- ✅ Entity tiers: 20 primary / 21 diagnostic / 18 disabled by default
  (including the grouped `Raw state` and `Feature flags` diagnostic entities)
- ✅ HACS metadata
- ⏳ Control (start/pause/cancel/settings) not enabled yet

Protocol notes, verification details and upstream revisions:
[`docs/protocol.md`](docs/protocol.md).

## Requirements

- Home Assistant **2024.6** or newer (the manifest/HACS floor; CI currently runs
  static tests only, not a Home Assistant runtime)
- The washer reachable on the LAN (TCP 56800); this project was tested on a
  class-0501 CE AB13LWTUWCU1
- A valid per-device `localKey` (one-time cloud fetch, see below)
- Python 3.11+ and `cryptography` only for the command-line tools; the
  integration itself runs in Home Assistant (which already ships it)

## 1. One-time localKey fetch

The key is issued by Haier's cloud and is needed for every local read.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt

cp .env.example .env
$EDITOR .env          # Haier Smart Home account + washer IP
chmod 600 .env
python3 -I tools/china_key.py --mqtt-probe
```

The helper logs in, asks the mainland uSDK gateway for `devLocalkey`, writes
`local_key.json` with mode `0600`, and verifies the key with one read-only
session against the washer. It also accepts `--phone/--password`, a refresh
token, or a credentials JSON file; see `python3 -I tools/china_key.py --help`.

`local_key.json` is what the Home Assistant config flow needs. The helper does
not change the washer's state.

## 2. Local read test (no Home Assistant)

```bash
python3 -I tools/read_washer.py --host <washer-ip>
```

This prints the decoded 93-field state and writes `washer_status.json`
(gitignored). A wrong key or a second concurrent uSS session fails with a
decryption error; the washer accepts one local session at a time.

## 3. Install the integration

### HACS (public GitHub repository)

HACS custom repositories are installed from a GitHub repository URL; a local
filesystem path is not supported.

1. Publish this repository on GitHub.
2. HACS → Integrations → ⋮ → Custom repositories.
3. Add the repository URL, category **Integration**.
4. Install **Haier Local**, then restart Home Assistant.
5. HACS updates it when you publish a new tag/release.

`hacs.json` and the `custom_components/haier_local/` layout are ready.

### Local git remote (no public host)

Keep a clone on the HA host and copy the component after each update:

```bash
git clone <your-local-remote> /config/haier_local_repo

# after each update:
cd /config/haier_local_repo
git pull --ff-only
rm -rf /config/custom_components/haier_local
cp -r custom_components/haier_local /config/custom_components/haier_local
# restart Home Assistant
```

Or symlink once, so `git pull` updates the live component directly:

```bash
rm -rf /config/custom_components/haier_local
ln -s /config/haier_local_repo/custom_components/haier_local \
      /config/custom_components/haier_local
# update later: cd /config/haier_local_repo && git pull
# then restart Home Assistant
```

### Manual copy

```bash
cp -r custom_components/haier_local /config/custom_components/
# restart Home Assistant
```

Do not clone the repository directly into
`/config/custom_components/haier_local`: that directory must contain
`manifest.json`, and the integration lives one level down in this repository.

## 4. Configure Home Assistant

**Settings → Devices & services → Add integration → Haier Local**

| Field | Required | Notes |
|---|---|---|
| LAN address | yes | e.g. `192.168.1.50` |
| localKey | yes | 32-hex key, or paste the whole `local_key.json` (the key and device id are extracted) |
| Device ID | no | UDISCOVERY fills it from the MAC; enter it manually only if discovery fails |
| Name | no | no default; blank uses the LAN address as the config-entry title |
| Poll interval | no | default 30 s, minimum 15 s |

There is no device-type selector. UDISCOVERY returns `deviceId` and `uPlusId`;
the integration requires class `0501`. A class-0501 appliance whose uPlusId is
not the verified model asks for explicit confirmation before setup.

## Entities

The primary set is deliberately small; detailed values are diagnostic and raw
data stays grouped.

- **20 primary entities**: remaining time, phase, program, running mode,
  message, wash temperature, spin speed, remaining main wash/rinse, current and
  total water/energy; binary power, running, door, door lock, remote control,
  child lock and problem.
- **21 enabled diagnostic entities**: cycles, standby time, program-started,
  detergent/softener/booster levels, dry mode/status/time/level, detergent
  type/ratio, dirt/stain/fabric, and subsystem problem sensors.
- **18 disabled-by-default diagnostic entities**: doses, detergent B, dry
  type/flag/cleaning reminder, air wash, cloud program fields, weights, wash
  speed, and the grouped `Feature flags` and `Raw state` entities.
- **`Raw state`** exposes all 93 decoded values as attributes for debugging;
  **`Feature flags`** exposes the 22 optional flags. Both are disabled by
  default.

## Security

These files contain secrets and are mode `0600` / gitignored:

- `.env` — Haier account credentials
- `.haier_token` — cached access token
- `local_key.json` — the washer's LAN encryption key

Do not commit or share them. Home Assistant stores the key in its own config
entry (`.storage`), so protect the HA configuration directory as usual.

The localKey decrypts the appliance's LAN traffic. Treat it like a password.
The integration is read-only in this version.

## Blocking WAN

Do this only after the Home Assistant entities have updated reliably for a
while. Keep the washer's LAN access to TCP `56800` open; block its outbound WAN
traffic with a firewall rule or address-list on your router. The localKey does
not rotate while the appliance is cut off from Haier's cloud. The Haier app will
show the washer offline; local polling continues.

Before blocking, confirm that:

1. `local_key.json` is saved and the HA config entry works;
2. the washer has a DHCP reservation (or static lease), so its address does not
   change;
3. you can still reach TCP 56800 from the HA host after the rule is applied.

## Troubleshooting

- **`could not decrypt` / `invalid key`**: the key and device ID must belong to
  this washer. Re-run the key helper; do not use a key from another appliance.
- **No status after a while**: check the DHCP lease. If the address changed,
  update the integration options.
- **Second client fails**: the washer permits one uSS session at a time. Disable
  other local pollers before using this integration.
- **Unsupported class**: this integration only handles class `0501`; do not
  force another class.
- HA logs: **Settings → System → Logs**, filter for `haier_local`.

## Development

Layout:

```
custom_components/haier_local/   Home Assistant integration (domain: haier_local)
  vendor/haier_local_hrdp/        vendored MIT decoder from enapt/haismart-local
tools/                            one-time key fetch, optional probe, reader
tests/                            static spec/translation tests (no HA needed)
docs/                             protocol notes, licenses
```

Run the tests:

```bash
python -m pip install -r requirements_test.txt
python -m pytest
```

Translations are kept in `strings.json` and `translations/`; the tests check
that every entity and enum state has an English and Chinese entry.

## Tools

| File | Purpose |
|---|---|
| `tools/china_key.py` | one-time mainland token → uSDK gateway → localKey |
| `tools/read_washer.py` | standalone local status reader/decoder |
| `tools/probe_haier.py` | optional read-only UDISCOVERY + port + uSS HELLO preflight |

## Documentation and provenance

- [`docs/protocol.md`](docs/protocol.md) — protocol, localKey path, verification,
  limitations and upstream revisions
- [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — attribution and licenses
- [`CHANGELOG.md`](CHANGELOG.md)

This is an unofficial community project, not affiliated with Haier or Casarte.
