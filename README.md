# SentriX

Middleware-independent, multi-stage IoT security proxy for heterogeneous protocols (MQTT and CoAP), with protocol-normalized feature extraction, ML-based anomaly scoring, and real-time mitigation.

## What This Project Is

SentriX is an inline reverse-proxy security architecture designed for IoT traffic inspection without modifying backend middleware.

Core idea:
- Parse protocol-native traffic (MQTT/CoAP)
- Normalize behavior into a shared feature space
- Run staged detection (rules + ML)
- Apply mitigation decisions (`forward`, `rate_limit`, `drop`)
- Export runtime metrics/events for monitoring and analysis

## High-Level Architecture

Traffic flow:
- Clients -> SentriX proxy ingress (`1884/tcp` for MQTT, `5684/udp` for CoAP)
- SentriX protocol modules parse and extract features
- Detection pipeline scores anomaly and decides action
- Forwarded traffic goes to native backends (`1883/tcp` Mosquitto, `5683/udp` Californium)
- Metrics/events are written and exposed via API + dashboard

Main components:
- [proxy-core](proxy-core): C++17 proxy and detection runtime
- [ml-pipeline](ml-pipeline): dataset processing, model training, statistical analysis, figure generation
- [simulators](simulators): MQTT/CoAP benign and attack traffic generation
- [deploy](deploy): Docker Compose testbed (brokers, proxy, metrics API)
- [dashboard](dashboard): Next.js monitoring UI
- [Research_Paper](Research_Paper): manuscript artifacts

## Repository Structure

Top-level layout:
- [config](config): feature schema and configuration docs
- [data](data): raw/labeled datasets and processed outputs
- [deploy](deploy): containers and runtime stack
- [dashboard](dashboard): monitoring frontend
- [ml-pipeline](ml-pipeline): ML lifecycle scripts and reports
- [proxy-core](proxy-core): C++ runtime implementation
- [simulators](simulators): synthetic traffic and scenarios

## Quick Start (Recommended: Docker Backends + Host Tooling)

### 1) Start infrastructure

```bash
cd deploy
docker compose up -d mosquitto californium-backend metrics-api-stub
docker compose ps
```

### 2) Build and run proxy core (host)

```bash
cd ../proxy-core
cmake -S . -B build
cmake --build build -j

SENTRIX_MQTT_BROKER_HOST=127.0.0.1 \
SENTRIX_MQTT_BROKER_PORT=1883 \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 \
SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884 \
SENTRIX_COAP_PROXY_PORT=5684 \
SENTRIX_METRICS_PATH=/tmp/sentrix_metrics.json \
SENTRIX_EVENTS_PATH=/tmp/sentrix_events.log \
./build/sentrix_proxy
```

### 3) Start dashboard

```bash
cd ../dashboard
npm install
npm run dev
```

Open:
- Dashboard: `http://localhost:3000`
- Metrics API: `http://localhost:8080/metrics`
- Health: `http://localhost:8080/health`

### 4) Validate live counters

```bash
curl http://localhost:8080/metrics
curl http://localhost:8080/events | python -m json.tool | head -n 40
```

## Full Stack via Docker Compose

Run everything from [deploy](deploy):

```bash
cd deploy
docker compose up --build
```

Services defined in [deploy/docker-compose.yml](deploy/docker-compose.yml):
- `mosquitto` on `1883/tcp`
- `californium-backend` on `5683/udp`
- `proxy-core` on `1884/tcp` and `5684/udp`
- `metrics-api-stub` on `8080/tcp`

## Machine Learning Workflow

Pipeline summary:
- Generate/collect labeled events
- Validate feature quality and drift
- Train baselines (`logreg`, `random_forest`, `mlp`, `lightgbm`)
- Select champion model
- Export ONNX for runtime inference
- Run statistical tests and generate paper figures

Key scripts:
- [ml-pipeline/src/export_events_to_dataset.py](ml-pipeline/src/export_events_to_dataset.py)
- [ml-pipeline/src/validate_feature_quality.py](ml-pipeline/src/validate_feature_quality.py)
- [ml-pipeline/src/train_baselines.py](ml-pipeline/src/train_baselines.py)
- [ml-pipeline/src/week6_train_champion.py](ml-pipeline/src/week6_train_champion.py)
- [ml-pipeline/src/week6_export_onnx.py](ml-pipeline/src/week6_export_onnx.py)
- [ml-pipeline/src/week11_statistical_analysis.py](ml-pipeline/src/week11_statistical_analysis.py)
- [ml-pipeline/src/week11_generate_figures.py](ml-pipeline/src/week11_generate_figures.py)

Run baseline training:

```bash
source .venv/bin/activate
python ml-pipeline/src/train_baselines.py
```

Expected core artifact examples:
- [ml-pipeline/reports/week5_baseline_metrics.csv](ml-pipeline/reports/week5_baseline_metrics.csv)
- [ml-pipeline/models/lightgbm_full.onnx](ml-pipeline/models/lightgbm_full.onnx)

## Data and Features

Primary labeled dataset:
- [data/raw/proxy_events_labeled.csv](data/raw/proxy_events_labeled.csv)

Unified feature schema:
- 33 dimensions total
- shared behavioral features + protocol encoding + protocol-specific auxiliaries
- schema reference: [config/feature_schema.md](config/feature_schema.md)

## Typical Development Commands

Build proxy core:

```bash
cd proxy-core
cmake -S . -B build
cmake --build build -j
```

Run metrics server (host mode):

```bash
node deploy/scripts/metrics_server.js
```

Run dashboard:

```bash
cd dashboard
npm run dev
```

Generate baseline traffic:

```bash
python proxy-core/scripts/week8_benign_scenario.py
```

## Notes

- Do not run host proxy and Docker `proxy-core` simultaneously on the same ports (`1884`, `5684`).
- In host mode, use `127.0.0.1` for backend endpoints; Docker service names are not resolvable on host.
- For production-like runs, prefer containerized deployment and pinned package versions.

