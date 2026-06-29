#!/usr/bin/env python3
"""
SentriX Live Detection Experiment Runner
Runs all 6 scenarios through the live proxy and collects detection metrics.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List

EVENTS_LOG = "/tmp/sentrix_events.log"
RESULTS_JSON = "/tmp/sentrix_live_results.json"
REPO_ROOT = Path(__file__).parent.parent

# ── Scenario definitions ──────────────────────────────────────────────────────
SCENARIOS = [
    {
        "name": "benign_mqtt",
        "label": "MQTT Benign",
        "protocol": "mqtt",
        "cmd": [
            sys.executable, "-c",
            """import paho.mqtt.client as mqtt, time
c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id='benign-sensor-01', protocol=mqtt.MQTTv311)
c.connect('127.0.0.1', 1884, keepalive=60)
c.loop_start()
for i in range(30):
    c.publish('sensor/temp', payload=str(22.0 + i*0.1), qos=0)
    time.sleep(0.5)
c.loop_stop(); c.disconnect()
print('benign done: 30 msgs')""",
        ],
        "duration_s": 30,
    },
    {
        "name": "mqtt_publish_flood",
        "label": "MQTT Publish Flood",
        "protocol": "mqtt",
        "cmd": [
            sys.executable, "-m", "simulators.mqtt.mqtt_live_attacks",
            "--attack", "publish_flood", "--count", "100", "--interval-ms", "20",
        ],
        "duration_s": 120,
    },
    {
        "name": "mqtt_wildcard_abuse",
        "label": "MQTT Wildcard Abuse",
        "protocol": "mqtt",
        "cmd": [
            sys.executable, "-m", "simulators.mqtt.mqtt_live_attacks",
            "--attack", "wildcard_abuse", "--count", "50",
        ],
        "duration_s": 30,
    },
    {
        "name": "mqtt_protocol_abuse",
        "label": "MQTT Protocol Abuse",
        "protocol": "mqtt",
        "cmd": [
            sys.executable, "-m", "simulators.mqtt.mqtt_live_attacks",
            "--attack", "malformed", "--count", "40",
        ],
        "duration_s": 30,
    },
    {
        "name": "coap_request_flood",
        "label": "CoAP Request Flood",
        "protocol": "coap",
        "cmd": [
            sys.executable, "-m", "simulators.coap.coap_live_attacks",
            "--attack", "request_flood", "--count", "60",
            "--host", "127.0.0.1", "--port", "5684",
        ],
        "duration_s": 60,
    },
    {
        "name": "coap_protocol_abuse",
        "label": "CoAP Protocol Abuse",
        "protocol": "coap",
        "cmd": [
            sys.executable, "-m", "simulators.coap.coap_live_attacks",
            "--attack", "malformed_burst", "--count", "40",
            "--host", "127.0.0.1", "--port", "5684",
        ],
        "duration_s": 60,
    },
]


def parse_events(log_path: str, protocol_filter: str = None) -> Dict:
    """Parse the events log and return aggregated counters."""
    events: List[dict] = []
    try:
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        return {"total": 0, "drops": 0, "forwards": 0, "rate_limits": 0, "raw": []}

    if protocol_filter:
        events = [e for e in events if e.get("protocol") == protocol_filter]

    drops = [e for e in events if e.get("direction") == "mitigation" and e.get("event") == "drop"]
    forwards = [e for e in events if e.get("direction") == "incoming" and e.get("event") not in ("connection_open",)]
    rate_limits = [e for e in events if e.get("direction") == "mitigation" and e.get("event") == "rate_limit"]

    drop_reasons = Counter(e.get("detail", "unknown") for e in drops)

    return {
        "total_events": len(events),
        "drops": len(drops),
        "forwards": len(forwards),
        "rate_limits": len(rate_limits),
        "drop_reasons": dict(drop_reasons),
    }


def run_scenario(scenario: dict) -> dict:
    """Run one scenario, collect events, return result dict."""
    name = scenario["name"]
    label = scenario["label"]
    protocol = scenario["protocol"]

    print(f"\n{'='*60}")
    print(f"[Scenario] {label}")
    print(f"{'='*60}")

    # Clear log for this scenario
    if os.path.exists(EVENTS_LOG):
        os.remove(EVENTS_LOG)
    time.sleep(0.5)

    # Run the attack/traffic generator
    t_start = time.time()
    print(f"  Running: {' '.join(scenario['cmd'])}")
    try:
        result = subprocess.run(
            scenario["cmd"],
            capture_output=True,
            text=True,
            timeout=scenario["duration_s"],
            cwd=str(REPO_ROOT),
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            print(f"  stdout: {stdout}")
        if stderr and "DeprecationWarning" not in stderr:
            print(f"  stderr: {stderr[:400]}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"  [WARN] Timeout after {scenario['duration_s']}s")
    except Exception as e:
        print(f"  [ERROR] {e}", file=sys.stderr)

    elapsed = time.time() - t_start
    time.sleep(1)  # Let final events flush

    # Parse results
    metrics = parse_events(EVENTS_LOG, protocol_filter=protocol)

    result_dict = {
        "scenario": name,
        "label": label,
        "protocol": protocol,
        "elapsed_s": round(elapsed, 1),
        **metrics,
    }

    print(f"  Done in {elapsed:.1f}s")
    print(f"  Events: drops={metrics['drops']}, forwards={metrics['forwards']}, "
          f"rate_limits={metrics['rate_limits']}")
    if metrics["drop_reasons"]:
        print(f"  Drop reasons: {metrics['drop_reasons']}")

    return result_dict


def compute_detection_rate(result: dict) -> float:
    """For attack scenarios: drop_rate = drops / (drops + forwards).
    For benign: false_positive_rate = drops / (drops + forwards).
    """
    total_actionable = result["drops"] + result["forwards"] + result["rate_limits"]
    if total_actionable == 0:
        return 0.0
    mitigated = result["drops"] + result["rate_limits"]
    return round(mitigated / total_actionable, 4)


def main():
    print("\nSentriX Live Detection Experiment Runner")
    print("=" * 60)
    print(f"Events log: {EVENTS_LOG}")
    print(f"Results:    {RESULTS_JSON}")
    print()

    # Verify proxy is reachable
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", 1884), timeout=2)
        s.close()
        print("[OK] Proxy MQTT port 1884 reachable")
    except Exception as e:
        print(f"[FATAL] Cannot reach proxy on 1884: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for scenario in SCENARIOS:
        res = run_scenario(scenario)
        res["detection_rate"] = compute_detection_rate(res)
        results.append(res)

    # Write JSON results
    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2)

    # Summary table
    print("\n" + "=" * 70)
    print(f"{'Scenario':<28} {'Protocol':<6} {'Drops':>6} {'Fwd':>5} {'Det.Rate':>9}")
    print("-" * 70)
    for r in results:
        print(f"{r['label']:<28} {r['protocol']:<6} {r['drops']:>6} {r['forwards']:>5} {r['detection_rate']:>9.1%}")
    print("=" * 70)
    print(f"\nResults saved to {RESULTS_JSON}")


if __name__ == "__main__":
    main()
