# Maintenance

Commands for updating dependency snapshots and regenerating derived files. Run
from the repository root:

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
REPO="$PWD"
git clone https://github.com/enapt/haismart-local /tmp/haismart-local
cd /tmp/haismart-local
git checkout <upstream-commit>
rm -rf "$REPO/custom_components/haier_local/vendor/haier_local_hrdp"
cp -r custom_components/haismart/vendor/haismart_hrdp \
  "$REPO/custom_components/haier_local/vendor/haier_local_hrdp"
rm -rf "$REPO/tools/vendor/haismart_extractor"
cp -r custom_components/haismart/vendor/haismart_extractor \
  "$REPO/tools/vendor/haismart_extractor"
cp LICENSE "$REPO/custom_components/haier_local/vendor/haier_local_hrdp/LICENSE"
cp LICENSE "$REPO/tools/vendor/haismart_extractor/LICENSE"
cd "$REPO"
```

The profile's `map_typeid` is loaded directly from
`vendor/haier_local_hrdp/device_models.json.gz`; there is no separate copy to
regenerate. After updating the snapshot, run:

```bash
python -m pytest
python3 -I tools/read_washer.py --help
```

Update the upstream revision in `THIRD_PARTY_NOTICES.md`.

## Regenerate translations

`tools/generate_component_translations.py` expands the entity and enum tables in
`specs.py` and `enum_defs.py`. It preserves the existing `config` and `options`
sections in the translation files:

```bash
python3 -I tools/generate_component_translations.py
```

Run the tests afterward; they check that the generated entity keys and states
cover the specs.

## Validate

```bash
python -m pytest
python3 -I tools/read_washer.py --host <washer-ip>
```

The reader and integration load the same fixed profile and call the same decode function. If the reader
succeeds but Home Assistant does not, check the config entry's host/key/device
id and the HA logs rather than changing the map.

To capture a report for a future decoder test:

```bash
python3 -I tools/read_washer.py --host <washer-ip> --raw-out /tmp/status.json
```

The JSON contains every decrypted blob from the burst, but not the localKey. Review them
before committing any fixture.
