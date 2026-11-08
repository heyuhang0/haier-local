"""Constants for the Haier/Casarte local washer integration."""
from __future__ import annotations

DOMAIN = "haier_local"
VERSION = "0.1.1"

CONF_HOST = "host"
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 300

PLATFORMS = ["sensor", "binary_sensor"]
