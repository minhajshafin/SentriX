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

### 1.1) Run `sentrix_proxy` on host (outside Docker)

If you run the binary directly on your machine, use localhost backend targets (Docker service names are not resolvable on host):

```bash
cd deploy
docker compose up -d mosquitto californium-backend metrics-api-stub

cd ../proxy-core/build
SENTRIX_MQTT_BROKER_HOST=127.0.0.1 \
SENTRIX_MQTT_BROKER_PORT=1883 \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 \
SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884 \
SENTRIX_COAP_PROXY_PORT=5684 \
SENTRIX_METRICS_PATH=/tmp/sentrix_metrics.json \
SENTRIX_EVENTS_PATH=/tmp/sentrix_events.log \
./sentrix_proxy
```

In this mode:
- MQTT ingress is `localhost:1884`
- CoAP ingress is `localhost:5684/udp`

> Do not run host `./sentrix_proxy` and Docker `proxy-core` at the same time on the same ports (`1884`, `5684`).
> Pick one mode:
> - **Docker mode**: dashboard + metrics use container `proxy-core`
> - **Host mode**: dashboard will not reflect host proxy metrics unless API is also pointed to host files

## 2) Start baseline containers

```bash
cd deploy
docker compose up --build
```

Started services:
- MQTT ingress via proxy-core (`1884/tcp`)
- Mosquitto backend (`1883/tcp`, internal)
- CoAP ingress via proxy-core (`5684/udp`)
- Californium backend (`5683/udp`, internal)
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

If MQTT messages do not show on dashboard:

```bash
cd deploy
docker compose ps -a
docker compose up -d proxy-core
curl http://localhost:8080/metrics
```

`proxy-core` must be `Up` (not `Created`/`Exited`).

## 2.3) View timestamped security event tracker

- Open dashboard at `http://localhost:3000`
- The **Security Event Tracker** panel shows recent events with timestamp, protocol, direction, event type, and byte count.
- Raw event feed is available at:

```bash
curl http://localhost:8080/events | python -m json.tool | head -n 60
```

## 2.4) Verify CoAP pass-through + live counters

Generate benign CoAP traffic through proxy ingress (`5684`):

```bash
python -m simulators.coap.coap_live_benign --host 127.0.0.1 --port 5684 --count 20
```

Generate attack-like CoAP traffic:

```bash
python -m simulators.coap.coap_live_attacks --host 127.0.0.1 --port 5684 --attack request_flood --count 80
```

Check counters:

```bash
curl http://localhost:8080/metrics
```

`coap_msgs` should increase after CoAP traffic runs.

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

## 3.1) Export live protocol-tagged proxy events to dataset CSV

```bash
python ml-pipeline/src/export_events_to_dataset.py \
	--events-api http://localhost:8080/events \
	--out data/raw/proxy_events.csv \
	--run-id MQ-BENIGN-R1 \
	--scenario mqtt_benign \
	--label benign \
	--rep 1
```

For additional runs, append to the same output file:

```bash
python ml-pipeline/src/export_events_to_dataset.py \
	--events-api http://localhost:8080/events \
	--out data/raw/proxy_events.csv \
	--run-id CP-FLOOD-R1 \
	--scenario coap_request_flood \
	--label coap_request_flood \
	--rep 1 \
	--append
```

Output file:
- `data/raw/proxy_events.csv`

## 4) Immediate next coding steps

1. Implement protocol-specific parsing and feature extraction for live CoAP events
2. Implement Stage 1 CoAP-specific rule checks in proxy path
3. Implement Stage 1 rules using normalized fields
4. Extend metrics counters (per-action/per-attack)
5. Connect dashboard charts to time-series metrics
