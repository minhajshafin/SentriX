# SentriX 5-Minute Demo Cheatsheet

Use this when you need a fast, high-confidence live demo.

## 0) One-line intro (say this first)

"SentriX is a C++ in-line security proxy for MQTT and CoAP that applies rule-based checks plus ML anomaly scoring on a normalized shared feature space, then decides forward/rate-limit/drop in real time."

## 1) Start Services (3 terminals)

## Terminal A: Backends

```bash
cd /home/billy/X/SentriX/deploy
docker compose up -d mosquitto californium-backend
docker compose ps
```

## Terminal B: Proxy-core

```bash
cd /home/billy/X/SentriX
mkdir -p /tmp/sentrix-week8

cd proxy-core
cmake -S . -B build
cmake --build build -j

SENTRIX_MQTT_BROKER_HOST=127.0.0.1 \
SENTRIX_MQTT_BROKER_PORT=1883 \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 \
SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884 \
SENTRIX_COAP_PROXY_PORT=5684 \
SENTRIX_METRICS_PATH=/tmp/sentrix-week8/metrics.json \
SENTRIX_EVENTS_PATH=/tmp/sentrix-week8/events.jsonl \
SENTRIX_FEATURE_DEBUG_PATH=/tmp/sentrix-week8/features.jsonl \
./build/sentrix_proxy
```

## Terminal C: Metrics API

```bash
cd /home/billy/X/SentriX
node deploy/scripts/metrics_server.js
```

## 2) Quick API Proof (Terminal D)

```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/features/stats | python -m json.tool
```

Say:
- "Health is up."
- "Counters are exposed through API for dashboard and observability."

## 3) Generate MQTT + CoAP Traffic

## MQTT benign

```bash
cd /home/billy/X/SentriX
python proxy-core/scripts/week8_benign_scenario.py
```

## CoAP benign + attack-like

```bash
python -m simulators.coap.coap_live_benign --host 127.0.0.1 --port 5684 --count 20
python -m simulators.coap.coap_live_attacks --host 127.0.0.1 --port 5684 --attack request_flood --count 40
```

## 4) Show What Changed (proof of working)

```bash
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/features/stats | python -m json.tool
head -1 /tmp/sentrix-week8/features.jsonl | python -m json.tool
```

What to point to:
- `mqtt_msgs` increased.
- `coap_msgs` increased.
- `total_vectors` increased.
- JSON row contains `behavioral` features + `decision.anomaly_score` + `decision.action`.

## 5) 40-second architecture explanation

- Protocol modules (MQTT/CoAP) parse native traffic.
- Shared normalization maps behavior to a 33D vector.
- Stage-1 rules catch obvious abuse.
- Stage-2 ML scores anomaly.
- Stage-3 mitigation decides `forward`, `rate_limit`, or `drop`.
- Metrics and vectors are exported for live monitoring and offline analysis.

## 6) 4 likely viva questions (short answers)

## Q1: What is your novelty?

A single protocol-preserving in-line proxy that unifies MQTT and CoAP detection in one shared behavioral feature framework, without broker modification or protocol translation.

## Q2: Why LightGBM?

Best/tied-best result with practical deployment efficiency; selected for robust performance and low inference overhead.

## Q3: Main finding?

Strong within-protocol detection, weak zero-shot cross-protocol transfer; quantified as a significant generalization gap.

## Q4: Current limitations?

Cross-protocol adaptation, larger live-scale testing, and formal throughput/latency benchmarking under heavy load.

## 7) If dashboard is needed (optional)

```bash
cd /home/billy/X/SentriX/dashboard
npm run dev
```

Open `http://localhost:3000`

## 8) Clean shutdown

- Ctrl+C in proxy terminal
- Ctrl+C in metrics API terminal
- Then:

```bash
cd /home/billy/X/SentriX/deploy
docker compose down
```

## 9) One-line close (say this)

"This demo showed live dual-protocol interception, feature extraction, ML-based decisioning, and real-time observability, which validates the end-to-end SentriX architecture."