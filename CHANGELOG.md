# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions use
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-08

### Added

- Local uSS client on TCP 56800 for the Casarte CE AB13LWTUWCU1 (Haier class
  `0501`), using the per-device `localKey`.
- One-time mainland-China localKey helper (`tools/china_key.py`) that logs in,
  requests `devLocalkey` from the uSDK gateway, and verifies the key locally.
- Standalone status reader and class-0501 decoder (`tools/read_washer.py`).
- Home Assistant custom integration `haier_local` with config flow, options
  flow, `DataUpdateCoordinator`, 20 primary entities, 21 enabled diagnostic
  entities, 18 disabled-by-default diagnostic entities, one grouped
  `Raw state` sensor and one grouped `Feature flags` sensor.
- English entity/state translations and a Simplified Chinese (`zh-Hans`)
  translation set.
- HACS metadata, local-git update helper, tests, and protocol/reference docs.

### Security

- Secrets (`.env`, `.haier_token`, `local_key.json`) are kept out of Git.
- Runtime is fully local; the cloud is only contacted by the one-time localKey
  helper.

### Known limitations

- Read-only: control commands are not implemented.
- One uSS session at a time; do not poll the same washer from two clients.
- Field layout is verified on the CE AB13LWTUWCU1; other class-0501 models can
  differ and require confirmation in the config flow.
