# Protocol notes

How the supported class-0501 washer profile is read locally. Device-specific
verification and entity presentation live in
[`devices/casarte-ce-ab13lwtu.md`](devices/casarte-ce-ab13lwtu.md).

## Result

- The appliance exposes Haier's uSS protocol on **TCP 56800**.
- UDISCOVERY on **UDP 7083** identifies it without a key.
- The status report is AES-128-CBC encrypted with a per-device `localKey`.
- A fixed class-0501 map decodes the profile's status report; the device page
  records the observed field and value results.

## Discovery

`UDISCOVERY_UWT` is a key-free UDP query to port 7083:

- request: `Haier` + command `0x6915` + a fixed discovery payload;
- reply: `deviceId` (Wi-Fi module MAC), `uPlusId`, local IP/port, SDK and
  firmware versions, and the module's current cloud-connection state.

The class is encoded in `uPlusId` characters 16–20 (`0501` for this washer).
The config flow uses this to reject non-washer appliances and other uPlusIds;
only the profile's exact uPlusId is accepted when discovery reports one.

## uSS transport

The local protocol is a small session over TCP 56800:

1. `HELLO` / `HELLO_RESP` / `HELLO_DONE`.
2. `HELLO_RESP` carries `status` (BE32) and `localkey_version` (BE32).
3. The appliance permits one local session at a time.

Decrypted reports are EPP frames:

```text
ff ff | length | address (6 bytes) | type | data | checksum
```

The washer status report is requested/identified with status command `6D01`.
The class-0501 decoder in `custom_components/haier_local/vendor/` places the
fields in the report.

## localKey

The `localKey` is a 32-character hex string supplied by Haier's cloud. The
local cipher is:

- AES-128-CBC, IV = zero;
- key = `MD5(localKey-as-ASCII)`.

The mainland app gets the key through the uSDK gateway rather than the ordinary
cloud API. The path used by `tools/china_key.py` is:

- log in with the Haier Smart Home account (`zj.haier.net` OAuth);
- query the account's device list (`uws.haier.net`);
- connect to the uSDK gateway at `39.107.46.61:56262` with TLS SNI
  `gw.haier.net`;
- publish a `devLocalkey` request on the MQTT topics
  `Client/<clientId>/Business/Up` and `Down`;
- read `data.localkey` and `data.localkey_vers` from the reply.

The gateway certificate is self-signed and is also embedded in the mainland
APK. The APK was used only to confirm that identity; it is not redistributed.
The APK certificate is used as a dedicated trust anchor. The gateway's current
leaf certificate chains to it, and `tools/china_key.py` keeps hostname
verification enabled. The public certificates and the independent
`openssl verify` command are in [`tools/certs/`](../tools/certs/). The key is
written with mode `0600` and verified with one read-only uSS session; it is not
part of this repository.

## Status decoding

The class-0501 map used for this unit is:

```text
201c51890c31c30805010021800239584d000000000000000000000000000140
```

It contains 219 fields and 61 alarm positions. The device's own uPlusId is not
in the bundled model table, so this profile pins the map explicitly. Both the
integration and `tools/read_washer.py` load that map from the profile; neither
guesses a map at read time.

The map's field/value verification is recorded in the profile's device page.
No raw report or cloud response is committed; the reader can capture a report
with `--raw-out` for future regression evidence.

Two practical details:

- The 219-field class-0501 map is selected by `profile.map_typeid` from the
  vendored `vendor/haier_local_hrdp/device_models.json.gz`.
- The 93 attributes exposed by `Raw state` are an explicit whitelist in
  `custom_components/haier_local/specs.py`.

## Reconstruction

See [`maintenance.md`](maintenance.md) for updating the vendored catalogue,
and regenerating translations. The map itself is not regenerated: the profile
pins the catalogue id.

One local session is allowed at a time; this is a device constraint, not an
integration setting.

## References

Only the projects that directly inform the implementation are listed here.
License texts and the exact upstream revisions are in
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

- [`enapt/haismart-local`](https://github.com/enapt/haismart-local),
  revision `4af6a1281cba3ab23e13714275089242bb2402a4`, MIT. Its uSS/class-0501
  decoder is vendored as `haier_local_hrdp`; its cloud/localKey helper is
  vendored as `haismart_extractor`.
- [`banto6/haier`](https://github.com/banto6/haier),
  revision `6b06bf5eac237b248362227762ca6253102a0c5d`, Apache-2.0. Reference
  for the mainland OAuth flow, app identities and gateway request shape used
  by `tools/china_key.py`.
- [`Andre0512/hon`](https://github.com/Andre0512/hon),
  revision `70eb6c0111436b5f83fb20ee9dad69fe8407bb31`, MIT. English enum wording
  was adapted from its translations.

The mainland APK used to confirm the gateway certificate is Haier's official
download, `V11.1.0_2026102904`, SHA-256
`83ccddb3840f23a1d7621529e1de76c5eebbf7d559dd0e086f0ed4ea4efa1852`:

<https://download.haier.com/cn/support_buy/support/downloadcenter/app/W020261105340593964843.apk?appdesc=V11.1.0_2026102904>

It is not redistributed in this repository.
