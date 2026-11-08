"""Config and options flow for the local washer."""
from __future__ import annotations

import json
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from . import decoder
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .profile import CASARTE_CE_AB13LWTUWCU1

_LOGGER = logging.getLogger(__name__)


def _clean_device_id(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum()).upper()


def _parse_key_input(value: str) -> tuple[str, str]:
    """Accept a raw 32-hex key or a pasted local_key.json document."""
    text = value.strip()
    if not text.startswith("{"):
        return text, ""
    doc = json.loads(text)
    key = str(doc.get("local_key") or doc.get("localkey") or "")
    device = str(doc.get("device_id") or doc.get("deviceId") or "")
    return key, device


def _clean_key(value: str) -> str:
    key = value.strip()
    if len(key) != 32:
        raise ValueError("localKey must be 32 hex characters")
    bytes.fromhex(key)
    return key


def _user_schema(defaults: dict | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=d.get(CONF_HOST, vol.UNDEFINED)): str,
            vol.Required(CONF_LOCAL_KEY): str,
            vol.Optional(CONF_DEVICE_ID, default=d.get(CONF_DEVICE_ID, "")): str,
            vol.Optional(CONF_NAME): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=d.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)),
        }
    )


class HaierLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._pending: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            device_id = _clean_device_id(user_input.get(CONF_DEVICE_ID, ""))
            uplus_id = ""

            try:
                key_text, key_device = _parse_key_input(user_input[CONF_LOCAL_KEY])
                device_id = device_id or _clean_device_id(key_device)
            except (ValueError, json.JSONDecodeError):
                errors["base"] = "invalid_key"
                key_text = ""

            if not errors:
                try:
                    local_key = _clean_key(key_text)
                except ValueError:
                    errors["base"] = "invalid_key"

            if not errors:
                try:
                    info = await self.hass.async_add_executor_job(
                        decoder.discover_device, host
                    )
                except Exception:  # noqa: BLE001 - discovery is best-effort
                    info = None
                if info is not None:
                    uplus_id = info.uplus_id or ""
                    device_id = device_id or info.device_id

            if not device_id:
                errors.setdefault("base", "device_id_required")
            if uplus_id and len(uplus_id) >= 20 and uplus_id[16:20] != "0501":
                errors["base"] = "unsupported_class"
            elif (uplus_id
                  and uplus_id.upper() != CASARTE_CE_AB13LWTUWCU1.uplus_id.upper()):
                errors["base"] = "unsupported_model"

            if not errors:
                try:
                    await self.hass.async_add_executor_job(
                        decoder.read_state, host, device_id, local_key
                    )
                except Exception as err:  # noqa: BLE001
                    _LOGGER.warning("washer validation failed: %s", err)
                    errors["base"] = "cannot_connect"

            if not errors:
                self._pending = {
                    CONF_HOST: host,
                    CONF_DEVICE_ID: device_id,
                    CONF_LOCAL_KEY: local_key,
                    CONF_NAME: (user_input.get(CONF_NAME) or "").strip(),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                }
                return await self._async_create_entry()

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def _async_create_entry(self) -> config_entries.ConfigFlowResult:
        pending = self._pending
        await self.async_set_unique_id(pending[CONF_DEVICE_ID])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=pending[CONF_NAME] or pending[CONF_HOST],
            data={
                CONF_HOST: pending[CONF_HOST],
                CONF_DEVICE_ID: pending[CONF_DEVICE_ID],
                CONF_LOCAL_KEY: pending[CONF_LOCAL_KEY],
                CONF_SCAN_INTERVAL: pending[CONF_SCAN_INTERVAL],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return HaierLocalOptionsFlow()


class HaierLocalOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input: dict | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                key_text, _device = _parse_key_input(user_input[CONF_LOCAL_KEY])
                local_key = _clean_key(key_text)
            except (ValueError, json.JSONDecodeError):
                errors["base"] = "invalid_key"
            if not errors:
                try:
                    await self.hass.async_add_executor_job(
                        decoder.read_state,
                        host,
                        self.config_entry.data[CONF_DEVICE_ID],
                        local_key,
                    )
                except Exception:  # noqa: BLE001
                    errors["base"] = "cannot_connect"
            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_HOST: host,
                        CONF_LOCAL_KEY: local_key,
                        CONF_SCAN_INTERVAL: int(
                            user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                        ),
                    },
                )

        data = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=data[CONF_HOST]): str,
                    vol.Required(CONF_LOCAL_KEY, default=data[CONF_LOCAL_KEY]): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                }
            ),
            errors=errors,
        )
