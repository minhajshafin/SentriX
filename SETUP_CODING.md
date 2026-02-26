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
- MQTT ingress via proxy-core (`1884/tcp`)
- Mosquitto backend (`1883/tcp`, internal)
- Californium backend (`5683/udp`)
- C++ proxy-core scaffold
- Metrics API stub (`http://localhost:8080/health`)
- Event feed API (`http://localhost:8080/events`)

## 2.1) Run the dashboard

```bash
cd dashboard
cp .env.example .env.local
npm install
npm run dev
```

Dashboard URL:
- `http://localhost:3000`

The dashboard fetches metrics from `NEXT_PUBLIC_METRICS_BASE_URL` (default: `http://localhost:8080`).

## 2.2) Verify MQTT pass-through + live counters

Publish test MQTT messages to the proxy ingress (`1884`):

```bash
python - <<'PY'
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc, properties=None):
	if rc == 0:
		for i in range(10):
			client.publish("sensors/temp", payload=f"sentrix-{i}", qos=0)
	client.disconnect()

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
c.on_connect = on_connect
c.connect("127.0.0.1", 1884, 30)
c.loop_forever(timeout=2.0)
PY
```

Check counters:

```bash
curl http://localhost:8080/metrics
```

`mqtt_msgs` should increase after each publish batch.

## 2.3) View timestamped security event tracker

- Open dashboard at `http://localhost:3000`
- The **Security Event Tracker** panel shows recent events with timestamp, protocol, direction, event type, and byte count.
- Raw event feed is available at:

```bash
curl http://localhost:8080/events | python -m json.tool | head -n 60
```

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
2. Implement CoAP UDP pass-through in `proxy-core/src/coap/coap_module.cpp`
3. Implement Stage 1 rules using normalized fields
4. Extend metrics counters (per-action/per-attack)
5. Connect dashboard charts to time-series metrics
