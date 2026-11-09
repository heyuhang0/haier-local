# Tools

These scripts are command-line helpers, not part of the Home Assistant runtime.
Install their dependency with `pip install -r requirements.txt`.

## Supported path

- `read_washer.py` — read-only status using the same fixed profile map as the
  integration.
- `fetch_cloud_model.py` — fetch the device's cloud digital model for enum
  curation (requires the saved token and key).
- `generate_component_translations.py` — regenerate entity/enum translations
  from specs.

## Key helper

`china_key.py` is the one-time localKey fetcher. One successful run used the
mainland gateway endpoint `39.107.46.61:56262` with SNI `gw.haier.net`; that
observation does not establish which broker, authentication mode, topic or
request shape is necessary. The helper still searches those variants.

```bash
python3 -I tools/china_key.py \
  --mqtt-probe --mqtt-brokers 39.107.46.61:56262:legacy
```

Constrain the broker list with this command to keep a retry focused; the code
does not claim the remaining search space is verified.
