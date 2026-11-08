"""Constants for the Haier/Casarte local washer integration."""
from __future__ import annotations

from pathlib import Path

DOMAIN = "haier_local"
NAME = "Haier Local"
VERSION = "0.1.0"

CONF_HOST = "host"
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_UPIUS_ID = "uplus_id"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 300

# The exact uPlusId this component was built and verified against.  It is also
# announced by UDISCOVERY, so the config flow can warn if a different unit is
# pointed at it.
MODEL_UPIUS_ID = (
    "201c51890c31c308050100218006664300000000000000000000000000000040"
)

DATA_DIR = Path(__file__).resolve().parent / "data"
MODEL_FILE = DATA_DIR / "model_0501.json"
DIGITAL_MODEL_FILE = DATA_DIR / "digital_model.json"

PLATFORMS = ["sensor", "binary_sensor"]

# Idle cycle phases from the digital model's 洗涤阶段 list: standby, finished,
# post-wash drying/tangle finished.  Anything else means the drum is busy.
IDLE_PHASES = frozenset({0, 14, 18, 19})
