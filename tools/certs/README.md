# Gateway certificates

These are public self-signed certificates for `gw.haier.net`, kept so the
pinned fingerprints in `tools/china_key.py` can be audited.

- `gw-haier-apk.pem`: certificate embedded in the mainland Haier Smart Home
  APK (SHA-256 `163f1c6f...`).
- `gw-haier-current.pem`: certificate presented by
  `39.107.46.61:56262` with SNI `gw.haier.net` on 2026-11-09 (SHA-256
  `d5cabcab...`). Both have the same subject/issuer and dates but different
  keys.

The second certificate is trusted because it is the certificate the known Haier
gateway presented on the verified connection, not because it chains to a public
CA. If the gateway changes again, inspect the new certificate with:

```bash
openssl s_client -connect 39.107.46.61:56262 -servername gw.haier.net \
  -showcerts </dev/null \
  | openssl x509 -noout -subject -issuer -fingerprint -sha256
```

Do not add a fingerprint without recording where it came from.
