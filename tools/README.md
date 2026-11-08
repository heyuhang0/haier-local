# Tools

These scripts are command-line helpers, not part of the Home Assistant runtime.
Install their dependency with `pip install -r requirements.txt`.

## Supported path

- `read_washer.py` — read-only status using the same fixed profile map as the
  integration.
- `refresh_digital_model.py` — refresh the device-declared cloud descriptions
  (requires the saved token/key).
- `generate_component_translations.py` — regenerate entity/enum translations
  from specs.

## Key helper

`china_key.py` is the one-time localKey fetcher. The path verified on the
supported device is the mainland gateway:

```bash
python3 -I tools/china_key.py \
  --mqtt-probe --mqtt-brokers 39.107.46.61:56262:legacy
```

The helper also contains candidate brokers, topic shapes and request variants
used during discovery. They are experiments, not guaranteed compatibility
paths; use `--mqtt-probe` with the broker above when repeating the verified
procedure. The README command uses the default broker list, whose first entry
is this verified gateway.
