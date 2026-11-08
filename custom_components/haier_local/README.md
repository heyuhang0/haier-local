# Haier Local

Home Assistant custom integration for the supported Haier/Casarte washer
profile. It reads uSS over TCP 56800 and uses Haier's cloud only once, through
the setup helper, to fetch the per-device `localKey`.

- Installation and configuration: [project README](../../README.md)
- Supported device, verification and entity inventory:
  [Casarte CE AB13LWTUWCU1](../../docs/devices/casarte-ce-ab13lwtu.md)
- Protocol and reconstruction notes: [protocol](../../docs/protocol.md)

The integration is read-only. One uSS session is allowed at a time.

`vendor/haier_local_hrdp` is vendored from
[`enapt/haismart-local`](https://github.com/enapt/haismart-local), MIT licensed.
This is an unofficial project, not affiliated with Haier or Casarte.
