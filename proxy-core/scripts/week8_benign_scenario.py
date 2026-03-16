#!/usr/bin/env python3

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MQTT_PROXY_PORT = 1884
MQTT_PROXY_HOST = "127.0.0.1"
METRICS_PATH = Path("/tmp/sentrix-week8/metrics.json")
DEBUG_PATH = Path("/tmp/sentrix-week8/features.jsonl")
EVENTS_PATH = Path("/tmp/sentrix-week8/events.jsonl")


def mqtt_connect_packet(client_id: str) -> bytes:
    """Generate a minimal MQTT CONNECT packet."""
    client_bytes = client_id.encode("utf-8")
    var_header = b"\x00\x04MQTT\x04\x02\x00<"
    payload = len(client_bytes).to_bytes(2, "big") + client_bytes
    remaining_length = len(var_header) + len(payload)
    return bytes([0x10, remaining_length]) + var_header + payload


def mqtt_subscribe_packet(packet_id: int, topic: str, qos: int = 1) -> bytes:
    """Generate an MQTT SUBSCRIBE packet."""
    topic_bytes = topic.encode("utf-8")
    payload = packet_id.to_bytes(2, "big")
    payload += len(topic_bytes).to_bytes(2, "big") + topic_bytes
    payload += bytes([qos])
    remaining_length = len(payload)
    return bytes([0x80, remaining_length]) + payload


def mqtt_publish_packet(topic: str, payload_text: str = "", qos: int = 1) -> bytes:
    """Generate an MQTT PUBLISH packet."""
    topic_bytes = topic.encode("utf-8")
    payload_bytes = payload_text.encode("utf-8")
    flags = 0x30 | (qos << 1)
    packet = bytes([flags])
    var_header = len(topic_bytes).to_bytes(2, "big") + topic_bytes
    if qos > 0:
        var_header += bytes([0x00, 0x01])  # packet ID
    remaining_length = len(var_header) + len(payload_bytes)
    return packet + bytes([remaining_length]) + var_header + payload_bytes


def run_mqtt_benign_scenario(num_clients: int = 3, msgs_per_client: int = 5) -> dict:
    """Simulate multiple MQTT clients subscribing and publishing."""
    results = {
        "scenario": "benign_mqtt",
        "num_clients": num_clients,
        "msgs_per_client": msgs_per_client,
        "sent_packets": 0,
        "errors": 0,
    }

    for client_idx in range(num_clients):
        client_id = f"week8-benign-{client_idx}"
        try:
            with socket.create_connection(
                (MQTT_PROXY_HOST, MQTT_PROXY_PORT), timeout=2.0
            ) as sock:
                # Send CONNECT
                sock.sendall(mqtt_connect_packet(client_id))
                response = sock.recv(64)
                if not response:
                    results["errors"] += 1
                    continue
                results["sent_packets"] += 1

                # Send SUBSCRIBEs
                for sub_idx in range(2):
                    topic = f"sensors/temp/room{sub_idx}"
                    sock.sendall(mqtt_subscribe_packet(sub_idx + 1, topic))
                    time.sleep(0.05)
                    results["sent_packets"] += 1

                # Send PUBLISHes
                for msg_idx in range(msgs_per_client):
                    topic = f"sensors/temp/output"
                    payload = f"value_{msg_idx}"
                    sock.sendall(mqtt_publish_packet(topic, payload))
                    time.sleep(0.05)
                    results["sent_packets"] += 1

        except Exception as e:
            results["errors"] += 1
            print(f"Error with client {client_id}: {e}")

    return results


def main() -> int:
    # Clear prior outputs
    for path in [METRICS_PATH, DEBUG_PATH, EVENTS_PATH]:
        if path.exists():
            path.unlink()

    print("[Week 8] Starting benign MQTT scenario...")
    time.sleep(0.5)

    benign_result = run_mqtt_benign_scenario(num_clients=3, msgs_per_client=4)

    # Wait for metrics to flush
    time.sleep(2.0)

    # Read results
    metrics = {}
    if METRICS_PATH.exists():
        metrics = json.loads(METRICS_PATH.read_text())

    debug_rows = []
    if DEBUG_PATH.exists():
        debug_rows = [
            json.loads(line)
            for line in DEBUG_PATH.read_text().splitlines()
            if line.strip()
        ]

    report = {
        "scenario": benign_result,
        "metrics_collected": metrics,
        "debug_feature_rows": len(debug_rows),
        "timestamp": time.time(),
    }

    report_path = Path("/tmp/sentrix-week8/benign_scenario_report.json")
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Benign scenario report: {report_path}")
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
