# Third-party notices

`haier-local` is an unofficial community project. It is not affiliated with,
endorsed by, or supported by Haier, Casarte, or their subsidiaries.

## Vendored packages

### `haier_local_hrdp`

- Upstream: <https://github.com/enapt/haismart-local>
- Revision: `4af6a1281cba3ab23e13714275089242bb2402a4`
- License: MIT
- Location: `custom_components/haier_local/vendor/haier_local_hrdp/`
- Full license: `custom_components/haier_local/vendor/haier_local_hrdp/LICENSE`

Copyright (c) 2026 haismart-local contributors.

The upstream package is named `haismart_hrdp`; it was renamed to
`haier_local_hrdp` only to avoid a Python import conflict. The code and the
bundled device-model data are otherwise upstream work.

### `haismart_extractor`

- Upstream: <https://github.com/enapt/haismart-local>
- Revision: `4af6a1281cba3ab23e13714275089242bb2402a4`
- License: MIT
- Location: `tools/vendor/haismart_extractor/`
- Full license: `tools/vendor/haismart_extractor/LICENSE`

Copyright (c) 2026 haismart-local contributors.

This package is used only by the one-time `tools/china_key.py` helper. It is
not loaded by the Home Assistant integration at runtime.

## Adapted material

### `Andre0512/hon`

- Upstream: <https://github.com/Andre0512/hon>
- Revision: `70eb6c0111436b5f83fb20ee9dad69fe8407bb31`
- License: MIT (see `docs/licenses/MIT-hon.txt`)
- Use: English enum labels and wording in `custom_components/haier_local/enum_defs.py`
  were adapted from the hOn translation tables. No Home Assistant code from
  that project is included.

Copyright (c) 2023 Andre Basche.

### `banto6/haier`

- Upstream: <https://github.com/banto6/haier>
- Revision: `6b06bf5eac237b248362227762ca6253102a0c5d`
- License: Apache License 2.0 (see `docs/licenses/Apache-2.0.txt`)
- Use: the mainland-China OAuth/login flow, app identities, endpoint names and
  the `devLocalkey` MQTT request shape used by the optional `tools/china_key.py`
  helper were derived from this project's public implementation. The helper is
  a standalone implementation informed by that project, not a vendored copy of
  the integration.

Copyright the `banto6/haier` authors.

## Technical notes

See [`docs/protocol.md`](docs/protocol.md) for the protocol summary and the
exact revisions of the projects above.

## Trademarks

Haier, Casarte, and Home Assistant are trademarks of their respective owners.
Use of these names is descriptive only and does not imply endorsement.
