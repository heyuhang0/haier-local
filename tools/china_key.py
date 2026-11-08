#!/usr/bin/env python3
"""Fetch a mainland-China Haier localKey, then verify it against the washer locally.

The uSDK business gateway is the same mechanism the official app uses: an MQTT
request ``devLocalkey`` carrying the account accessToken and the device id.  The
SE-Asia host/port is documented by haismart-local; the mainland host is not, so
this tries a short candidate list.

Credentials (choose one):
  * --creds-file JSON: {"refresh_token": "...", "client_id": "...", "app_source": "wxapp"}
    (or app_source "app"), or
  * --phone/--password (prompts with getpass; app-source path), or
  * HAIER_REFRESH_TOKEN + HAIER_CLIENT_ID + HAIER_APP_SOURCE env vars.

Nothing secret is printed.  The key is written to --key-out with mode 0600 and
then verified by one read-only uSS session against the washer.

Usage:
    python3 -I china_key.py --creds-file ~/.haier_creds.json
    python3 -I china_key.py --phone 138... --device-id <washer-mac> \
        --washer-ip <washer-ip>
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import random
import secrets
import socket
import ssl
import stat
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from types import SimpleNamespace

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(TOOLS / "vendor"))
sys.path.insert(0, str(PROJECT / "custom_components/haier_local/vendor"))

from haismart_extractor.gateway import (  # noqa: E402
    GatewayConnectionError,
    GatewayCreds,
    GatewayError,
    _TlsMqttConnection,
    _encode_len,
    _mqtt_field,
    derive_client_id,
    derive_gateway_auth,
    get_localkey_via_gateway,
    localkey_request_payload,
    parse_localkey_response,
)
from haier_local_hrdp.udiscovery import query as udiscovery_query  # noqa: E402
from haier_local_hrdp.uss import read_status  # noqa: E402

APP_SOURCES = {
    # (appId, appKey) -- the same shipped app identities banto6/haier uses.
    "wxapp": ("MB-SHEZJAPPWXXCX-0000", "79ce99cc7f9804663939676031b8a427"),
    "app": ("MB-UZHSH-0001", "5dfca8714eb26e3a776e58a8273c8752"),
}
REFRESH_URL = "https://zj.haier.net/api-gw/oauthserver/account/v1/refreshToken"
LOGIN_URL = "https://zj.haier.net/api-gw/oauthserver/account/v1/login"
DEVICES_URL = "https://uws.haier.net/uds/v1/protected/deviceinfos"
PACKAGE = "com.haier.uhome.uplus"
# App-side endpoint that returns the MQTT broker connection info (from the APK).
MQTT_INFO_URLS = [
    "http://iotplatform.haier.net:8080/iot/rest/user/mqtt/getMqttUserInfo",
    "https://iotplatform.haier.net/iot/rest/user/mqtt/getMqttUserInfo",
    "https://uws.haier.net/iot/rest/user/mqtt/getMqttUserInfo",
]

DEFAULT_HOSTS = [
    "gw.haier.net:58702",
    "gw.haieriot.net:58702",
    "gw-sgp.haieriot.net:58702",
    "gw.haier.net:56802",
    "gw.haier.net:56803",
    "gw.haieriot.net:56802",
    "gw.haieriot.net:56803",
    "gw.haier.net:56042",
    "gw.haieriot.net:56042",
]

# SHA-256 fingerprints of the DER certificates known for gw.haier.net
# (self-signed, CN=gw.haier.net, valid 2014..2044).  The gateway is reached by
# IP and has no publicly trusted chain, so pin a known certificate before
# sending the account token over MQTT.
GATEWAY_CERT_SHA256S = {
    # Embedded in the mainland app / observed originally.
    "163f1c6f89c896866bac8c85d1996927a01d49fa78ad6a35fbc58b11be49c4c9",
    # Presented by 39.107.46.61:56262 on 2026-11-09.
    "d5cabcab7d6429aaecfc43cc1fa1beb6bec8140761e334a39eec149491829e76",
}


def _sign(app_id: str, app_key: str, timestamp: str, body: str, url: str) -> str:
    path = urllib.parse.urlparse(url).path
    content = (
        path
        + body.replace(" ", "").replace("\t", "").replace("\r", "").replace("\n", "")
        + app_id
        + app_key
        + timestamp
    )
    return hashlib.sha256(content.encode()).hexdigest()


def _headers(app_id: str, app_key: str, client_id: str, token: str,
             body: str, url: str) -> dict[str, str]:
    timestamp = str(int(time.time() * 1000))
    sequence = time.strftime("%Y%m%d%H%M%S") + str(random.randint(100000, 999999))
    return {
        "accessToken": token,
        "appId": app_id,
        "appKey": app_key,
        "clientId": client_id,
        "sequenceId": sequence,
        "sign": _sign(app_id, app_key, timestamp, body, url),
        "timestamp": timestamp,
        "timezone": "+8",
        "language": "zh-CN",
        "Accept-Encoding": "identity",
    }


def _http_json(url: str, *, method: str = "GET", payload: dict | None = None,
               headers: dict | None = None, timeout: float = 25.0) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw)


def _assert_ok(content: dict, what: str) -> dict:
    code = content.get("retCode")
    if code is not None and str(code) != "00000":
        raise SystemExit(f"{what} failed: retCode={code} retInfo={content.get('retInfo')}")
    return content


def refresh_access_token(refresh_token: str, client_id: str,
                         app_source: str) -> tuple[str, str, str]:
    app_id, app_key = APP_SOURCES[app_source]
    body = json.dumps({"refreshToken": refresh_token})
    headers = _headers(app_id, app_key, client_id, "", body, REFRESH_URL)
    content = _assert_ok(
        _http_json(REFRESH_URL, method="POST", payload={"refreshToken": refresh_token},
                   headers=headers),
        "refreshToken",
    )
    info = content["data"]["tokenInfo"]
    return info["accountToken"], info.get("refreshToken", refresh_token), client_id


def phone_login(phone: str, password: str) -> tuple[str, str, str]:
    app_id, app_key = APP_SOURCES["app"]
    payload = {"username": phone, "password": password}
    body = json.dumps(payload)
    headers = _headers(app_id, app_key, phone, "", body, LOGIN_URL)
    content = _assert_ok(
        _http_json(LOGIN_URL, method="POST", payload=payload, headers=headers),
        "phone login",
    )
    info = content["data"]["tokenInfo"]
    return info["accountToken"], info.get("refreshToken", ""), phone


def get_devices(access_token: str, client_id: str, app_source: str) -> list[dict]:
    app_id, app_key = APP_SOURCES[app_source]
    headers = _headers(app_id, app_key, client_id, access_token, "", DEVICES_URL)
    content = _assert_ok(_http_json(DEVICES_URL, headers=headers), "device list")
    return content.get("deviceinfos") or []




_SECRET_WORDS = ("password", "passwd", "pwd", "secret", "token", "accesstoken",
                 "refreshtoken", "key")


def _print_json_summary(obj: object, prefix: str = "", depth: int = 0) -> None:
    if depth > 3:
        return
    if isinstance(obj, dict):
        for key, value in list(obj.items())[:40]:
            name = f"{prefix}.{key}" if prefix else str(key)
            lower = str(key).lower()
            if isinstance(value, (dict, list)):
                _print_json_summary(value, name, depth + 1)
            elif any(word in lower for word in _SECRET_WORDS):
                print(f"    {name} = <redacted len={len(str(value))}>")
            elif lower in ("clientid", "username", "user"):
                text = str(value)
                print(f"    {name} = {text[:4]}...<masked>")
            else:
                print(f"    {name} = {value}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj[:5]):
            _print_json_summary(value, f"{prefix}[{index}]", depth + 1)


def get_mqtt_info(access_token: str, client_id: str, app_source: str) -> list[dict]:
    """Ask the app-facing endpoint for MQTT broker connection info."""
    app_id, app_key = APP_SOURCES[app_source]
    results: list[dict] = []
    for url in MQTT_INFO_URLS:
        for method in ("GET", "POST"):
            body = "" if method == "GET" else "{}"
            headers = _headers(app_id, app_key, client_id, access_token, body, url)
            try:
                content = _http_json(
                    url, method=method,
                    payload=None if method == "GET" else {},
                    headers=headers,
                )
            except urllib.error.HTTPError as exc:
                detail = exc.read()[:200].decode("utf-8", "replace")
                print(f"  {method} {url}: HTTP {exc.code} {detail}")
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"  {method} {url}: {type(exc).__name__}: {exc}")
                continue
            print(f"  {method} {url}: OK")
            _print_json_summary(content)
            results.append(content)
            break
    return results


class PlainMqttConnection(_TlsMqttConnection):
    """MQTT 3.1.1 framing identical to the TLS gateway, without TLS (port 8080/1883)."""

    def __init__(self, creds) -> None:
        self.ss = socket.create_connection((creds.host, creds.port), timeout=8)
        self._pid = 0
        self._buf = b""
        self._subacked: set[int] = set()
        self._publishes: list[tuple[str, bytes]] = []
        self._closed = False
        vh = b"\x00\x04MQTT\x04" + bytes([0x02 | 0x80 | 0x40]) + struct.pack(">H", 60)
        body = (vh + _mqtt_field(creds.client_id) + _mqtt_field(creds.username)
                + _mqtt_field(creds.password))
        self.ss.sendall(b"\x10" + _encode_len(len(body)) + body)
        ack = b""
        while len(ack) < 4:
            chunk = self.ss.recv(4 - len(ack))
            if not chunk:
                raise GatewayConnectionError("broker closed before CONNACK")
            ack += chunk
        if ack[0] != 0x20:
            raise GatewayError(f"expected CONNACK, got packet type {ack[0] >> 4}")
        if ack[3] != 0:
            raise GatewayError(f"CONNACK rc={ack[3]}")


class LegacyTlsMqttConnection(_TlsMqttConnection):
    """MQTT/TLS to the uSDK ``gw.haier.net`` gateway (self-signed 2014 cert).

    The APK pins this exact certificate; it is C=CN, O=haier ubic, CN=gw.haier.net,
    valid 2014-2044. Modern trust stores reject it, so the chain is not trusted;
    instead the exact DER certificate is pinned by SHA-256 before any MQTT
    credentials are sent.  The host is fixed to the app's gateway IP and SNI.
    """

    def __init__(self, creds, sni: str = "gw.haier.net") -> None:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=0")
        except ssl.SSLError:
            pass
        raw = socket.create_connection((creds.host, creds.port), timeout=8)
        self.ss = ctx.wrap_socket(raw, server_hostname=sni)
        server_cert = self.ss.getpeercert(binary_form=True)
        actual = hashlib.sha256(server_cert or b"").hexdigest()
        if actual not in GATEWAY_CERT_SHA256S:
            self.ss.close()
            raise GatewayConnectionError(
                "gateway certificate pin mismatch: "
                f"expected one of {sorted(GATEWAY_CERT_SHA256S)}, got {actual}"
            )
        self._pid = 0
        self._buf = b""
        self._subacked: set[int] = set()
        self._publishes: list[tuple[str, bytes]] = []
        self._closed = False
        vh = b"\x00\x04MQTT\x04" + bytes([0x02 | 0x80 | 0x40]) + struct.pack(">H", 60)
        body = (vh + _mqtt_field(creds.client_id) + _mqtt_field(creds.username)
                + _mqtt_field(creds.password))
        self.ss.sendall(b"\x10" + _encode_len(len(body)) + body)
        ack = b""
        while len(ack) < 4:
            chunk = self.ss.recv(4 - len(ack))
            if not chunk:
                raise GatewayConnectionError("gateway closed before CONNACK")
            ack += chunk
        if ack[0] != 0x20:
            raise GatewayError(f"expected CONNACK, got packet type {ack[0] >> 4}")
        if ack[3] != 0:
            raise GatewayError(f"CONNACK rc={ack[3]}")


def _mqtt_request_variants(device_id: str, access_token: str, sn: str):
    """The documented devLocalkey body, plus two best-effort uSDK shapes."""
    yield "devLocalkey", localkey_request_payload(device_id, access_token, sn=sn)
    inner = {"sn": sn, "devs": [device_id], "force": 1, "setBindTimeWindow": 0}
    data = base64.b64encode(json.dumps(inner, separators=(",", ":")).encode()).decode()
    yield "getLocalkey", json.dumps(
        {"type": "getLocalkey", "data": data, "tokens": [access_token]},
        separators=(",", ":"),
    )
    yield "getAllDevLocalKey", json.dumps(
        {"type": "getAllDevLocalKey", "devs": [device_id], "tokens": [access_token]},
        separators=(",", ":"),
    )


def _as_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _extract_key_from_reply(body: bytes, device_id: str) -> tuple[str | None, int | None, dict]:
    """Pull a localKey out of the reply envelopes the gateways use."""
    def _json(raw):
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            try:
                return json.loads(
                    zlib.decompress(base64.b64decode(raw), 16 + zlib.MAX_WBITS)
                )
            except Exception:  # noqa: BLE001
                return None

    outer = _json(body)
    if not isinstance(outer, dict):
        return None, None, {"raw_len": len(body)}
    info: dict = {"keys": sorted(outer.keys())[:12], "errNo": outer.get("errNo")}

    inner = parse_localkey_response(body)
    if isinstance(inner, dict) and inner.get("key"):
        return str(inner["key"]), _as_int(inner.get("vers")), inner

    data = outer.get("data")
    if isinstance(data, str):
        decoded = _json(data)
        if decoded is not None:
            data = decoded
    if isinstance(data, dict):
        key = data.get("localkey") or data.get("localKey")
        if key:
            return (str(key),
                    _as_int(data.get("localkey_vers") or data.get("vers")), data)
        results = data.get("results") or outer.get("results")
        if isinstance(results, dict):
            key_list = results.get("keyList") or results.get("keylist") or []
            for item in key_list:
                if not isinstance(item, dict):
                    continue
                dev = str(item.get("dev") or item.get("deviceId") or "")
                if dev.upper() == device_id.upper() and item.get("key"):
                    return str(item["key"]), _as_int(item.get("vers")), item

    key = outer.get("localkey") or outer.get("localKey") or outer.get("key")
    if key:
        return (str(key), _as_int(outer.get("localkey_vers") or outer.get("vers")), outer)
    return None, None, info


def try_mqtt_brokers(access_token: str, device_id: str, account_client_id: str,
                     brokers: list[tuple[str, int, str]],
                     timeout: float) -> tuple[str, int | None, str, int] | None:
    client_ids = []
    if account_client_id:
        client_ids.append(account_client_id)   # banto6 client_id / phone
    client_ids.append(derive_client_id(secrets.token_hex(16), PACKAGE))

    for host, port, mode in brokers:
        for mqtt_client_id in client_ids:
            for auth_mode in ("gateway", "token-user", "token-pass", "token-both"):
                if auth_mode == "gateway":
                    username, password = derive_gateway_auth()
                else:
                    username, password = {
                        "token-user": (access_token, ""),
                        "token-pass": ("", access_token),
                        "token-both": (access_token, access_token),
                    }[auth_mode]
                creds = SimpleNamespace(host=host, port=port, client_id=mqtt_client_id,
                                        username=username, password=password)
                label = (f"{host}:{port}{' '+mode if mode else ''} "
                         f"client={mqtt_client_id[:12]}... auth={auth_mode}")
                try:
                    if mode == "legacy":
                        conn = LegacyTlsMqttConnection(creds)
                    elif mode in ("tls", "ssl", "1", "true"):
                        conn = _TlsMqttConnection(creds)
                    else:
                        conn = PlainMqttConnection(creds)
                except (GatewayError, GatewayConnectionError, OSError, ssl.SSLError) as exc:
                    print(f"  {label}: connect {type(exc).__name__}: {str(exc)[:120]}")
                    continue
                try:
                    # Try both uSDK topic families: Client/ (acu) and Dev/ (acd),
                    # plus the user-level response namespace.
                    for topic in (f"Client/{mqtt_client_id}/Business/Down",
                                  f"Dev/{mqtt_client_id}/Business/Down",
                                  "Client/#", "Dev/#", "User/#"):
                        try:
                            conn.subscribe(topic, timeout=2.0)
                        except (GatewayError, GatewayConnectionError) as exc:
                            print(f"  {label}: subscribe {topic} "
                                  f"{type(exc).__name__}: {str(exc)[:80]}")
                    sn = str(int(time.time() * 1000) % 1_000_000_000)
                    variants = list(_mqtt_request_variants(device_id, access_token, sn))
                    for prefix in ("Client", "Dev"):
                        up = f"{prefix}/{mqtt_client_id}/Business/Up"
                        for _kind, payload in variants:
                            conn.publish(up, payload)
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        try:
                            replies = conn.poll(1.0)
                        except GatewayConnectionError:
                            break
                        for reply_topic, body in replies:
                            key, version, detail = _extract_key_from_reply(body, device_id)
                            print(f"  {label} reply topic={reply_topic} "
                                  f"keys={detail.get('keys')} errNo={detail.get('errNo')} "
                                  f"key={'yes' if key else 'no'}")
                            if key:
                                return key, version, host, port
                except (GatewayError, GatewayConnectionError, OSError, ssl.SSLError) as exc:
                    print(f"  {label}: {type(exc).__name__}: {str(exc)[:120]}")
                finally:
                    try:
                        conn.close()
                    except OSError:
                        pass
    return None


def try_gateways(access_token: str, device_id: str, hosts: list[str],
                 timeout: float) -> tuple[str, int | None, str, int] | None:
    for spec in hosts:
        host, _, port_text = spec.partition(":")
        port = int(port_text or "58702")
        creds = GatewayCreds.derive(
            usdk_client_id=secrets.token_hex(16),
            access_token=access_token,
            package=PACKAGE,
            host=host,
            port=port,
        )
        try:
            key = get_localkey_via_gateway(creds, device_id, timeout=timeout)
        except (GatewayError, GatewayConnectionError, OSError, TimeoutError, ValueError) as exc:
            print(f"  {host}:{port}: {type(exc).__name__}: {str(exc)[:140]}")
            continue
        except Exception as exc:  # noqa: BLE001 - keep trying other candidates
            print(f"  {host}:{port}: unexpected {type(exc).__name__}: {str(exc)[:140]}")
            continue
        print(f"  {host}:{port}: FOUND key (version={key.version})")
        return key.key, key.version, host, port
    return None


def verify_local(washer_ip: str, device_id: str, local_key: str) -> bool:
    print("verifying key against the washer over uSS (read-only)...")
    try:
        blobs = read_status(washer_ip, device_id, local_key, timeout=4.0)
    except Exception as exc:  # noqa: BLE001
        print(f"  uSS read failed: {type(exc).__name__}: {exc}")
        return False
    if not blobs:
        print("  handshake ok, but no payload decrypted -- key is likely wrong")
        return False
    ok = False
    for index, blob in enumerate(blobs):
        cae = len(blob) >= 4 and blob[2:4] == b"\x27\x15"
        epp = b"\xff\xff" in blob[:200]
        ok = ok or cae or epp
        print(f"  blob[{index}] len={len(blob)} cae={cae} epp={epp} head={blob[:24].hex()}")
    print("  key verified" if ok else "  decrypted, but no CAE/EPP signature seen")
    return ok


def _save_key(path: Path, device_id: str, key: str, version: int | None) -> None:
    payload = json.dumps(
        {"device_id": device_id, "local_key": key, "localkey_version": version}, indent=2
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(payload + "\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    print(f"  key written to {path} (mode 0600)")


def _save_and_verify(
    path: Path,
    device_id: str,
    key: str,
    version: int | None,
    washer_ip: str,
    skip_verify: bool,
) -> int:
    """Save the key, then make verification failure visible to scripts."""
    _save_key(path, device_id, key, version)
    if skip_verify:
        print("  local verification skipped")
        return 0
    if not verify_local(washer_ip, device_id, key):
        print("  key saved, but local verification failed", file=sys.stderr)
        return 5
    return 0


def load_env(path: Path) -> None:
    """Load KEY=VALUE lines from .env (no python-dotenv dependency)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _save_token(path: Path, access_token: str, client_id: str, app_source: str) -> None:
    payload = json.dumps(
        {"access_token": access_token, "client_id": client_id,
         "app_source": app_source, "saved_at": int(time.time())},
        indent=2,
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(payload + "\n")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    print(f"  access token cached in {path} (mode 0600)")


def _load_token(path: Path) -> tuple[str, str, str]:
    text = path.expanduser().read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text.strip(), "", ""
    return (str(data.get("access_token", "")), str(data.get("client_id", "")),
            str(data.get("app_source", "")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--creds-file", help="JSON with refresh_token/client_id/app_source")
    parser.add_argument("--refresh-token")
    parser.add_argument("--client-id")
    parser.add_argument("--app-source", choices=sorted(APP_SOURCES), default=None)
    parser.add_argument("--env-file", default=".env",
                        help="read HAIER_* values from this file (default .env)")
    parser.add_argument("--phone")
    parser.add_argument("--password", help="omit to prompt with getpass")
    parser.add_argument("--force-login", action="store_true",
                        help="ignore a cached access token and log in again")
    parser.add_argument("--device-id",
                        help="washer MAC/device id; defaults to HAIER_DEVICE_ID")
    parser.add_argument("--washer-ip",
                        help="LAN address for verification; defaults to HAIER_WASHER_IP")
    parser.add_argument("--hosts", help="comma-separated host:port candidates")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--key-out", default="local_key.json")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--access-token-file",
                        help="cached access token (raw or JSON) from a previous run")
    parser.add_argument("--token-out",
                        help="write access token/client_id/app_source JSON here (0600)")
    parser.add_argument("--mqtt-info-only", action="store_true",
                        help="dump the MQTT broker info endpoint and exit")
    parser.add_argument("--mqtt-probe", action="store_true",
                        help="try the China MQTT brokers directly for devLocalkey")
    parser.add_argument(
        "--mqtt-brokers",
        default=("39.107.46.61:56262:legacy,gw-sgp.haieriot.net:58702:tls"),
        help="comma-separated host:port[:legacy|tls]",
    )
    args = parser.parse_args()
    load_env(Path(args.env_file).expanduser())
    args.device_id = args.device_id or os.environ.get("HAIER_DEVICE_ID", "")
    args.washer_ip = args.washer_ip or os.environ.get("HAIER_WASHER_IP", "")

    if not args.device_id:
        if not args.washer_ip:
            parser.error("set --washer-ip/HAIER_WASHER_IP so UDISCOVERY can find "
                         "the device, or set --device-id/HAIER_DEVICE_ID")
        try:
            info = udiscovery_query(args.washer_ip, timeout=2.0)
        except Exception as exc:  # noqa: BLE001
            parser.error(f"UDISCOVERY failed: {type(exc).__name__}: {exc}")
        if info is None:
            parser.error("UDISCOVERY got no reply; set --device-id/HAIER_DEVICE_ID")
        args.device_id = "".join(ch for ch in info.device_id if ch.isalnum()).upper()
        if not args.device_id:
            parser.error("UDISCOVERY replied without a device id; set --device-id")
        print(f"discovered device {args.device_id} at {args.washer_ip}")

    if not args.washer_ip and not args.skip_verify:
        parser.error("--washer-ip or HAIER_WASHER_IP is required "
                     "(or pass --skip-verify)")

    phone = args.phone or os.environ.get("HAIER_PHONE", "")
    password = args.password or os.environ.get("HAIER_PASSWORD", "")
    refresh_token = args.refresh_token or os.environ.get("HAIER_REFRESH_TOKEN", "")
    client_id = args.client_id or os.environ.get("HAIER_CLIENT_ID", "")
    app_source = args.app_source or os.environ.get("HAIER_APP_SOURCE", "")
    token_file = os.environ.get("HAIER_TOKEN_FILE", "")
    token_out = args.token_out or token_file

    if args.creds_file:
        creds = json.loads(Path(args.creds_file).expanduser().read_text())
        refresh_token = refresh_token or creds.get("refresh_token", "")
        client_id = client_id or creds.get("client_id", "")
        app_source = app_source or creds.get("app_source", "")

    cached_source = args.access_token_file or token_file
    cached_token = ""
    if cached_source and Path(cached_source).expanduser().exists():
        cached_token, token_client, token_source = _load_token(
            Path(cached_source).expanduser()
        )
        client_id = client_id or token_client
        app_source = app_source or token_source

    if phone and (args.force_login or not cached_token):
        if not password:
            password = getpass.getpass("海尔智家 App 密码: ")
        access_token, new_refresh, client_id = phone_login(phone, password)
        app_source = "app"
        print(f"logged in as {client_id}; accessToken length={len(access_token)}")
    elif cached_token:
        access_token = cached_token
        client_id = client_id or phone
        if not client_id:
            raise SystemExit(
                "cached token needs a client_id; set HAIER_CLIENT_ID or --client-id"
            )
        app_source = app_source or "app"
        print(f"using cached accessToken length={len(access_token)}; "
              f"client_id={client_id[:6]}...")
    else:
        if not refresh_token or not client_id:
            raise SystemExit(
                "need HAIER_PHONE/--phone, HAIER_REFRESH_TOKEN/--refresh-token, "
                "a cached token, or --creds-file"
            )
        app_source = app_source or "wxapp"
        if app_source not in APP_SOURCES:
            raise SystemExit(f"app_source must be one of {sorted(APP_SOURCES)}")
        access_token, new_refresh, client_id = refresh_access_token(
            refresh_token, client_id, app_source
        )
        print(f"refreshed token for client_id={client_id[:6]}...; "
              f"accessToken length={len(access_token)}")

    if token_out:
        _save_token(Path(token_out).expanduser(), access_token, client_id, app_source)

    print("querying mainland device list...")
    try:
        devices = get_devices(access_token, client_id, app_source)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"device list failed: {type(exc).__name__}: {exc}")

    target = None
    for device in devices:
        print("  device: " + json.dumps({
            key: device.get(key) for key in (
                "deviceId", "deviceName", "deviceType", "productCodeT",
                "productNameT", "online", "wifiType",
            ) if key in device
        }, ensure_ascii=False))
        if str(device.get("deviceId", "")).replace(":", "").upper() == args.device_id.upper():
            target = device
    if target is None:
        print(f"  target {args.device_id} not found in this account's device list")
        return 2

    # If the cloud ever exposes the key directly, take it.
    for key, value in target.items():
        if "local" in key.lower() and "key" in key.lower() and isinstance(value, str) and len(value) == 32:
            print(f"  cloud device list carries {key}; saving it")
            return _save_and_verify(
                Path(args.key_out), args.device_id, value, None,
                args.washer_ip, args.skip_verify,
            )

    if args.mqtt_probe:
        print("querying MQTT broker info...")
        get_mqtt_info(access_token, client_id, app_source)
        brokers = []
        for item in args.mqtt_brokers.split(","):
            item = item.strip()
            if not item:
                continue
            parts = item.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 1883
            mode = parts[2].lower() if len(parts) > 2 else ""
            brokers.append((host, port, mode))
        print("probing China MQTT brokers...")
        found = try_mqtt_brokers(access_token, args.device_id, client_id,
                                 brokers, args.timeout)
        if found:
            key, version, host, port = found
            result = _save_and_verify(
                Path(args.key_out), args.device_id, key, version,
                args.washer_ip, args.skip_verify,
            )
            if result == 0:
                print(f"done via {host}:{port}")
            return result
        print("no MQTT broker returned a key")
        return 4

    print("querying MQTT broker info...")
    get_mqtt_info(access_token, client_id, app_source)
    if args.mqtt_info_only:
        return 0

    hosts = ([h.strip() for h in args.hosts.split(",") if h.strip()]
             if args.hosts else DEFAULT_HOSTS)
    print("trying uSDK devLocalkey gateways...")
    found = try_gateways(access_token, args.device_id, hosts, args.timeout)
    if not found:
        print("no gateway returned a key")
        return 3
    key, version, host, port = found
    result = _save_and_verify(
        Path(args.key_out), args.device_id, key, version,
        args.washer_ip, args.skip_verify,
    )
    if result == 0:
        print(f"done via {host}:{port}")
    return result


if __name__ == "__main__":
    sys.exit(main())
