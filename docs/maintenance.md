# Maintenance and reconstruction

Commands for changing the vendored code, regenerating the profile data, and
checking a second appliance. Run from the repository root with the CLI
dependencies installed:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements_test.txt
```

## Update the vendored decoder

The vendored packages are snapshots of
[`enapt/haismart-local`](https://github.com/enapt/haismart-local):

- `custom_components/haier_local/vendor/haier_local_hrdp/` is upstream
  `custom_components/haismart/vendor/haismart_hrdp/` (directory renamed);
- `tools/vendor/haismart_extractor/` is upstream
  `custom_components/haismart/vendor/haismart_extractor/`.

```bash
git clone https://github.com/enapt/haismart-local
cd haismart-local
git checkout <upstream-commit>
cp -r custom_components/haismart/vendor/haismart_hrdp \
  ../haier-local/custom_components/haier_local/vendor/haier_local_hrdp
cp -r custom_components/haismart/vendor/haismart_extractor \
  ../haier-local/tools/vendor/haismart_extractor
cp LICENSE ../haier-local/custom_components/haier_local/vendor/haier_local_hrdp/LICENSE
cp LICENSE ../haier-local/tools/vendor/haismart_extractor/LICENSE
```

Update the upstream revision in `THIRD_PARTY_NOTICES.md`, then run:

```bash
python -m pytest
python3 -I tools/refresh_model.py --check
```

## Regenerate the class-0501 map

The profile pins both the device's uPlusId and the catalogue map. Edit
`custom_components/haier_local/profile.py` first if either changes, then:

```bash
python3 -I tools/refresh_model.py
python3 -I tools/refresh_model.py --check
```

This rebuilds `custom_components/haier_local/data/model_0501.json` from the
vendored `device_models.json.gz`. The output keeps `source_typeid` so the
selected map is auditable.

## Regenerate translations

`tools/generate_component_translations.py` writes `strings.json`,
`translations/en.json` and `translations/zh-Hans.json` from `specs.py` and
`enum_defs.py`:

```bash
python3 -I tools/generate_component_translations.py
```

## Refresh cloud descriptions

`tools/refresh_digital_model.py` keeps only the attributes present in the local
map and writes `custom_components/haier_local/data/digital_model.json`. It
requires the access token and key produced by the one-time setup:

```bash
python3 -I tools/china_key.py --mqtt-probe
python3 -I tools/refresh_digital_model.py
```

The second command contacts Haier's cloud; it is not part of normal local
operation.

## Check another appliance

Use the read-only probe first:

```bash
python3 -I tools/probe_haier.py <ip>
```

It reports the uPlusId, class, open ports and uSS localKey version. Do not add a
profile from UDISCOVERY alone: obtain the class-0501 map, decode a report, and
verify its values against the cloud shadow before changing
`custom_components/haier_local/profile.py`. The config flow accepts an unknown
class-0501 uPlusId only after explicit confirmation, but that does not prove the
field map is correct.

## Validate

```bash
python -m pytest
python3 -I tools/read_washer.py --host <washer-ip>
```

The reader and the integration intentionally load the same fixed profile map.
If the reader succeeds but Home Assistant does not, check the config entry's
host/key/device id and the HA logs rather than changing the map.

To preserve a report for a future decoder regression test, ask the reader to
save the decrypted bytes:

```bash
python3 -I tools/read_washer.py --host <washer-ip> --raw-out /tmp/status.bin
```

Review the bytes before committing a sanitized fixture; they contain device
state even though they no longer contain the localKey.
