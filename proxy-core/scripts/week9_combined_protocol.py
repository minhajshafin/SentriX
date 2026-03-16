#!/usr/bin/env python3

import json
import socket
import time
from pathlib import Path

MQTT_PROXY_HOST = "127.0.0.1"
MQTT_PROXY_PORT = 1884
COAP_PROXY_HOST = "127.0.0.1"
COAP_PROXY_PORT = 5684
METRICS_PATH = Path("/tmp/sentrix-week8/metrics.json")
DEBUG_PATH = Path("/tmp/sentrix-week8/features.jsonl")


def mqtt_connect(client_id: str) -> bytes:
    """Generate MQTT CONNECT packet."""
    client_bytes = client_id.encode("utf-8")
    var_header = b"\x00\x04MQTT\x04\x02\x00<"
    payload = len(client_bytes).to_bytes(2, "big") + client_bytes
    remaining_length = len(var_header) + len(payload)
    return bytes([0x10, remaining_length]) + var_header + payload


def encode_remaining_length(length: int) -> bytes:
    """Encode MQTT remaining length (variable length)."""
    encoded = bytearray()
    while True:
        encoded_byte = length % 128
        length //= 128
        if length > 0:
            encoded_byte |= 0x80
        encoded.append(encoded_byte)
        if length == 0:
            break
    return bytes(encoded)


def mqtt_publish(topic: str, payload: str) -> bytes:
    """Generate MQTT PUBLISH packet."""
    topic_bytes = topic.encode("utf-8")
    payload_bytes = payload.encode("utf-8")
    flags = 0x30 | (1 << 1)  # QoS 1
    var_header = len(topic_bytes).to_bytes(2, "big") + topic_bytes + bytes([0, 1])
    remaining_length = len(var_header) + len(payload_bytes)
    return bytes([flags]) + encode_remaining_length(remaining_length) + var_header + payload_bytes


def coap_get(message_id: int, path: str) -> bytes:
    """Generate CoAP GET packet."""
    segments = [s for s in path.split("/") if s]
    packet = bytearray([0x40, 0x01, (message_id >> 8) & 0xFF, message_id & 0xFF])
    for segment in segments:
        option_number = 11
        value = segment.encode("utf-8")
        packet.append((12 << 4) | len(value))
        packet.extend(value)
    return bytes(packet)


def main() -> int:
    print("[Week 9] Combined MQTT + CoAP Integration Test\n")
    print("=" * 70)

    mqtt_count = 0
    coap_count = 0
    errors = 0

    # MQTT phase
    print("\n[MQTT Phase] Simulating IoT devices via MQTT\n")
    mqtt_devices = [
        ("sensor/temp", "room1", "22.5C"),
        ("sensor/humidity", "room2", "45%"),
        ("actuator/light", "hallway", "brightness:80"),
    ]

    for topic, device, value in mqtt_devices:
        try:
            with socket.create_connection((MQTT_PROXY_HOST, MQTT_PROXY_PORT), timeout=2) as sock:
                sock.sendall(mqtt_connect(device))
                resp = sock.recv(64)
                if resp:
                    mqtt_count += 1
                    print(f"  [{device}] CONNECT: OK")
                    time.sleep(0.05)

                    sock.sendall(mqtt_publish(topic, value))
                    time.sleep(0.05)
                    mqtt_count += 1
                    print(f"  [{device}] PUBLISH {topic}={value}: OK")
        except Exception as e:
            errors += 1
            print(f"  [{device}] error: {e}")

    time.sleep(0.5)

    # CoAP phase
    print("\n[CoAP Phase] Simulating IoT sensors via CoAP\n")
    coap_resources = [
        (1001, "/temp/indoor"),
        (1002, "/temp/outdoor"),
        (1003, "/pressure/room1"),
        (1004, "/light/hallway"),
    ]

    for msg_id, path in coap_resources:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2.0)
                sock.sendto(coap_get(msg_id, path), (COAP_PROXY_HOST, COAP_PROXY_PORT))
                resp, _ = sock.recvfrom(2048)
                if resp:
                    coap_count += 1
                    print(f"  GET {path}: OK ({len(resp)} bytes)")
                    time.sleep(0.05)
        except Exception as e:
            errors += 1
            print(f"  GET {path}: error {e}")

    time.sleep(1.0)

    # Collect results
    metrics = {}
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text())

    debug_rows = []
    if DEBUG_PATH.exists():
        debug_rows = [
            json.loads(line) for line in DEBUG_PATH.read_text().splitlines() if line.strip()
        ]

    mqtt_rows = [r for r in debug_rows if r.get("protocol") == "mqtt"]
    coap_rows = [r for r in debug_rows if r.get("protocol") == "coap"]

    # Feature distance check: compare behavioral vs legacy on recent packets
    feature_deltas = []
    for row in debug_rows[-10:]:
        if row.get("behavioral") and row.get("legacy"):
            legacy = row["legacy"]
            behavioral = row["behavioral"]
            delta = sum(abs(l - b) for l, b in zip(legacy, behavioral)) / len(legacy)
            feature_deltas.append(delta)

    report = {
        "test": "combined_protocol_integration",
        "mqtt_packets": mqtt_count,
        "coap_packets": coap_count,
        "total_packets": mqtt_count + coap_count,
        "errors": errors,
        "proxy_metrics": metrics,
        "captured_mqtt_rows": len(mqtt_rows),
        "captured_coap_rows": len(coap_rows),
        "captured_total_rows": len(debug_rows),
        "feature_consistency": {
            "behavioral_legacy_avg_delta": sum(feature_deltas) / len(feature_deltas) if feature_deltas else 0,
            "samples_analyzed": len(feature_deltas),
        },
        "timestamp": time.time(),
    }

    report_path = Path("/tmp/sentrix-week8/week9_combined_protocol_report.json")
    report_path.write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 70)
    print(f"\nCombined Protocol Integration Report: {report_path}")
    print(json.dumps(report, indent=2))

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
