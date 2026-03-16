# SentriX Demo + Viva Guide (Professor Presentation)

This guide is for a live manual demonstration of your project and for answering viva questions confidently.

## 1) 30-Second Project Pitch

SentriX is a middleware-independent, multi-stage IoT security proxy for **MQTT** and **CoAP**.
It sits between clients and backend servers, extracts protocol-aware features, normalizes them to a shared 33-dimensional vector, and applies:
1. fast rules,
2. ML anomaly scoring,
3. protocol-aware mitigation.

Key outcomes to highlight:
- End-to-end C++ proxy integration is complete.
- 11,209 labeled observations used in evaluation.
- LightGBM best model: F1-macro 0.5977.
- Live runtime test (n=101) showed 0 false positives at threshold 0.75.

## 2) Architecture (How It Works)

## 2.1 Components

- `proxy-core/` (C++): MQTT + CoAP proxy modules and shared detection pipeline.
- `deploy/`: Mosquitto broker and Californium CoAP backend in Docker.
- `deploy/scripts/metrics_server.js`: API that serves runtime metrics and feature stats.
- `dashboard/`: Next.js monitoring UI.
- `ml-pipeline/`: model training, figures, statistical analysis.

## 2.2 Data Flow

1. Client sends MQTT/CoAP traffic to SentriX proxy.
2. Protocol module parses message and extracts behavior features.
3. Features normalized into a shared vector.
4. Stage-1 rules check obvious anomalies.
5. Stage-2 inference computes anomaly score.
6. Stage-3 chooses action: `forward`, `rate_limit`, or `drop`.
7. Metrics and feature vectors are written to disk.
8. Metrics API + dashboard display live status.

## 2.3 Detection Pipeline Logic (important for viva)

- Rule thresholds (default):
  - message-rate rule: `0.95`
  - payload-size rule: `0.97`
- Inference thresholds (default):
  - `>= 0.90` -> `drop`
  - `>= 0.75` -> `rate_limit`
  - below `0.75` -> `forward`

## 3) Pre-Demo Checklist (2 minutes)

Run from repo root `/home/billy/X/SentriX`.

- Docker is running.
- Python venv exists and can be activated.
- Node/npm works for dashboard.
- Ports free: `1883`, `1884`, `5683/udp`, `5684/udp`, `8080`, `3000`.

Quick checks:

```bash
docker --version
node --version
npm --version
python --version
```

## 4) Live Demo Script (Step-by-Step)

Use multiple terminals so your professor sees system pieces clearly.

## 4.1 Terminal A: Start backends (Mosquitto + CoAP)

```bash
cd deploy
docker compose up -d mosquitto californium-backend
docker compose ps
```

Expected:
- `sentrix-mosquitto` is `Up`
- `sentrix-coap-backend` is `Up`

## 4.2 Terminal B: Build and run C++ proxy manually

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

Expected logs:
- Detection runtime config line
- MQTT module listening on `1884`
- CoAP module listening on `5684`

## 4.3 Terminal C: Start metrics API

```bash
cd /home/billy/X/SentriX
node deploy/scripts/metrics_server.js
```

Expected:
- API on `http://localhost:8080`
- Endpoints:
  - `/metrics`
  - `/features/stats`
  - `/health`

## 4.4 Terminal D: Start dashboard

```bash
cd /home/billy/X/SentriX/dashboard
npm install
npm run dev
```

Open: `http://localhost:3000`

## 4.5 Terminal E: Baseline health check (before traffic)

```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics
curl http://localhost:8080/features/stats
```

What to say:
- "System is up, and counters are currently near zero."

## 4.6 Generate MQTT traffic and show live updates

```bash
cd /home/billy/X/SentriX
python proxy-core/scripts/week8_benign_scenario.py
```

Then verify:

```bash
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/features/stats | python -m json.tool
```

What to point out:
- `mqtt_msgs` increases.
- `total_vectors` increases.
- Anomaly statistics appear.

## 4.7 Generate CoAP traffic and show dual-protocol behavior

```bash
cd /home/billy/X/SentriX
python -m simulators.coap.coap_live_benign --host 127.0.0.1 --port 5684 --count 30
python -m simulators.coap.coap_live_attacks --host 127.0.0.1 --port 5684 --attack request_flood --count 60
```

Then verify again:

```bash
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/features/stats | python -m json.tool
```

What to point out:
- `coap_msgs` also increases.
- `by_protocol.mqtt` and `by_protocol.coap` both non-zero.

## 4.8 Show actual feature vectors + decisions (proof of pipeline)

```bash
head -1 /tmp/sentrix-week8/features.jsonl | python -m json.tool
```

Explain this JSON live:
- `protocol`, `event_type`, `behavioral`, `active`, `decision.anomaly_score`, `decision.action`.

## 4.9 Show evaluation artifacts (offline science proof)

```bash
cat ml-pipeline/reports/week11_statistical_analysis.json | head -n 80
ls -1 ml-pipeline/figures
```

Key points to mention:
- Best model and confidence interval.
- Significant differences (or ties) between baselines.
- Cross-protocol gap quantified.

## 5) Recommended Talk Track (What To Say While Running)

## 5.1 During startup

- "I am starting protocol backends first, then the C++ proxy, then monitoring services."
- "This separation shows edge deployment without broker modification."

## 5.2 During traffic generation

- "Now I send MQTT benign traffic through port 1884."
- "Now I send CoAP traffic through port 5684."
- "Counters and feature vectors increase in real time, proving live capture and processing."

## 5.3 During feature JSON explanation

- "This row represents one runtime event transformed into model-ready features."
- "The detection engine outputs anomaly score and mitigation decision per event."

## 5.4 During results explanation

- "Within-protocol learning is strong, but zero-shot cross-protocol transfer is weak."
- "This is the major research finding and future work direction."

## 6) Common Viva Questions + Good Answers

## 6.1 Why two protocols (MQTT and CoAP)?

They represent dominant but different IoT communication styles: MQTT (brokered TCP pub/sub) and CoAP (UDP request/response + observe). This makes cross-protocol security non-trivial and meaningful.

## 6.2 What is your main novelty?

A protocol-normalized feature framework with one shared detection pipeline, implemented in a standalone C++ in-line proxy without broker modification or protocol translation.

## 6.3 Why not just use Snort/Suricata?

Network IDS tools are packet/flow oriented and often miss higher-level protocol semantics used by MQTT/CoAP abuse patterns. SentriX operates at protocol-aware behavioral level.

## 6.4 Why LightGBM?

It provided best or tied-best performance with low inference overhead and practical deployability compared to larger models.

## 6.5 Why is cross-protocol transfer weak?

Even after normalization, protocol-specific semantics and transport behavior (TCP vs UDP) remain. Statistical analysis and feature drift confirm this mismatch.

## 6.6 What does multi-stage mean here?

Stage 1: rules for obvious anomalies.
Stage 2: ML anomaly scoring.
Stage 3: mitigation decision (`forward`, `rate_limit`, `drop`).

## 6.7 How do you avoid false positives?

Conservative thresholds and layered decisions. In live benign runtime evaluation (n=101), false positives were zero at threshold 0.75.

## 6.8 Why no protocol translation?

Translation can break protocol guarantees and adds risk in security-critical in-line paths. SentriX preserves native protocol behavior.

## 6.9 Can this scale?

Architecture is modular and edge-friendly, but formal throughput/latency benchmarking under high load is still future work.

## 6.10 What are current limitations?

- Cross-protocol generalization gap.
- Limited live sample size.
- No head-to-head benchmark against deployed production IDS in this version.

## 6.11 What is the future work?

Domain adaptation for cross-protocol transfer, stress/load benchmarking, adding more protocols (AMQP/LwM2M/OPC-UA), and larger real-world datasets.

## 6.12 Why C++ for proxy-core?

Low-latency in-line packet handling, fine-grained control over sockets, and production-friendly performance profile.

## 7) Likely Professor Concerns (and how to answer honestly)

- Concern: "Sample size for live evaluation is small."
  - Response: Correct. We reported it transparently and framed it as integration validation, not final production claim.

- Concern: "Cross-protocol transfer is weak."
  - Response: Yes, and that is a key scientific result. We quantified the gap and identified candidate adaptation methods.

- Concern: "Is this only simulation?"
  - Response: It includes simulation for controlled labeling plus live in-line proxy runs with real network traffic paths and runtime telemetry.

## 8) Fast Troubleshooting During Demo

- `curl /metrics` not changing:
  - Ensure proxy is running.
  - Ensure traffic sent to proxy ports (`1884`, `5684`) not backend ports.
  - Check metrics path matches `/tmp/sentrix-week8/metrics.json`.

- Dashboard not updating:
  - Verify metrics API is running on `8080`.
  - Check `http://localhost:8080/health`.

- Port conflict on proxy start:
  - Stop any old process binding `1884` or `5684`.

- CoAP traffic fails:
  - Ensure `californium-backend` container is up.
  - Ensure UDP port mapping `5683/5684` is available.

## 9) Clean Shutdown

- Stop proxy (Ctrl+C in Terminal B)
- Stop metrics API (Ctrl+C in Terminal C)
- Stop dashboard (Ctrl+C in Terminal D)
- Stop containers:

```bash
cd /home/billy/X/SentriX/deploy
docker compose down
```

## 10) One-Minute Final Closing Line

"SentriX demonstrates that a protocol-preserving edge proxy can unify security reasoning across MQTT and CoAP in one deployable pipeline. The system is fully integrated and reproducible, with strong within-protocol detection and a clearly quantified cross-protocol research challenge."