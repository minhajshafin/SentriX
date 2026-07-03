# SentriX

**SentriX** is a middleware-independent, multi-stage security proxy for heterogeneous IoT protocols. It sits inline between IoT clients and backend brokers — parsing MQTT and CoAP traffic, extracting behavioral features, running staged detection (rule engine → ML anomaly scorer → mitigation engine), and enforcing drop/rate-limit/forward decisions in real time.

No broker modification. No protocol translation. Sub-millisecond latency overhead.

---

## Key Capabilities

| Capability | Detail |
|---|---|
| **Protocols** | MQTT v3.1.1 (TCP) · CoAP RFC 7252 (UDP) |
| **Detection stages** | Rule engine → ONNX ML inference → Mitigation |
| **Feature space** | 33-dimensional normalized behavioral vector (shared across protocols) |
| **Champion model** | LightGBM — Accuracy 0.780, macro-F1 0.598 |
| **Live latency overhead** | +0.306 ms mean per packet |
| **Live false-positive rate** | 0% on benign traffic (behavioral windows enabled) |
| **Dataset** | 11,209 labeled records · 21 experimental runs · 6 classes |
| **Deployment** | Docker Compose (backends) + host binary (proxy) |
| **Dashboard** | Next.js real-time monitoring UI |

---

## Repository Layout

```
SentriX/
├── proxy-core/          # C++17 proxy and detection runtime
│   ├── src/
│   │   ├── common/      # main, proxy_core, detection_pipeline, feature_mapping, event_log, metrics_store
│   │   ├── mqtt/        # MqttModule — TCP ingress, MQTT frame parser
│   │   └── coap/        # CoapModule — UDP ingress, CoAP datagram parser
│   ├── include/sentrix/ # Public headers for all modules
│   └── third_party/     # onnxruntime headers
│
├── ml-pipeline/         # Python ML lifecycle
│   ├── src/             # Training, ONNX export, statistical analysis, figure generation
│   └── models/          # lightgbm_full.onnx (champion model)
│
├── simulators/          # Traffic generation
│   ├── mqtt/            # Paho-based MQTT benign + attack generators
│   ├── coap/            # aiocoap-based CoAP benign + attack generators
│   └── live_experiment_runner.py  # Orchestrates all live scenarios
│
├── data/                # Dataset artifacts
│   ├── raw/             # week3_runs_labeled.csv (primary dataset)
│   └── DATASET_README.md
│
├── deploy/              # Docker Compose infrastructure
│   ├── docker-compose.yml
│   ├── mosquitto.conf
│   └── californium/     # Californium CoAP backend container
│
├── dashboard/           # Next.js monitoring frontend
│   └── src/
│
├── docs/                # Extended documentation
│   ├── ARCHITECTURE.md  # Deep technical design
│   └── DEVELOPMENT.md   # Setup and dev workflow
│
└── Research_Paper/      # Conference manuscript
    └── main.tex         # IEEE CCNC 2026 submission (6 pages)
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- C++17 compiler (GCC 11+ or Clang 14+) · CMake 3.18+
- Python 3.10+ · Node.js 18+

### 1 — Start backend infrastructure

```bash
cd deploy
docker compose up -d mosquitto californium-backend metrics-api-stub
```

Services started:
- `mosquitto` — MQTT broker on `localhost:1883`
- `californium-backend` — CoAP server on `localhost:5683`
- `metrics-api-stub` — REST metrics API on `localhost:8080`

### 2 — Build and run the proxy

```bash
cd proxy-core
cmake -S . -B build_debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build_debug -j$(nproc)

SENTRIX_MQTT_BROKER_HOST=127.0.0.1  SENTRIX_MQTT_BROKER_PORT=1883  \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884        SENTRIX_COAP_PROXY_PORT=5684   \
SENTRIX_METRICS_PATH=/tmp/sentrix_metrics.json                      \
SENTRIX_EVENTS_PATH=/tmp/sentrix_events.log                         \
SENTRIX_ENABLE_BEHAVIORAL_WINDOWS=1                                  \
./build_debug/sentrix_proxy
```

The proxy listens on:
- `localhost:1884` (MQTT ingress from clients)
- `localhost:5684` (CoAP ingress from clients)

### 3 — Run the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:3000`

### 4 — Generate test traffic

```bash
# Benign MQTT (1 msg/s for 30 messages)
python3 -m simulators.mqtt.mqtt_live_attacks --attack publish_flood --count 30 --interval-ms 1000

# Attack: MQTT publish flood
python3 -m simulators.mqtt.mqtt_live_attacks --attack publish_flood --count 100 --interval-ms 20

# Run all 6 scenarios + benign baseline
python3 simulators/live_experiment_runner.py
```

---

## Detection Architecture

```
Client → [Proxy Ingress]
              │
              ▼
    [Feature Extraction]      ← behavioral windows, normalization
              │
              ▼
    ┌─[Stage 1: Rule Engine]
    │   msg_rate > 0.95  →  DROP
    │   payload_size > 0.97 →  DROP
    └─ else → Stage 2
              │
              ▼
    ┌─[Stage 2: ONNX Inference]
    │   anomaly_score > 0.90  →  DROP
    │   anomaly_score > 0.75  →  RATE_LIMIT
    └─ else → FORWARD
              │
              ▼
    [Mitigation Engine] → Backend Broker
              │
              ▼
    [Event Log + Metrics Store]
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical deep-dive.

---

## Live Experiment Results

Experiments run against the live proxy with `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS=1`:

| Scenario | Protocol | Drops | Forwarded | Stage-1 Rate |
|---|---|---|---|---|
| Benign baseline | MQTT | 0 | 31 | **0.0% FP** |
| Publish flood | MQTT | 58 | 19 | 75.3% |
| Wildcard abuse | MQTT | 81 | 19 | 81.0% |
| Protocol abuse (malformed) | MQTT | 0 | 12 | Needs Stage 2 |
| Request flood | CoAP | 3 | 60 | 4.8% |
| Protocol abuse | CoAP | 2 | 40 | Needs Stage 2 |

Stage 1 catches high-rate attacks at zero ML cost. Protocol-abuse and sequential CoAP attacks require Stage 2 ONNX inference.

---

## Environment Variables

All proxy configuration is via environment variables at startup:

| Variable | Default | Description |
|---|---|---|
| `SENTRIX_MQTT_BROKER_HOST` | `127.0.0.1` | Upstream MQTT broker address |
| `SENTRIX_MQTT_BROKER_PORT` | `1883` | Upstream MQTT broker port |
| `SENTRIX_MQTT_PROXY_PORT` | `1884` | MQTT ingress port (clients connect here) |
| `SENTRIX_COAP_BACKEND_HOST` | `127.0.0.1` | Upstream CoAP server address |
| `SENTRIX_COAP_BACKEND_PORT` | `5683` | Upstream CoAP server port |
| `SENTRIX_COAP_PROXY_PORT` | `5684` | CoAP ingress port |
| `SENTRIX_METRICS_PATH` | `/tmp/sentrix_metrics.json` | Metrics snapshot output path |
| `SENTRIX_EVENTS_PATH` | `/tmp/sentrix_events.log` | Per-packet event log (JSONL) |
| `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS` | _(unset)_ | Set to `1` to enable stateful normalization |
| `SENTRIX_ONNX_MODEL_PATH` | _(unset)_ | Path to `.onnx` model file |
| `SENTRIX_RULE_MSG_RATE_THRESHOLD` | `0.95` | Stage 1 rate drop threshold |
| `SENTRIX_RULE_PAYLOAD_THRESHOLD` | `0.97` | Stage 1 payload size drop threshold |
| `SENTRIX_INFERENCE_DROP_THRESHOLD` | `0.90` | Stage 2 anomaly score → DROP |
| `SENTRIX_INFERENCE_RATE_LIMIT_THRESHOLD` | `0.75` | Stage 2 anomaly score → RATE_LIMIT |

---

## Notes

- Do not run host proxy and Docker `proxy-core` container simultaneously (port conflicts on 1884/5684).
- The `Debug` build is stable and recommended; the `Release` build has known initialization issues.
- Without `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS=1`, the proxy falls back to `legacyNormalize` which sets `msg_rate=1.0` for all traffic events, causing all packets to trigger Stage 1 drops.
- Without `SENTRIX_ONNX_MODEL_PATH`, Stage 2 falls back to a heuristic scorer.

---

## Dataset and Paper

- Dataset: [`data/DATASET_README.md`](data/DATASET_README.md) · Zenodo DOI: TBD
- Conference paper: [`Research_Paper/main.tex`](Research_Paper/main.tex) — IEEE CCNC 2026 submission
