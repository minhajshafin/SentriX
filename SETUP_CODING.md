# SentriX Coding Setup (Week 2 Scaffold)

## Repository Layout

- `proxy-core/` — C++ shared proxy framework + protocol module stubs
- `simulators/` — Python benign/attack traffic feature simulators
- `ml-pipeline/` — ML training pipeline workspace (placeholder)
- `dashboard/` — UI workspace (placeholder)
- `deploy/` — Docker Compose stack + backend stubs
- `data/features/` — unified labeled feature dataset output

## 1) Build C++ proxy-core stub

```bash
cd proxy-core
cmake -S . -B build
cmake --build build -j
./build/sentrix_proxy
```

Expected output includes MQTT and CoAP stub start/stop messages.

## 2) Start baseline containers

```bash
cd deploy
docker compose up --build
```

Started services:
- Mosquitto (`1883/tcp`)
- CoAP backend stub (`5683/udp`)
- C++ proxy-core scaffold
- Metrics API stub (`http://localhost:8080/health`)

## 3) Generate unified labeled feature data

Run from repository root:

```bash
python -m simulators.mqtt.mqtt_benign --count 100
python -m simulators.mqtt.mqtt_attacks --count 100
python -m simulators.coap.coap_benign --count 100
python -m simulators.coap.coap_attacks --count 100
```

Output file:
- `data/features/unified_features.csv`

## 4) Immediate next coding steps

1. Replace CoAP backend stub with Californium runtime in `deploy/docker-compose.yml`
2. Add real socket listeners to MQTT/CoAP modules in `proxy-core/src/`
3. Implement Stage 1 rules using normalized fields
4. Add metrics counters and export to `metrics-api`
5. Start baseline dashboard app in `dashboard/`
