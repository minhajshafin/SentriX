# SentriX Proxy Core

SentriX Proxy Core is the C++17 inline security runtime for the SentriX project. It sits in front of native MQTT and CoAP backends, parses protocol traffic, extracts behavior features, evaluates detection rules and inference, and applies mitigation decisions in real time.

This README is specific to the proxy-core package. For the full repository overview, see [../README.md](../README.md). For ML workflow details, see [../ml-pipeline/README.md](../ml-pipeline/README.md). For setup instructions, see [../SETUP_CODING.md](../SETUP_CODING.md).

## What Proxy Core Does

Proxy core is responsible for:

- Accepting MQTT client connections on a TCP ingress port
- Accepting CoAP datagrams on a UDP ingress port
- Forwarding traffic to the appropriate backend broker/server
- Parsing protocol-native messages into a common internal event model
- Computing raw, legacy, and behavioral feature vectors
- Running a two-stage detection flow:
	- rule checks
	- anomaly scoring and mitigation
- Writing runtime metrics and event logs to disk
- Optionally exporting feature-debug JSONL records for offline analysis

## Architecture

The runtime is intentionally simple:

1. `main.cpp` creates a `ProxyCore` instance.
2. MQTT and CoAP modules are registered.
3. Each module starts its own listener / I/O loop.
4. Incoming traffic is parsed into `ProtocolEvent`.
5. Features are extracted and normalized into a 33-dimensional vector.
6. The detection pipeline evaluates rules and scores anomaly.
7. The mitigation engine chooses `forward`, `rate_limit`, or `drop`.
8. Metrics, events, and optional feature-debug records are flushed to disk.

### Data Flow

```text
MQTT client -> MQTT proxy port -> MQTT module -> feature map -> detection -> broker
CoAP client  -> CoAP proxy port  -> CoAP module  -> feature map -> detection -> backend
```

### Key Runtime Artifacts

- Metrics snapshot: `/tmp/sentrix_metrics.json` by default
- Event log: `/tmp/sentrix_events.log` by default
- Feature debug log: optional path set by `SENTRIX_FEATURE_DEBUG_PATH`

## Source Layout

```text
proxy-core/
├── CMakeLists.txt
├── include/sentrix/
│   ├── coap_module.hpp
│   ├── detection_pipeline.hpp
│   ├── event_log.hpp
│   ├── feature_debug.hpp
│   ├── feature_mapping.hpp
│   ├── feature_vector.hpp
│   ├── metrics_store.hpp
│   ├── mqtt_module.hpp
│   ├── protocol_module.hpp
│   └── proxy_core.hpp
├── src/common/
│   ├── detection_pipeline.cpp
│   ├── event_log.cpp
│   ├── feature_debug.cpp
│   ├── feature_mapping.cpp
│   ├── main.cpp
│   ├── metrics_store.cpp
│   └── proxy_core.cpp
├── src/mqtt/mqtt_module.cpp
├── src/coap/coap_module.cpp
├── scripts/
│   ├── week7_smoke_validation.py
│   ├── week8_benign_scenario.py
│   ├── week8_attack_scenario.py
│   ├── week8_latency_analysis.py
│   ├── week8_feature_drift_analysis.py
│   ├── week9_coap_integration.py
│   ├── week9_combined_protocol.py
│   ├── week10_analyze_features.py
│   ├── week10_coap_stress.py
│   ├── week10_mqtt_stress.py
│   ├── week10_mqtt_stress_direct.py
│   └── week10_mqtt_stress_simple.py
└── build/
		└── sentrix_proxy
```

## Build Requirements

### Required

- CMake 3.16+
- C++17 compiler such as GCC or Clang
- POSIX sockets and threading support

### Optional

- ONNX Runtime C++ SDK, if you want ONNX inference enabled at compile time

## Build

### Standard build

```bash
cd /home/billy/X/SentriX/proxy-core
cmake -S . -B build
cmake --build build -j
```

### Build with ONNX Runtime support

The build system enables ONNX integration when `SENTRIX_ENABLE_ONNX_RUNTIME=ON` is passed to CMake.

```bash
cd /home/billy/X/SentriX/proxy-core
cmake -S . -B build-onnx -DSENTRIX_ENABLE_ONNX_RUNTIME=ON
cmake --build build-onnx -j
```

If ONNX Runtime is enabled, the build looks for headers and libraries in:

- `$ONNXRUNTIME_ROOT/include`
- `$ONNXRUNTIME_ROOT/lib`
- `third_party/onnxruntime/include`
- `third_party/onnxruntime/lib`
- system include/library paths

If the SDK cannot be found, configuration fails early with a CMake error.

### Compiler warnings

When building with GCC or Clang, the binary is compiled with:

- `-Wall`
- `-Wextra`
- `-Wpedantic`

## Runtime Configuration

Proxy core is configured through environment variables. Defaults are shown in parentheses.

### MQTT

- `SENTRIX_MQTT_PROXY_PORT` (1884)
- `SENTRIX_MQTT_BROKER_HOST` (`mosquitto` in Docker, or `127.0.0.1` in host mode)
- `SENTRIX_MQTT_BROKER_PORT` (1883)

### CoAP

- `SENTRIX_COAP_PROXY_PORT` (5684)
- `SENTRIX_COAP_BACKEND_HOST` (`californium-backend` in Docker, or `127.0.0.1` in host mode)
- `SENTRIX_COAP_BACKEND_PORT` (5683)

### Logging and debug output

- `SENTRIX_METRICS_PATH` (`/tmp/sentrix_metrics.json`)
- `SENTRIX_EVENTS_PATH` (`/tmp/sentrix_events.log`)
- `SENTRIX_FEATURE_DEBUG_PATH` (disabled if unset)

### Detection thresholds

All thresholds are unit-bounded floats in the range [0, 1].

- `SENTRIX_RULE_MSG_RATE_THRESHOLD` (0.95)
- `SENTRIX_RULE_PAYLOAD_THRESHOLD` (0.97)
- `SENTRIX_INFERENCE_DROP_THRESHOLD` (0.90)
- `SENTRIX_INFERENCE_RATE_LIMIT_THRESHOLD` (0.75)

### ONNX inference

- `SENTRIX_ONNX_MODEL_PATH` points to the ONNX model file when ONNX Runtime support is compiled in

### Behavioral feature mode

- `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS`

If enabled, the runtime uses the stateful behavioral feature path instead of the legacy normalization path. If unset, proxy core defaults to the legacy feature mapping.

## Feature Model

Proxy core exposes a 33-dimensional normalized vector:

- 15 shared behavioral features
- 2 protocol ID slots
- 8 MQTT auxiliary features
- 8 CoAP auxiliary features

### Feature vector ordering

- `f00` to `f14`: shared behavioral features
- `f15` to `f16`: protocol ID one-hot encoding
- `f17` to `f24`: MQTT auxiliary features
- `f25` to `f32`: CoAP auxiliary features

The exact numeric semantics are implemented in [src/common/feature_mapping.cpp](src/common/feature_mapping.cpp).

### Two feature paths

Proxy core can compute features in two ways:

- Legacy normalization: stateless, deterministic, simpler fallback
- Behavioral normalization: stateful, windowed, richer runtime context

The active path is controlled by `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS`.

### Debug comparison export

If `SENTRIX_FEATURE_DEBUG_PATH` is set, each processed message can be written as a JSONL record containing:

- timestamp
- protocol
- source id
- direction
- event type
- raw bytes
- legacy vector
- behavioral vector
- active vector
- decision details

This is useful for comparing feature representations during development and evaluation.

## Detection Pipeline

The detection pipeline is defined in [include/sentrix/detection_pipeline.hpp](include/sentrix/detection_pipeline.hpp) and implemented in [src/common/detection_pipeline.cpp](src/common/detection_pipeline.cpp).

### Stage 1: Rules

Rule checks use the normalized feature vector and currently inspect at least:

- message rate
- payload size

If a rule fires, the packet is dropped immediately.

### Stage 2: Inference

Inference uses ONNX Runtime when available, otherwise a deterministic heuristic fallback.

The fallback score combines:

- message rate
- payload pressure
- a small protocol-specific adjustment for CoAP

### Stage 3: Mitigation

Decision outcomes:

- `forward` when anomaly is below the rate-limit threshold
- `rate_limit` when anomaly is elevated but below the drop threshold
- `drop` when a rule triggers or anomaly exceeds the drop threshold

### Decision order

1. Rule engine evaluates the vector.
2. Inference engine computes anomaly score.
3. Mitigation engine applies the final decision.

## MQTT Module

The MQTT module is implemented in [src/mqtt/mqtt_module.cpp](src/mqtt/mqtt_module.cpp) and declared in [include/sentrix/mqtt_module.hpp](include/sentrix/mqtt_module.hpp).

### Responsibilities

- Listen on a TCP socket, default `1884`
- Connect upstream to the MQTT broker, default `1883`
- Parse MQTT control packets
- Extract packet metadata such as:
	- packet type
	- client id
	- keepalive value
	- QoS
	- retain flag
	- topic name
	- wildcard subscription markers
- Compute features and run detection
- Forward allowed traffic to the broker
- Relay broker responses back to the client

### MQTT packet handling

The parser currently recognizes packet classes such as:

- CONNECT
- PUBLISH
- SUBSCRIBE
- PUBACK / PUBREC / PUBREL / PUBCOMP
- PINGREQ / PINGRESP
- DISCONNECT

### MQTT event logging

When clients connect or disconnect, the module logs internal events. When packets are passed or blocked, it records:

- direction
- event type
- byte count
- mitigation reason when applicable

### MQTT metrics

The module increments the MQTT message counter using frame estimation so that multiple MQTT frames in one TCP read are counted correctly.

## CoAP Module

The CoAP module is implemented in [src/coap/coap_module.cpp](src/coap/coap_module.cpp) and declared in [include/sentrix/coap_module.hpp](include/sentrix/coap_module.hpp).

### Responsibilities

- Listen on a UDP socket, default `5684`
- Connect upstream to the CoAP backend, default `5683`
- Parse CoAP datagrams
- Extract metadata such as:
	- message type (CON, NON, ACK, RST)
	- request method
	- token
	- URI path
	- Observe flag
	- Blockwise transfer indicators
	- option count
- Compute features and run detection
- Maintain message-id routing so responses go back to the correct client

### CoAP routing model

Because CoAP is UDP-based, the proxy keeps a message-id to client-endpoint mapping for routed requests and responses.

If a backend response cannot be matched to a client, it is logged as an unrouted response.

### CoAP metrics

Allowed CoAP packets increment the CoAP counter. Dropped packets increment detections and are logged as mitigation events.

## Metrics and Event Logging

The proxy exports runtime observability through two files.

### Metrics snapshot

Implemented in [src/common/metrics_store.cpp](src/common/metrics_store.cpp).

Current fields:

- `mqtt_msgs`
- `coap_msgs`
- `detections`
- `latency_ms_p95`

Metrics are flushed once per second by the main loop.

### Event log

Implemented in [src/common/event_log.cpp](src/common/event_log.cpp).

Each line is a JSON object containing:

- timestamp
- protocol
- direction
- event type
- byte count
- detail string

The event log is append-only and is safe to tail while the proxy is running.

## Feature Debug Output

Implemented in [src/common/feature_debug.cpp](src/common/feature_debug.cpp).

If enabled, feature-debug JSONL records contain:

- protocol and source metadata
- raw payload statistics
- legacy, behavioral, and active feature vectors
- final decision metadata
- anomaly score

This is the best artifact for offline inspection of what the proxy saw and how it reacted.

## Proxy Core Lifecycle

`ProxyCore` is a small module manager defined in [include/sentrix/proxy_core.hpp](include/sentrix/proxy_core.hpp) and implemented in [src/common/proxy_core.cpp](src/common/proxy_core.cpp).

Lifecycle methods:

- `registerModule` stores protocol handlers
- `startAll` starts every registered handler
- `stopAll` stops every registered handler

The main executable registers MQTT first, then CoAP.

## Main Executable

The entry point is [src/common/main.cpp](src/common/main.cpp).

Startup behavior:

1. Read `SENTRIX_METRICS_PATH` or fall back to `/tmp/sentrix_metrics.json`
2. Register MQTT and CoAP modules
3. Print the detection runtime summary
4. Start modules
5. Flush metrics every second
6. Stop cleanly on SIGINT or SIGTERM

Example console output:

```text
[Detection] Runtime config: ...
[MQTT] proxy listening on 0.0.0.0:1884 -> mosquitto:1883
[CoAP] proxy listening on 0.0.0.0:5684 -> californium-backend:5683
SentriX proxy-core running (Week 7 detection scaffold mode). Press Ctrl+C to stop.
```

## Default Ports and Endpoints

| Component | Default |
|---|---|
| MQTT ingress | `1884/tcp` |
| MQTT broker | `1883/tcp` |
| CoAP ingress | `5684/udp` |
| CoAP backend | `5683/udp` |
| Metrics API | `8080/tcp` |

## Build and Run

### Host mode

Use host mode when you want the compiled binary to connect to local Docker services.

```bash
cd /home/billy/X/SentriX/deploy
docker compose up -d mosquitto californium-backend metrics-api-stub

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
SENTRIX_FEATURE_DEBUG_PATH=/tmp/sentrix_features.jsonl \
./build/sentrix_proxy
```

### Docker mode

Docker mode uses the service names defined in [../deploy/docker-compose.yml](../deploy/docker-compose.yml).

```bash
cd /home/billy/X/SentriX/deploy
docker compose up --build
```

## Validation Workflows

### Smoke test

```bash
cd /home/billy/X/SentriX
python proxy-core/scripts/week7_smoke_validation.py
```

### Benign MQTT traffic

```bash
python proxy-core/scripts/week8_benign_scenario.py
```

### Attack and stress scenarios

```bash
python proxy-core/scripts/week8_attack_scenario.py
python proxy-core/scripts/week10_mqtt_stress.py
python proxy-core/scripts/week10_coap_stress.py
```

### Integration checks

```bash
python proxy-core/scripts/week9_coap_integration.py
python proxy-core/scripts/week9_combined_protocol.py
```

### Runtime analysis

```bash
python proxy-core/scripts/week8_latency_analysis.py
python proxy-core/scripts/week8_feature_drift_analysis.py
python proxy-core/scripts/week10_analyze_features.py
```

## Troubleshooting

### Proxy does not start

Check for:

- bad port values
- missing backend services
- socket permission issues
- port conflicts with another process

Useful commands:

```bash
docker compose ps
docker compose logs -f proxy-core
lsof -i :1884
lsof -i :5684
```

### ONNX model is not used

If ONNX Runtime support was compiled in but inference still falls back to heuristics:

- verify `SENTRIX_ONNX_MODEL_PATH` is set
- verify the file exists
- verify the ONNX Runtime shared library is discoverable at runtime

The process logs a warning if ONNX initialization fails and the fallback heuristic is active.

### Metrics file is empty or stale

The main loop writes the metrics snapshot once per second. Confirm:

- the process is still running
- `SENTRIX_METRICS_PATH` points to a writable location
- the proxy has processed at least one packet

### MQTT packets are not forwarded

Confirm:

- the upstream broker is reachable
- `SENTRIX_MQTT_BROKER_HOST` and `SENTRIX_MQTT_BROKER_PORT` are correct
- no rule is dropping the traffic

### CoAP responses are unrouted

This usually means the response message-id was not found in the proxy map.
Check the client/backend traffic pattern and confirm the request was routed through the proxy first.

## Expected Outputs

When proxy core is working correctly, you should see:

- MQTT listener bound on `0.0.0.0:1884`
- CoAP listener bound on `0.0.0.0:5684`
- periodic metrics writes to `/tmp/sentrix_metrics.json`
- append-only event log lines in `/tmp/sentrix_events.log`
- optional feature-debug JSONL records when enabled

### Example metrics snapshot

```json
{
	"mqtt_msgs": 84,
	"coap_msgs": 14,
	"detections": 0,
	"latency_ms_p95": 0
}
```

## Notes on Current Status

This codebase is already beyond a stub:

- MQTT and CoAP modules are implemented
- feature mapping has both legacy and behavioral paths
- detection supports rules plus inference fallback
- event and metrics logging are live
- ONNX support is optional and gated at build time

The remaining work in the broader project is mostly around model quality, feature evolution, and evaluation rather than basic runtime scaffolding.

## Related Documentation

- [../README.md](../README.md)
- [../SETUP_CODING.md](../SETUP_CODING.md)
- [../REPRODUCIBILITY.md](../REPRODUCIBILITY.md)
- [../ml-pipeline/README.md](../ml-pipeline/README.md)
- [../config/feature_schema.md](../config/feature_schema.md)

