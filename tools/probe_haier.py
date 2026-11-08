#!/usr/bin/env python3
"""Read-only LAN probe for Haier appliances.

Does three things, in order, and changes nothing on the appliance:

1. UDISCOVERY_UWT query on UDP :7083 (key-free; returns device id, uPlusId, uSS port,
   firmware, and whether the module currently reaches Haier's cloud).
2. TCP connect scan of the candidate local/control ports.
3. uSS HELLO handshake on :56800 (and optionally another port) -- the reply states the
   device's current localKey version, which is useful before you have a key at all.

No localKey is sent.  Intended for appliances you own, on your own LAN.

Usage:
    python3 -I probe_haier.py 192.168.1.50
    python3 -I probe_haier.py 192.168.1.50 --hello-port 12334
    python3 -I probe_haier.py 192.168.1.50 --skip-ports
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from dataclasses import dataclass, asdict

UDISCOVERY_PORT = 7083
CMD_SEARCH = 0x6915
CMD_DEVICE_INFO = 0x684D
USS_PORT = 56800

# Ports worth checking. 56800/12334 are the two known uSS generations; the rest are
# cloud-gateway ports from Haier manuals (outbound, but cheap to confirm they are closed).
CANDIDATE_PORTS = [
    56800, 12334, 7083,
    80, 443, 1883, 8883,
    56802, 56803, 56808, 56601, 56602, 56881, 56711, 56712,
    56692, 56611, 56612, 56691, 56701, 56702,
]


@dataclass
class Discovery:
    device_id: str = ""
    uplus_id: str = ""
    host: str = ""
    port: int = 0
    sdk_version: str = ""
    firmware: tuple[str, ...] = ()
    cloud_state: int | None = None
    protocol_tag: str = ""


def udiscovery_query(ip: str, timeout: float = 3.0) -> tuple[bytes | None, str]:
    payload = bytearray(56)
    payload[0x10:0x10 + 5] = b"2.0.0"
    payload[0x18:0x18 + len(b"UDISCOVERY_SDK")] = b"UDISCOVERY_SDK"
    packet = (
        b"Haier"
        + struct.pack(">I", CMD_SEARCH)
        + b"\x00" * 8
        + struct.pack(">I", len(payload))
        + bytes(payload)
    )

    last = "no reply"
    # Broadcast requires source port 7083; unicast is answered from an ephemeral port too.
    for bind in (("0.0.0.0", UDISCOVERY_PORT), ("0.0.0.0", 0)):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(bind)
            s.settimeout(timeout)
            s.sendto(packet, (ip, UDISCOVERY_PORT))
            data, addr = s.recvfrom(4096)
            return data, f"{addr[0]}:{addr[1]}"
        except OSError as exc:
            last = f"{type(exc).__name__}: {exc}"
        finally:
            s.close()
    return None, last


def _text(data: bytes) -> str:
    return data.split(b"\x00")[0].decode("ascii", "replace").strip()


def parse_udiscovery(data: bytes) -> Discovery | None:
    if len(data) < 0x49 or not data.startswith(b"Haier"):
        return None
    if struct.unpack_from(">I", data, 5)[0] != CMD_DEVICE_INFO:
        return None

    d = Discovery()
    d.device_id = _text(data[0x15:0x25])
    # BCD-packed: each byte is two digits; hex-encoding reproduces the cloud `wifiType`.
    d.uplus_id = data[0x25:0x45].hex()

    # Counted TLV area: type(1) | len(1) | value
    count = struct.unpack_from(">I", data, 0x45)[0]
    pos = 0x49
    for _ in range(min(count, 32)):
        if pos + 2 > len(data):
            break
        kind, length = data[pos], data[pos + 1]
        if kind == 0:
            break
        value = data[pos + 2:pos + 2 + length]
        if len(value) < length:
            break
        if kind == 0x03 and len(value) >= 4:
            d.cloud_state = struct.unpack_from(">I", value, 0)[0]
        pos += 2 + length

    if len(data) >= 0xF5:
        d.host = _text(data[0xE5:0xF5])
        d.port = struct.unpack_from(">H", data, 0xF5)[0]
    if len(data) >= 0xFD:
        d.sdk_version = _text(data[0xFD:0x105])
    if len(data) >= 0x115:
        d.firmware = tuple(x for x in (_text(data[0x105:0x10D]), _text(data[0x10D:0x115])) if x)
        d.protocol_tag = _text(data[0x115:])
    return d


def tcp_open(ip: str, port: int, timeout: float = 1.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((ip, port)) == 0
    finally:
        s.close()


def uss_hello(ip: str, port: int, device_id: str, timeout: float = 3.0,
              pro_ver: int = 2) -> dict:
    """Send one uSS HELLO and decode HELLO_RESP. No key, no state change."""
    type_byte = 0x01 if pro_ver == 2 else 0x6E
    dev = device_id.encode("ascii").ljust(32, b"\x00")[:32]
    payload = dev if pro_ver == 2 else dev + struct.pack(">II", 0, 0)
    header = struct.pack(
        ">IHBBIHH",
        0xEA60,            # info_code for HELLO
        len(payload) + 0x0A,
        type_byte,
        0,                 # plaintext
        1,                 # sn
        0,
        0,                 # session
    )
    packet = header + payload

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.sendall(packet)
        buf = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
            if len(buf) >= 6:
                declared = struct.unpack_from(">H", buf, 4)[0]
                if len(buf) >= 6 + declared:
                    break
        if len(buf) < 16:
            return {"ok": False, "error": "no complete reply", "raw": buf.hex()}
        info_code, length, tbyte, flag, sn, code2, session = struct.unpack_from(
            ">IHBBIHH", buf, 0
        )
        payload = buf[16:6 + length]
        out = {
            "ok": info_code == 0xEA61,
            "info_code": hex(info_code),
            "info_type": info_code - 0xEA60,
            "type_byte": hex(tbyte),
            "flag": flag,
            "sn": sn,
            "session": session,
            "payload_hex": payload.hex(),
        }
        if info_code == 0xEA61 and len(payload) >= 8:
            status, version = struct.unpack_from(">II", payload, 0)
            out["status"] = status
            out["localkey_version"] = version
        return out
    except OSError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        s.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("ip", help="appliance LAN IP")
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--hello-port", type=int, default=USS_PORT,
                   help="port for the uSS HELLO probe (default 56800)")
    p.add_argument("--skip-ports", action="store_true", help="skip the TCP scan")
    p.add_argument("--skip-discovery", action="store_true")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    report: dict = {"ip": args.ip}

    disc = None
    if not args.skip_discovery:
        data, peer = udiscovery_query(args.ip, args.timeout)
        if data:
            disc = parse_udiscovery(data)
            report["udiscovery"] = {
                "peer": peer,
                "parsed": asdict(disc) if disc else None,
                "raw_hex": data.hex(),
            }
        else:
            report["udiscovery"] = {"error": peer}

    if not args.skip_ports:
        report["ports"] = {
            str(port): tcp_open(args.ip, port, min(args.timeout, 1.5))
            for port in CANDIDATE_PORTS
        }

    device_id = disc.device_id if disc else ""
    if args.hello_port and (device_id or not args.skip_ports):
        if not device_id:
            report["uss_hello"] = {
                "error": "no device id from UDISCOVERY; uSS HELLO needs the module MAC"
            }
        else:
            report["uss_hello"] = uss_hello(
                args.ip, args.hello_port, device_id, args.timeout
            )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"target: {args.ip}")
        ud = report.get("udiscovery", {})
        if "parsed" in ud and ud["parsed"]:
            d = ud["parsed"]
            print(f"  UDISCOVERY: ok (from {ud['peer']})")
            print(f"    device id : {d['device_id']}")
            print(f"    uPlusId   : {d['uplus_id']}")
            print(f"    local IP  : {d['host']}:{d['port']}")
            print(f"    sdk/fw    : {d['sdk_version']} / {d['firmware']}")
            print(f"    cloud     : {d['cloud_state']} "
                  f"(1000=connected, 1006=disconnected)")
            print(f"    protocol  : {d['protocol_tag']}")
        else:
            print(f"  UDISCOVERY: {ud.get('error', 'no reply')}")
        if "ports" in report:
            open_ports = [int(k) for k, v in report["ports"].items() if v]
            print(f"  TCP open  : {open_ports or 'none'}")
        hello = report.get("uss_hello")
        if hello:
            if hello.get("ok"):
                print(f"  uSS HELLO: ok, session={hello['session']}, "
                      f"localkey_version={hello.get('localkey_version')}")
            else:
                print(f"  uSS HELLO: {hello.get('error') or hello}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
