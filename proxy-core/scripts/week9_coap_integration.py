#!/usr/bin/env python3

import json
import socket
import time
from pathlib import Path

COAP_PROXY_PORT = 5684
COAP_PROXY_HOST = "127.0.0.1"
DEBUG_PATH = Path("/tmp/sentrix-week8/features.jsonl")
METRICS_PATH = Path("/tmp/sentrix-week8/metrics.json")


def coap_get_packet(message_id: int, path: str) -> bytes:
    """Generate a CoAP GET request packet."""
    segments = [segment for segment in path.split("/") if segment]
    packet = bytearray([0x40, 0x01, (message_id >> 8) & 0xFF, message_id & 0xFF])
    previous_option = 0
    for segment in segments:
        option_number = 11  # URI-Path
        delta = option_number - previous_option
        value = segment.encode("utf-8")
        if delta > 12 or len(value) > 12:
            raise ValueError("path segment too large for simple smoke packet")
        packet.append((delta << 4) | len(value))
        packet.extend(value)
        previous_option = option_number
    return bytes(packet)


def coap_post_payload(message_id: int, path: str, payload: bytes) -> bytes:
    """Generate a CoAP POST request with payload."""
    segments = [segment for segment in path.split("/") if segment]
    packet = bytearray(
        [0x40, 0x02, (message_id >> 8) & 0xFF, message_id & 0xFF]
    )  # POST
    previous_option = 0
    for segment in segments:
        option_number = 11  # URI-Path
        delta = option_number - previous_option
        value = segment.encode("utf-8")
        packet.append((delta << 4) | len(value))
        packet.extend(value)
        previous_option = option_number

    # Add payload marker (0xFF) and payload
    packet.append(0xFF)
    packet.extend(payload)
    return bytes(packet)


def run_coap_benign_scenario() -> dict:
    """Send benign CoAP traffic through the proxy."""
    results = {
        "scenario": "benign_coap",
        "packets_sent": 0,
        "errors": 0,
    }

    print("[Week 9] CoAP Benign Scenario: GET requests to various resources\n")

    resources = [
        "/.well-known/core",
        "/sensors/temperature",
        "/sensors/humidity",
        "/actuators/lamp",
        "/status/uptime",
    ]

    for resource in resources:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2.0)
                sock.sendto(
                    coap_get_packet(results["packets_sent"] + 1, resource),
                    (COAP_PROXY_HOST, COAP_PROXY_PORT),
                )
                response, _ = sock.recvfrom(2048)
                if response:
                    results["packets_sent"] += 1
                    print(f"  GET {resource}: OK (response {len(response)} bytes)")
                else:
                    results["errors"] += 1
        except socket.timeout:
            results["errors"] += 1
            print(f"  GET {resource}: timeout")
        except Exception as e:
            results["errors"] += 1
            print(f"  GET {resource}: error {e}")

    return results


def run_coap_attack_scenario() -> dict:
    """Send attack-like CoAP traffic (large payloads, discovery bombing)."""
    results = {
        "scenario": "attack_coap",
        "packets_sent": 0,
        "errors": 0,
    }

    print("\n[Week 9] CoAP Attack Scenario: Large payloads and discovery attempts\n")

    # Attack 1: Large payload POST
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2.0)
            large_payload = b"X" * 1000
            packet = coap_post_payload(
                results["packets_sent"] + 1, "/cmd/exfil", large_payload
            )
            sock.sendto(packet, (COAP_PROXY_HOST, COAP_PROXY_PORT))
            response, _ = sock.recvfrom(2048)
            if response:
                results["packets_sent"] += 1
                print(f"  POST /cmd/exfil (payload {len(large_payload)} bytes): OK")
    except Exception as e:
        results["errors"] += 1
        print(f"  POST /cmd/exfil: error {e}")

    # Attack 2: Rapid discovery requests (/.well-known/core)
    for i in range(4):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.5)
                sock.sendto(
                    coap_get_packet(
                        results["packets_sent"] + 1, "/.well-known/core"
                    ),
                    (COAP_PROXY_HOST, COAP_PROXY_PORT),
                )
                response, _ = sock.recvfrom(2048)
                if response:
                    results["packets_sent"] += 1
                time.sleep(0.05)
        except Exception:
            results["errors"] += 1

    return results


def main() -> int:
    print("[Week 9] CoAP Integration Validation\n")
    print("=" * 60)

    benign = run_coap_benign_scenario()
    time.sleep(0.5)
    attack = run_coap_attack_scenario()
    time.sleep(1.0)

    # Collect metrics
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

    # Count CoAP rows
    coap_rows = [r for r in debug_rows if r.get("protocol") == "coap"]

    report = {
        "benign_scenario": benign,
        "attack_scenario": attack,
        "total_packets_sent": benign["packets_sent"] + attack["packets_sent"],
        "total_errors": benign["errors"] + attack["errors"],
        "metrics": metrics,
        "debug_coap_rows_captured": len(coap_rows),
        "timestamp": time.time(),
    }

    report_path = Path("/tmp/sentrix-week8/week9_coap_integration_report.json")
    report_path.write_text(json.dumps(report, indent=2))
    print("\n" + "=" * 60)
    print(f"CoAP Integration Report: {report_path}")
    print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
