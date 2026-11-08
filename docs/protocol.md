# Protocol notes

How the local connection to the **Casarte CE AB13LWTUWCU1** (Haier class
`0501`) works, and how the implementation was verified.

## Result

- The appliance exposes Haier's uSS protocol on **TCP 56800**.
- UDISCOVERY on **UDP 7083** identifies it without a key.
- The status report is AES-128-CBC encrypted with a per-device `localKey`.
- The class-0501 byte map decodes **93 attributes**. All 92 attributes with a
  non-null value in Haier's cloud shadow matched; the remaining cloud value was null.
- The integration is read-only and does not use the cloud at runtime.

## Discovery

`UDISCOVERY_UWT` is a key-free UDP query to port 7083:

- request: `Haier` + command `0x6915` + a fixed discovery payload;
- reply: `deviceId` (Wi-Fi module MAC), `uPlusId`, local IP/port, SDK and
  firmware versions, and the module's current cloud-connection state.

The class is encoded in `uPlusId` characters 16–20 (`0501` for this washer).
The config flow uses this to reject non-washer appliances and to ask for
confirmation when the exact uPlusId is not the verified model.

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
`tools/china_key.py` pins the certificate by SHA-256
`163f1c6f89c896866bac8c85d1996927a01d49fa78ad6a35fbc58b11be49c4c9`
before sending any MQTT credentials. The key is written with mode `0600` and
verified with one read-only uSS session; it is not part of this repository.

The key remains valid for local use while the appliance is cut off from
Haier's cloud; that is why the WAN block is done only after the HA entities
work.

## Status decoding

The class-0501 map used for this unit is:

```text
201c51890c31c30805010021800239584d000000000000000000000000000140
```

It contains 219 fields and 61 alarm positions. The device's own uPlusId is not
in the bundled model table, so `tools/read_washer.py` tries the bundled
class-0501 maps against a live report and selects the map that places the most
known fields. The selected map produced the same 93 field names as the cloud
digital model; all 92 non-null values matched, including `remainingTimeHH/MM`, `cyclePhase`, `laundryCycle`,
`washTemp`, `spinSpeed`, `currentWater/totalWater`, and
`currentElectricity/totalElectricity`.

Two practical details:

- The class-0501 map (219 fields) is in
  `custom_components/haier_local/data/model_0501.json`.
- The 93 attributes exposed for this unit and their cloud descriptions are in
  `custom_components/haier_local/data/digital_model.json`.

The paired values from the verification run are kept as sanitized fixtures in
`tests/fixtures/`; `tests/test_component.py` compares all 93 offline.

## Integration

`custom_components/haier_local/` uses a `DataUpdateCoordinator` to read the
appliance every 30 seconds (configurable, minimum 15 seconds). The config flow
takes the LAN address and key, discovers the device, checks the `0501` class,
and validates the key with a real status read.

Entity tiers keep the device page readable:

- 20 primary entities;
- 21 enabled diagnostic entities;
- 18 disabled-by-default diagnostic entities, including grouped `Raw state`
  and `Feature flags`.

The full 93-field state remains available in `Raw state` as attributes.
Controls are not implemented; this version is read-only.

## Limitations

- One local session at a time; do not run another poller against the washer.
- The map is verified on the CE AB13LWTUWCU1; another class-0501 model may need
  a different map and asks for confirmation in the config flow.
- The localKey is required before any status read; the helper is the only part
  that contacts Haier's cloud.

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
