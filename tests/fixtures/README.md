# Decoder verification fixtures

These are sanitized, paired values from the verification run on 2026-11-08:

- device: Casarte CE AB13LWTUWCU1, Haier class `0501`;
- firmware: `e_4.6.38 / R_6.0.01`;
- `local_status_93.json`: attributes decoded from one local uSS `6D01` report;
- `cloud_values_93.json`: the same 93 attributes in Haier's cloud digital
  model at the same time.

No credentials, localKey, MAC address, LAN address or other identifiers are
included. `tests/test_component.py` compares every pair after normalizing
booleans and decimal formatting, and fails if the 93 field names or the 92
non-null values diverge.
