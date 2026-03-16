#!/usr/bin/env python3

import socket
import time
from pathlib import Path

MQTT_DIRECT_PORT = 1883
MQTT_PROXY_PORT = 1884
MQTT_HOST = "127.0.0.1"
ITERATIONS = 50


def mqtt_connect_packet(client_id: str) -> bytes:
    """Generate minimal MQTT CONNECT."""
    client_bytes = client_id.encode("utf-8")
    var_header = b"\x00\x04MQTT\x04\x02\x00<"
    payload = len(client_bytes).to_bytes(2, "big") + client_bytes
    remaining_length = len(var_header) + len(payload)
    return bytes([0x10, remaining_length]) + var_header + payload


def measure_latency(port: int, label: str, iterations: int = 50) -> dict:
    """Measure round-trip latency for MQTT CONNECT → CONNACK."""
    latencies = []
    errors = 0

    for i in range(iterations):
        try:
            start = time.perf_counter_ns()
            with socket.create_connection(
                (MQTT_HOST, port), timeout=2.0
            ) as sock:
                sock.sendall(mqtt_connect_packet(f"latency-test-{i}"))
                response = sock.recv(64)
                end = time.perf_counter_ns()
                if response:
                    latencies.append((end - start) / 1_000_000)  # Convert to ms
        except Exception as e:
            errors += 1

    if not latencies:
        return {"error": f"no successful connections on {label}"}

    latencies.sort()
    return {
        "port": port,
        "label": label,
        "samples": len(latencies),
        "errors": errors,
        "latency_ms": {
            "min": latencies[0],
            "p50": latencies[len(latencies) // 2],
            "p95": latencies[int(len(latencies) * 0.95)],
            "p99": latencies[int(len(latencies) * 0.99)],
            "max": latencies[-1],
            "mean": sum(latencies) / len(latencies),
        },
    }


def main():
    print("[Week 8] Measuring MQTT latency: Direct vs Proxy\n")

    # Measure direct connection to Mosquitto
    print("Measuring direct MQTT latency...")
    direct_result = measure_latency(MQTT_DIRECT_PORT, "direct-mosquitto")

    # Measure through proxy
    print("Measuring proxy MQTT latency...")
    proxy_result = measure_latency(MQTT_PROXY_PORT, "through-proxy")

    # Compute overhead
    overhead_dict = {}
    if "latency_ms" in direct_result and "latency_ms" in proxy_result:
        for key in ["min", "p50", "p95", "p99", "max", "mean"]:
            direct_lat = direct_result["latency_ms"][key]
            proxy_lat = proxy_result["latency_ms"][key]
            overhead = proxy_lat - direct_lat
            overhead_pct = (overhead / direct_lat * 100) if direct_lat > 0 else 0
            overhead_dict[key] = {
                "direct_ms": direct_lat,
                "proxy_ms": proxy_lat,
                "overhead_ms": overhead,
                "overhead_pct": overhead_pct,
            }

    report = {
        "measurement": "mqtt_latency_direct_vs_proxy",
        "iterations": ITERATIONS,
        "direct_result": direct_result,
        "proxy_result": proxy_result,
        "overhead_analysis": overhead_dict,
        "timestamp": time.time(),
    }

    output_path = Path("/tmp/sentrix-week8/latency_analysis.json")
    output_path.write_text(
        __import__("json").dumps(report, indent=2)
    )
    print(f"\nLatency analysis saved to {output_path}")
    print(__import__("json").dumps(overhead_dict, indent=2))


if __name__ == "__main__":
    main()
