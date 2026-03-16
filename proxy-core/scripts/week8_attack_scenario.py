#!/usr/bin/env python3

import json
import socket
import time
from pathlib import Path

MQTT_PROXY_PORT = 1884
MQTT_PROXY_HOST = "127.0.0.1"
DEBUG_PATH = Path("/tmp/sentrix-week8/features.jsonl")
METRICS_PATH = Path("/tmp/sentrix-week8/metrics.json")


def encode_remaining_length(length: int) -> bytes:
    """Encode MQTT remaining length as variable-length encoding."""
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


def mqtt_connect_packet(client_id: str) -> bytes:
    """Generate a minimal MQTT CONNECT packet."""
    client_bytes = client_id.encode("utf-8")
    var_header = b"\x00\x04MQTT\x04\x02\x00<"
    payload = len(client_bytes).to_bytes(2, "big") + client_bytes
    remaining_length = len(var_header) + len(payload)
    return bytes([0x10, remaining_length]) + var_header + payload


def mqtt_publish_packet(topic: str, payload_text: str = "", qos: int = 1) -> bytes:
    """Generate an MQTT PUBLISH packet with large payload."""
    topic_bytes = topic.encode("utf-8")
    payload_bytes = payload_text.encode("utf-8")
    flags = 0x30 | (qos << 1)
    var_header = len(topic_bytes).to_bytes(2, "big") + topic_bytes
    if qos > 0:
        var_header += bytes([0x00, 0x01])  # packet ID
    remaining_length = len(var_header) + len(payload_bytes)
    return bytes([flags]) + encode_remaining_length(remaining_length) + var_header + payload_bytes


def run_attack_scenario() -> dict:
    """
    Generate suspicious MQTT traffic patterns designed to trigger detection:
    - High message rate
    - Large payloads
    - Many different client IDs (subscription breadth)
    """
    results = {
        "scenario": "attack_mqtt",
        "packets_sent": 0,
        "errors": 0,
        "detections_triggered": 0,
    }

    # Attack 1: Rapid message rate from single client
    print("[Week 8 Attack] Scenario 1: High message rate...")
    try:
        with socket.create_connection(
            (MQTT_PROXY_HOST, MQTT_PROXY_PORT), timeout=2.0
        ) as sock:
            sock.sendall(mqtt_connect_packet("attack-rate-1"))
            time.sleep(0.1)

            # Send many messages rapidly to the same topic
            for i in range(8):
                text = "X" * 500  # Large payload
                sock.sendall(mqtt_publish_packet("cmd/exec", text))
                results["packets_sent"] += 1
                time.sleep(0.02)  # Minimize delay to increase rate
    except Exception as e:
        print(f"Attack 1 error: {e}")
        results["errors"] += 1

    time.sleep(0.5)

    # Attack 2: Large payload from many clients
    print("[Week 8 Attack] Scenario 2: Oversized payloads...")
    for client_idx in range(4):
        try:
            with socket.create_connection(
                (MQTT_PROXY_HOST, MQTT_PROXY_PORT), timeout=2.0
            ) as sock:
                sock.sendall(mqtt_connect_packet(f"attack-payload-{client_idx}"))
                time.sleep(0.05)

                # Send one large payload per client
                large_payload = "A" * 2000  # 2KB payload
                sock.sendall(mqtt_publish_packet("data/exfil", large_payload))
                results["packets_sent"] += 1
                time.sleep(0.05)
        except Exception as e:
            print(f"Client {client_idx} error: {e}")
            results["errors"] += 1

    time.sleep(1.0)

    # Read feature export to check anomaly scores
    detected_attacks = 0
    if DEBUG_PATH.exists():
        rows = [
            json.loads(line)
            for line in DEBUG_PATH.read_text().splitlines()
            if line.strip()
        ]
        # Check for high anomaly scores in recent rows
        for row in rows[-results["packets_sent"] :]:
            score = row.get("decision", {}).get("anomaly_score", 0)
            if score > 0.75:  # High anomaly threshold
                detected_attacks += 1
                print(
                    f"  Detection: {row['source_id']} anomaly_score={score:.3f} action={row['decision']['action']}"
                )

    results["detections_triggered"] = detected_attacks
    results["final_metrics"] = (
        json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    )
    return results


if __name__ == "__main__":
    print("[Week 8 Running Attack Scenario]\n")
    result = run_attack_scenario()
    print(json.dumps(result, indent=2))

    report_path = Path("/tmp/sentrix-week8/attack_scenario_report.json")
    report_path.write_text(json.dumps(result, indent=2))
    print(f"\nAttack scenario report saved to {report_path}")
