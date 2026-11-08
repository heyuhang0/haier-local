# Gateway certificates

These are public certificates for the uSDK gateway `gw.haier.net`, kept so the
TLS trust decision in `tools/china_key.py` is auditable.

- `gw-haier-apk.pem`: the CA certificate embedded in the mainland Haier Smart
  Home APK. It is the dedicated trust anchor.
- `gw-haier-current.pem`: the leaf certificate presented by
  `39.107.46.61:56262` with SNI `gw.haier.net` on 2026-11-09.

The leaf is **signed by the APK certificate**; this can be checked independently:

```bash
openssl verify -show_chain -verify_hostname gw.haier.net \
  -CAfile tools/certs/gw-haier-apk.pem \
  tools/certs/gw-haier-current.pem
```

The chain is accepted by OpenSSL, but Python's default context enables
`VERIFY_X509_STRICT`, which rejects this legacy CA because its Basic Constraints
extension is not critical and it has no Key Usage extension. `china_key.py`
clears only that strict flag; chain and hostname verification stay enabled. The
leaf has a different subject DN and validity times from the CA; they are not the
same certificate.

If the gateway presents another leaf, first check whether it chains to the APK
certificate:

```bash
openssl s_client -connect 39.107.46.61:56262 -servername gw.haier.net \
  -showcerts </dev/null
```

Do not add a new trust anchor from observation alone.
