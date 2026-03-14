# SentriX

## A Middleware-Independent Multi-Stage Security Proxy for Heterogeneous IoT Protocols

Title Options :
- “A Lightweight Multi-Stage Reverse Proxy Architecture for Heterogeneous IoT Protocol Security”
- “Protocol-Agnostic Edge Defense for IoT: A Multi-Stage Security Proxy Supporting MQTT and CoAP”
- "SentriX: A Middleware-Independent Multi-Stage Security Proxy for Heterogeneous IoT Protocols"
- “SentriX: A Middleware-Agnostic Edge-Native Security Proxy for Heterogeneous IoT Protocols (MQTT and CoAP)”

---

## Current Status Snapshot (as of 2026-03-10)

- **Week 1:** Completed (objective, threat model, normalized feature spec freeze)
- **Week 2:** Completed (MQTT/CoAP testbeds + collection pipeline)
- **Week 3:** Completed (21/21 matrix runs, 11,209 labeled rows, all exit criteria satisfied)
- **Week 4:** Completed (feature quality validation + KL alignment reports)
- **Week 5:** Completed (5-fold baseline sweep completed with LogReg, RandomForest, MLP, LightGBM + per-class outputs)

**Current bottleneck:** cross-protocol generalization is weak relative to grouped CV performance.

**Next immediate actions:**

1. Select Week 6 model candidate using accuracy-latency-generalization tradeoff.
2. Run feature ablations and finalize deployable feature subset.
3. Begin model compression/export workflow (quantization/pruning + ONNX).

# 1. Research Scope

This research will focus on:

- **Protocols:** MQTT (v3.1.1, v5.0 stretch), CoAP (RFC 7252)
- **Backend Brokers:** Eclipse Mosquitto (MQTT), Eclipse Californium (CoAP)
- **Deployment Model:** Per-protocol reverse proxy instances, each sitting in front of its native broker — no protocol translation, no broker modification
- **Core Innovation:** A **protocol-normalized behavioral feature abstraction layer** that maps heterogeneous protocol semantics into a unified feature space, enabling a single ML detection model to operate across protocols

**Future protocol targets (explicitly out of scope for now):** AMQP, HTTP/WebSocket, LwM2M, OPC-UA.

### 1.1 Why MQTT and CoAP?

MQTT and CoAP represent the two dominant — and architecturally contrasting — IoT messaging paradigms:

| Property         | MQTT                               | CoAP                           |
| ---------------- | ---------------------------------- | ------------------------------ |
| Transport        | TCP (persistent, stateful)         | UDP (stateless, per-request)   |
| Pattern          | Publish/Subscribe                  | Request/Response (+ Observe)   |
| Connection Model | Long-lived sessions                | Transactionless datagrams      |
| QoS              | 0, 1, 2 (broker-managed)           | Confirmable / Non-confirmable  |
| Security         | TLS                                | DTLS                           |
| State            | Per-client session state in broker | Stateless (tokens per request) |

These architectural differences make them ideal candidates for validating that protocol-normalized behavioral features can generalize across fundamentally different IoT communication models.

---

# 2. Core Research Objective

Design and evaluate a **protocol-aware, multi-stage AI reverse proxy architecture** that:

1. Detects application-layer attacks across MQTT and CoAP in real time
2. Normalizes protocol-heterogeneous behaviors into a **unified behavioral feature space** — without protocol translation or broker modification
3. Maintains low latency overhead on both TCP (MQTT) and UDP (CoAP) paths
4. Operates within constrained edge environments
5. Is **extensible** to additional IoT protocols via the normalization abstraction

This research proposes and rigorously evaluates a **standalone, protocol-aware, multi-stage AI reverse proxy** that enables real-time mitigation of application-layer attacks across heterogeneous IoT protocols at the network edge.

The central hypothesis is:

> A protocol-aware reverse proxy that normalizes behavioral features across heterogeneous IoT protocols (MQTT over TCP, CoAP over UDP) can achieve high detection performance with minimal latency overhead, **without requiring protocol translation or broker modification**, using a single unified ML detection model.

The work seeks to formally quantify:

- The **security–performance tradeoff** introduced by edge-native AI-based inspection
- The **generalization capability** of protocol-normalized behavioral features across fundamentally different IoT communication models
- The **extensibility cost** of adding new protocols to the normalization framework

# 2.5 Threat Model

## Adversary Capabilities

- Network-level: Can send arbitrary MQTT or CoAP packets to the respective proxy's port
- Application-level: Can craft valid or malformed protocol control packets for either protocol
- No physical access to the broker or proxy host
- Adversary does **not** need to know which protocol is being proxied — attacks are protocol-native

## Attack Taxonomy (Cross-Protocol)

### Common Attack Classes (Both Protocols)

| Attack Class       | MQTT Manifestation                    | CoAP Manifestation                            |
| ------------------ | ------------------------------------- | --------------------------------------------- |
| **Volumetric**     | PUBLISH flood, CONNECT flood          | Request flood (CON/NON spam)                  |
| **Protocol abuse** | Malformed packets, oversized payloads | Malformed options, invalid tokens             |
| **Semantic**       | Topic squatting, payload injection    | Resource path manipulation, payload injection |
| **Slow-rate**      | SlowITe (slow CONNECT)                | Slow Observe registration, CON without ACK    |
| **Amplification**  | QoS 2 handshake abuse                 | Observe notification amplification            |

### MQTT-Specific Exploits

- **SlowITe** — Slow CONNECT attack exploiting MQTT keep-alive timer
- **Wildcard subscription abuse** — Using `#` or `+` wildcards to exfiltrate data across topics
- **QoS exploitation** — Abusing QoS 2 four-step handshake for amplification
- **Will message abuse** — Crafting malicious Last Will and Testament (LWT) payloads
- **Client ID spoofing** — Reusing or hijacking client identifiers to disrupt sessions

### CoAP-Specific Exploits

- **Amplification via Observe** — Registering Observe on high-frequency resources to amplify traffic
- **Token exhaustion** — Rapidly cycling tokens to exhaust server tracking state
- **Block-wise transfer abuse** — Incomplete Block2 transfers to waste server resources
- **Resource discovery abuse** — Flooding `/.well-known/core` to map and probe resources
- **Confirmable flood** — Sending CON messages with spoofed source IPs to trigger ACK amplification
- **Proxy-forward abuse** — Crafting Proxy-Uri options to turn CoAP servers into open proxies

## Trust Boundaries

- IoT devices are **untrusted**
- Each proxy ↔ its backend broker link is **trusted** (localhost or secured channel)
- MQTT proxy and CoAP proxy operate **independently** — no cross-protocol trust assumptions
- Dashboard is read-only and behind authentication

---

# 3. System Architecture

## 3.1 High-Level Architecture

```
                    ┌─────────────────────────────────────────────────┐
                    │              Edge Node                          │
                    │                                                 │
MQTT Devices ──TCP──▶ [MQTT Proxy] ──TCP──▶ Mosquitto Broker          │
                    │      │                                          │
                    │      ▼                                          │
                    │  ┌────────────────────┐                         │
                    │  │ Normalized Feature │ ──▶ Unified ML Model    │
                    │  │   Abstraction Layer│                         │
                    │  └────────────────────┘                         │
                    │      ▲                                          │
                    │      │                                          │
CoAP Devices ──UDP──▶ [CoAP Proxy] ──UDP──▶ Californium Server        │
                    │                                                 │
                    │      ┌──────────────────────┐                   │
                    │      │ Next.js Dashboard    │ ◀── Metrics API   │
                    └──────┴──────────────────────┴───────────────────┘
```

**Key architectural decision:** Each protocol gets its own dedicated proxy process. There is **no protocol translation** — MQTT traffic stays MQTT, CoAP traffic stays CoAP. The proxies share only the normalized behavioral feature space and the ML detection model.

## 3.2 Proxy Responsibilities (Per-Protocol Instance)

Each protocol proxy will:

- Intercept all protocol-native traffic (TCP for MQTT, UDP for CoAP)
- Parse protocol-specific control packets
- Extract protocol-specific raw features
- **Normalize** features into the unified behavioral feature vector
- Run the shared multi-stage detection pipeline
- Forward or mitigate traffic using protocol-appropriate actions
- Log metrics for analysis and visualization

## 3.3 Protocol Normalization Layer (Core Innovation)

The normalization layer maps protocol-specific semantics into **abstract behavioral dimensions** that are meaningful across protocols:

```
Protocol-Specific Features ──▶ Normalization Layer ──▶ Unified Behavioral Vector ──▶ ML Model
```

### Normalization Mapping

| Abstract Behavioral Dimension | MQTT Source                           | CoAP Source                        |
| ----------------------------- | ------------------------------------- | ---------------------------------- |
| `msg_rate`                    | PUBLISH rate                          | Request rate (GET/PUT/POST)        |
| `inter_arrival_time`          | Time between PUBLISHes                | Time between requests              |
| `payload_size`                | PUBLISH payload bytes                 | Request/response payload bytes     |
| `payload_entropy`             | Shannon entropy of PUBLISH payload    | Shannon entropy of request payload |
| `resource_path_depth`         | Topic depth (`/` count)               | URI-Path option depth (`/` count)  |
| `resource_path_entropy`       | Shannon entropy of topic string       | Shannon entropy of URI-Path        |
| `qos_level`                   | MQTT QoS (0/1/2) → normalized 0.0–1.0 | CON/NON → normalized 0.0/1.0       |
| `session_duration`            | CONNECT to DISCONNECT time            | Observation window duration        |
| `unique_resource_count`       | Unique topics per client              | Unique URI-Paths per source IP     |
| `error_rate`                  | Invalid packet ratio / CONNACK errors | 4.xx/5.xx response ratio           |
| `handshake_complexity`        | QoS 2 handshake steps initiated       | CON/ACK exchange ratio             |
| `subscription_breadth`        | Wildcard subscription scope           | Observe registration count         |
| `reconnection_rate`           | CONNECT frequency                     | New token generation rate          |
| `payload_to_resource_ratio`   | Payload size / topic length           | Payload size / URI-Path length     |
| `protocol_compliance_score`   | Valid MQTT packet ratio               | Valid CoAP option format ratio     |

The normalization layer also appends a **one-hot protocol identifier** (`[1,0]` for MQTT, `[0,1]` for CoAP) so the model can optionally learn protocol-specific patterns.

### 3.4 Normalized Feature Specification (Week 1 Freeze v1.0)

To complete Week 1, the normalized feature layer is frozen with explicit computation semantics for reproducible extraction:

| Feature | Symbol | Window | Unit | Range / Normalization | Definition |
| --- | --- | --- | --- | --- | --- |
| `msg_rate` | $r_m$ | 1s sliding | msg/s | min-max to [0,1] | Count of valid protocol messages in window / window length |
| `inter_arrival_time` | $\Delta t$ | 1s sliding | ms | z-score then clip to [-3,3] and rescale to [0,1] | Mean inter-arrival between consecutive messages from same client/source |
| `payload_size` | $s_p$ | per-message | bytes | log1p then min-max [0,1] | Application payload byte length |
| `payload_entropy` | $H_p$ | per-message | bits/byte | divide by 8 to [0,1] | Shannon entropy of payload bytes |
| `resource_path_depth` | $d_r$ | per-message | levels | divide by max depth cap (8) | Topic or URI path segment count |
| `resource_path_entropy` | $H_r$ | per-message | bits/char | divide by theoretical max | Shannon entropy of topic/URI string |
| `qos_level` | $q$ | per-message | n/a | MQTT: {0,0.5,1.0}; CoAP: NON=0, CON=1 | Delivery reliability abstraction |
| `session_duration` | $t_s$ | active session window | s | clip to 300s and divide by 300 | MQTT connection duration or CoAP observation window duration |
| `unique_resource_count` | $u_r$ | 10s sliding | count | divide by cap (32) | Distinct topic/URI targets by same source |
| `error_rate` | $e_r$ | 10s sliding | ratio | [0,1] | Protocol errors / total messages in window |
| `handshake_complexity` | $h_c$ | 10s sliding | ratio | [0,1] | MQTT QoS2 handshake stages or CoAP CON↔ACK exchange ratio |
| `subscription_breadth` | $b_s$ | 30s sliding | count/score | divide by cap (16) | MQTT wildcard breadth or CoAP Observe registration breadth |
| `reconnection_rate` | $r_c$ | 30s sliding | events/min | divide by cap (30) | MQTT reconnects or CoAP new-token-session bursts per source |
| `payload_to_resource_ratio` | $\rho_{pr}$ | per-message | ratio | log1p then min-max [0,1] | Payload bytes divided by resource string length |
| `protocol_compliance_score` | $c_p$ | 10s sliding | ratio | [0,1] | Well-formed message ratio according to protocol parser |

**Window policy:** per-message features are emitted immediately; windowed features use source-scoped sliding windows with 100 ms update granularity.

**Missing-value policy:** any undefined value (e.g., zero-length payload entropy) is imputed to 0 and accompanied by a binary validity flag in protocol-specific auxiliary features.

> **Extensibility:** Adding a new protocol requires only implementing a new protocol parser and defining the normalization mapping from that protocol's features to the abstract dimensions. The ML model and detection pipeline remain unchanged.

---

# 4. Multi-Stage Detection Pipeline

## Stage 1: Fast Rule-Based Filter

Lightweight, constant-time checks applied to the **normalized feature vector** (protocol-agnostic) plus protocol-specific rules:

### Cross-Protocol Rules (Applied to Normalized Features)

- `msg_rate` > threshold → rate anomaly
- `payload_size` > threshold → oversized payload
- `payload_entropy` < threshold → suspicious constant payload
- `resource_path_entropy` anomaly → resource scanning heuristic
- `reconnection_rate` > threshold → connection abuse

### MQTT-Specific Rules

- Topic blacklist check
- Wildcard subscription depth check (`#`, `+`)
- Keep-alive violation detection (SlowITe signature)
- Client ID format validation

### CoAP-Specific Rules

- `/.well-known/core` request rate limit
- Block-wise transfer completion tracking
- Observe registration rate cap
- Proxy-Uri option presence (open proxy abuse)
- Token format/length validation

Goal: Filter obvious malicious traffic with negligible overhead, leveraging both normalized and protocol-specific signals.

## Stage 2: Lightweight ML Classifier

### Feature Set Architecture

The feature vector fed to the ML model consists of three layers:

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Normalized Behavioral Features (15 dims, shared)       │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: Protocol Identifier (one-hot, 2 dims for now)          │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: Protocol-Specific Auxiliary Features (variable dims)   │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: Normalized Behavioral Features (Cross-Protocol)

These are the 15 abstract behavioral dimensions from Section 3.3, computed identically regardless of source protocol:

- `msg_rate` — Messages per second
- `inter_arrival_time` — Mean time between messages
- `payload_size` — Payload byte count
- `payload_entropy` — Shannon entropy of payload bytes
- `resource_path_depth` — Hierarchical depth of target resource
- `resource_path_entropy` — Shannon entropy of resource identifier
- `qos_level` — Delivery guarantee level (normalized 0.0–1.0)
- `session_duration` — Time span of current behavioral window
- `unique_resource_count` — Distinct resources targeted
- `error_rate` — Protocol error ratio
- `handshake_complexity` — Delivery handshake overhead
- `subscription_breadth` — Scope of data subscription
- `reconnection_rate` — Session re-establishment frequency
- `payload_to_resource_ratio` — Payload size relative to resource identifier
- `protocol_compliance_score` — Ratio of well-formed to total packets

### Layer 2: Protocol Identifier

- One-hot encoding: `[1,0]` = MQTT, `[0,1]` = CoAP
- Allows the model to learn protocol-conditional patterns when beneficial
- Future protocols extend this vector (e.g., `[0,0,1]` for AMQP)

### Layer 3: Protocol-Specific Auxiliary Features

**MQTT-Specific (8 dims):**

- Retain flag (binary)
- Wildcard subscription depth (`#`/`+` count)
- CONNECT/DISCONNECT ratio
- Keep-alive timer value (normalized)
- Will message presence (binary)
- QoS 2 handshake completion ratio
- Client ID entropy
- Message size variance

**CoAP-Specific (8 dims):**

- Message type distribution (CON/NON/ACK/RST ratios — 4 values)
- Observe registration flag (binary)
- Block-wise transfer in-progress (binary)
- Token reuse ratio
- Option count per message

> **Note:** Auxiliary features are zero-padded for the non-matching protocol. E.g., when processing CoAP traffic, the 8 MQTT auxiliary dims are all 0. This ensures a fixed-size input vector.

### Total Feature Vector Size

`15 (normalized) + 2 (protocol ID) + 8 (MQTT aux) + 8 (CoAP aux) = 33 dimensions`

Adding a new protocol adds its auxiliary features + extends the one-hot vector. The normalized 15 dimensions remain stable.

### Candidate Models

- Random Forest
- LightGBM
- Small MLP (fully connected neural network)

Selection criteria:

- Detection accuracy (overall and **per-protocol**)
- F1 score (macro, per-attack-class, **per-protocol**)
- Inference latency
- Memory footprint
- **Cross-protocol generalization** — train on MQTT+CoAP jointly, measure per-protocol performance

Model will be exported to ONNX or lightweight C++ inference runtime.

### Key Experiment: Cross-Protocol Generalization

To validate the normalization layer, we will evaluate:

1. **Joint model** — Single model trained on both MQTT + CoAP normalized features
2. **Protocol-specific models** — Separate models per protocol (baseline)
3. **Transfer test** — Train on MQTT only, test on CoAP (and vice versa) to measure zero-shot cross-protocol transfer via normalized features

This directly tests the central hypothesis.

## Stage 3: Adaptive Mitigation

Actions are protocol-aware:

**Cross-Protocol Actions:**

- Forward traffic
- Drop packet
- Rate limit client/source
- Temporary quarantine

**MQTT-Specific Actions:**

- Force DISCONNECT
- Reject SUBSCRIBE (wildcard filter)
- Downgrade QoS

**CoAP-Specific Actions:**

- Send RST (reset) message
- Reject Observe registration
- Return 4.01 Unauthorized / 4.29 Too Many Requests
- Silently drop (no ACK for CON)

Mitigation decisions will be logged with protocol tag for per-protocol evaluation.

---

# 5. Dataset & Training Strategy

## 5.1 Dataset Options

- BoT-IoT dataset (network-flow level; requires feature extraction from raw pcaps)
- CIC IoT dataset (network-flow level; same extraction requirement)
- **Custom multi-protocol traffic simulation (primary — see 5.3)**

> **Note:** BoT-IoT and CIC IoT are not protocol-specific. They operate at the network-flow level and lack application-layer MQTT/CoAP features. The custom testbed dataset is the primary data source; public datasets serve as supplementary baselines.

## 5.2 Training Workflow

1. Collect MQTT traffic from custom MQTT testbed
2. Collect CoAP traffic from custom CoAP testbed
3. Extract protocol-specific raw features per protocol parser
4. **Apply normalization mapping** to produce unified behavioral feature vectors
5. Label traffic using ground-truth attack scripts
6. Combine MQTT and CoAP normalized datasets with protocol identifier tags
7. Train candidate models on the **combined** normalized dataset
8. Evaluate with 5-fold stratified cross-validation (**stratified by both attack class and protocol**)
9. Run cross-protocol generalization experiments (Section 4, Key Experiment)
10. Apply model compression (quantization/pruning)
11. Export optimized model to ONNX for C++ inference

## 5.3 Custom Multi-Protocol Testbed

Build a reproducible testbed for labeled dataset generation across both protocols:

### MQTT Testbed

```
MQTT Clients (Eclipse Paho) → MQTT AI Proxy → Mosquitto Broker
       ↑
  Attack Scripts (mqtt-pwn, custom Python scripts)
```

**Benign MQTT traffic:**

- Simulated IoT sensors (temperature, humidity, motion) publishing on realistic topic hierarchies
- Varying publish rates, QoS levels, and payload sizes

**MQTT attack traffic:**

- Publish flood (high-rate PUBLISH from multiple clients)
- SlowITe (slow CONNECT with extended keep-alive)
- Malformed packet injection (invalid headers, oversized payloads)
- Connection exhaustion (rapid CONNECT without DISCONNECT)
- Wildcard subscription abuse (`#` subscription to exfiltrate)
- QoS 2 amplification (incomplete PUBREL handshakes)

### CoAP Testbed

```
CoAP Clients (libcoap / aiocoap) → CoAP AI Proxy → Californium Server
       ↑
  Attack Scripts (custom Python scripts using aiocoap/scapy)
```

**Benign CoAP traffic:**

- Simulated IoT sensors reporting via GET/PUT/POST to realistic URI paths (e.g., `/sensors/temp`, `/actuators/valve`)
- Mix of CON and NON messages
- Periodic Observe registrations for sensor monitoring
- Block-wise transfers for firmware update simulation

**CoAP attack traffic:**

- Request flood (high-rate CON/NON requests from multiple sources)
- Amplification via Observe (mass Observe registrations on high-frequency resources)
- Token exhaustion (rapidly cycling unique tokens)
- Block-wise transfer abuse (incomplete Block2 sequences)
- Resource discovery flood (`/.well-known/core` abuse)
- Confirmable flood with spoofed source (ACK amplification)
- Malformed option injection (invalid option numbers, oversized option values)

**Labeling:** Each attack script tags its traffic window with ground-truth labels **and protocol identifier**. Proxy logs are post-processed through the normalization layer to create the labeled unified feature dataset.

---

# 6. Implementation Plan

## 6.1 C++ Proxy Core (Shared Framework)

### Architecture Pattern

Both MQTT and CoAP proxies share a common C++ framework with protocol-specific modules plugged in:

```
┌─────────────────────────────────────────────────────────┐
│             Shared Proxy Framework (C++)                │
├─────────────────────────────────────────────────────────┤
│ • Feature Normalization Engine                          │
│ • ML Inference Engine (ONNX Runtime)                    │
│ • Rule Engine (cross-protocol rules)                    │
│ • Metrics Collector & Export                            │
│ • Mitigation Decision Engine                            │
├────────────────────────────┬────────────────────────────┤
│   MQTT Protocol Module     │   CoAP Protocol Module     │
│ • TCP Listener (epoll)     │ • UDP Listener (recvmmsg)  │
│ • MQTT Packet Parser       │ • CoAP Message Parser      │
│ • MQTT Feature Extractor   │ • CoAP Feature Extractor   │
│ • MQTT-specific rules      │ • CoAP-specific rules      │
│ • TCP forwarding           │ • UDP forwarding           │
└────────────────────────────┴────────────────────────────┘
```

### Shared Core Components

- **Feature Normalization Engine:** Maps protocol-specific raw features → unified behavioral vector (Section 3.3)
- **ML Inference Engine:** ONNX Runtime (C++ API) for neural models; custom native inference for tree models
- **Cross-Protocol Rule Engine:** Evaluates normalized feature rules from Stage 1
- **Mitigation Decision Engine:** Protocol-agnostic decision + protocol-specific action dispatch
- **Metrics Collector:** Aggregates throughput, latency, detection stats tagged by protocol

### MQTT Protocol Module

- **TCP Listener:** Event-driven with `epoll` (Linux) for async I/O
- **MQTT Packet Parser:** Stateful, streaming parser for MQTT v3.1.1 (v5.0 as stretch goal); handles fragmented TCP segments
- **MQTT Feature Extractor:** Per-packet and per-session MQTT-specific raw features
- **MQTT-Specific Rules:** Topic blacklists, wildcard checks, SlowITe signatures
- **TCP Forwarding:** Zero-copy buffer management where possible

#### MQTT Packet Types Handled

- CONNECT / CONNACK
- PUBLISH / PUBACK / PUBREC / PUBREL / PUBCOMP
- SUBSCRIBE / SUBACK
- UNSUBSCRIBE / UNSUBACK
- PINGREQ / PINGRESP
- DISCONNECT

### CoAP Protocol Module

- **UDP Listener:** Event-driven with `epoll` on UDP socket; uses `recvmmsg` for batch reception
- **CoAP Message Parser:** Stateless per-message parser for RFC 7252; handles all message types and option parsing
- **CoAP Feature Extractor:** Per-message and per-source-IP windowed features
- **CoAP-Specific Rules:** Resource discovery rate limits, Observe caps, token validation
- **UDP Forwarding:** Minimal-copy datagram forwarding to Californium backend

#### CoAP Message Types Handled

- CON (Confirmable)
- NON (Non-confirmable)
- ACK (Acknowledgement)
- RST (Reset)

#### CoAP Methods Handled

- GET / POST / PUT / DELETE
- Observe (RFC 7641)
- Block-wise transfers (RFC 7959)

### Dependencies

| Component        | Library                                           |
| ---------------- | ------------------------------------------------- |
| Networking (TCP) | Boost.Asio or raw `epoll`                         |
| Networking (UDP) | Raw `epoll` + `recvmmsg`                          |
| ML Inference     | ONNX Runtime C++ API                              |
| Serialization    | nlohmann/json or FlatBuffers                      |
| Logging          | spdlog (lock-free, zero-allocation)               |
| Build System     | CMake                                             |
| CoAP parsing ref | libcoap (reference only; custom parser for proxy) |

### Thread Model

- **MQTT I/O thread:** Accept TCP connections + event loop + Stage 1 filtering
- **CoAP I/O thread:** UDP recv loop + event loop + Stage 1 filtering
- **Inference thread(s):** Shared ML inference offloaded from both protocol threads
- **Metrics thread:** Periodic stats export via REST endpoint (serves both protocols)

### Protocol Module Interface (Extensibility)

Each protocol module implements a common C++ interface:

```cpp
class IProtocolModule {
public:
    virtual ~IProtocolModule() = default;
    virtual void start() = 0;
    virtual void stop() = 0;
    // Parse raw bytes into protocol-specific event
    virtual ProtocolEvent parse(const uint8_t* data, size_t len) = 0;
    // Extract raw protocol-specific features from event
    virtual RawFeatureVector extractFeatures(const ProtocolEvent& event) = 0;
    // Map raw features to normalized behavioral vector
    virtual NormalizedFeatureVector normalize(const RawFeatureVector& raw) = 0;
    // Execute protocol-specific mitigation action
    virtual void mitigate(const MitigationDecision& decision) = 0;
};
```

> **Adding a new protocol:** Implement `IProtocolModule` for the new protocol. Register it with the shared framework. Done.

## 6.2 Dashboard (Next.js)

Displays (with per-protocol breakdown):

- Message throughput (MQTT and CoAP, independently and combined)
- Detected attacks (filterable by protocol, attack class)
- Mitigation actions (per protocol)
- Latency overhead (per protocol: TCP vs UDP path)
- CPU and memory usage (per proxy instance)
- Cross-protocol correlation view (attacks spanning both protocols)
- Normalized feature distribution visualization

Dashboard connects to shared metrics API endpoint that aggregates from both proxy instances.

---

# 7. Experimental Evaluation Plan

## 7.1 Baselines

1. **No proxy:** Mosquitto + Californium without any proxy
2. **Rule-only proxy:** Proxy with Stage 1 only (both protocols)
3. **Protocol-specific models:** Separate ML models per protocol
4. **Joint model:** Single unified model on normalized features (proposed approach)
5. **Full multi-stage pipeline:** Rule + ML + mitigation (proposed system)

## 7.2 Metrics

Security Metrics (reported **per-protocol** and **aggregate**):

- Detection accuracy
- Precision, Recall, F1 score (macro and per-attack-class)
- False positive rate (FPR)
- ROC-AUC curves per model
- Confusion matrix per model per attack class
- **Cross-protocol generalization score** (train on one protocol, test on other)

Performance Metrics (reported **per-protocol**):

- End-to-end latency overhead: **p50, p95, p99** (not just mean)
- MQTT: connection-to-CONNACK latency, PUBLISH-to-forward latency
- CoAP: request-to-forward latency, CON-to-ACK overhead
- Throughput (messages/sec per protocol)
- CPU utilization (per proxy instance and shared inference)
- Memory usage (RSS, peak per proxy instance)

Normalization Metrics (novel):

- **Feature distribution alignment** — KL divergence between MQTT and CoAP normalized feature distributions for same attack class
- **Normalization overhead** — Time to map raw features to normalized vector

## 7.3 Evaluation Rigor

- **5-fold stratified cross-validation** for all model comparisons (stratified by attack class × protocol)
- **Per-attack-type detection rates** (not just aggregate), broken down by protocol
- **Statistical significance testing** between models (McNemar's test or paired t-test)
- **Ablation study:** measure contribution of each pipeline stage independently
  - Stage 1 only vs. Stage 1+2 vs. Full pipeline (per protocol)
  - Normalized features only vs. normalized + auxiliary features
  - With vs. without protocol identifier
- **Cross-protocol transfer study:** Train on Protocol A, test on Protocol B
- **Resource profiling:** measure inference time per packet for each model

## 7.4 Stress Testing

Simulate per protocol:

**MQTT Stress Tests:**

- High-frequency publish flood (10k+ msg/sec)
- SlowITe attack (slow CONNECT with keep-alive exploitation)
- Malformed payload injection (invalid headers, oversized payloads)
- Connection exhaustion attack (rapid CONNECT without DISCONNECT)
- Wildcard subscription abuse (`#` topic exfiltration)
- QoS 2 amplification (incomplete handshake flood)

**CoAP Stress Tests:**

- High-frequency request flood (10k+ msg/sec CON + NON)
- Observe amplification (mass registrations on high-frequency resource)
- Token exhaustion (rapid unique token generation)
- Block-wise transfer abuse (incomplete Block2 sequences at scale)
- Resource discovery flood (`/.well-known/core` at high rate)
- Confirmable flood with spoofed source IPs

**Cross-Protocol Stress Tests:**

- Simultaneous MQTT + CoAP volumetric attack (measure shared inference thread contention)
- Mixed benign/malicious across protocols (measure cross-protocol false positive interference)

Measure degradation curves: throughput vs. attack intensity, latency vs. attack intensity — **per protocol and combined**.

---

# 8. Timeline (12 Weeks)

## Week 1

- Finalize research objective and threat model (MQTT + CoAP)
- Review related work on cross-protocol IoT security, build comparison table
- Define normalized behavioral feature set and protocol-specific mappings

### Week 1 Completion Status (Done)

- ✅ Objective + central hypothesis finalized in Sections 2 and 2.5
- ✅ Cross-protocol threat taxonomy finalized with protocol-specific exploit lists
- ✅ Normalized feature layer frozen as v1.0 in Section 3.4 (definitions, units, windows, normalization)
- ✅ Related work comparison workflow drafted in `Related_Work_Shortlist_Draft.md` with final-8 candidate structure

**Week 1 Deliverables Produced:**

1. Final problem statement and hypothesis (Sections 2, 10)
2. Final Week 1 threat model baseline (Section 2.5)
3. Normalized feature specification v1.0 (Section 3.4)
4. Related-work screening + mapping worksheet (companion draft file)

## Week 2 - completed

- Set up MQTT testbed (Mosquitto, Paho clients, attack scripts)
- Set up CoAP testbed (Californium, aiocoap/libcoap clients, attack scripts)
- Build data collection pipeline with protocol tagging

## Week 3 - completed

- Complete MQTT dataset collection and labeling
- Complete CoAP dataset collection and labeling
- Implement and validate normalization mapping (Python prototype)

### Week 3 Step 1: Traffic Run Matrix (Frozen v0.1)

The following matrix is fixed for Week 3 data collection to ensure reproducibility and balanced labels.

**Run policy (applies to all rows):**

- 3 repetitions per scenario (`rep=1..3`)
- 120 seconds per run (except flood scenarios: 60 seconds)
- 30-second cooldown between runs
- Host-local proxy mode only (single proxy instance)
- All runs produce:
  - raw event log snapshot
  - metrics snapshot
  - exported protocol-tagged CSV (`proxy_events.csv` with `run_id`)

#### MQTT Run Matrix

| Run ID Pattern | Scenario | Label | Generator | Target Ingress | Duration |
| --- | --- | --- | --- | --- | --- |
| `MQ-BENIGN-R{rep}` | benign telemetry publish | `benign` | `simulators.mqtt.mqtt_benign` | `tcp://127.0.0.1:1884` | 120s |
| `MQ-FLOOD-R{rep}` | publish flood | `mqtt_publish_flood` | `simulators.mqtt.mqtt_attacks` | `tcp://127.0.0.1:1884` | 60s |
| `MQ-WILDCARD-R{rep}` | wildcard subscription abuse | `mqtt_wildcard_abuse` | `simulators.mqtt.mqtt_attacks` | `tcp://127.0.0.1:1884` | 120s |
| `MQ-MALFORM-R{rep}` | malformed/abusive packet profile | `mqtt_protocol_abuse` | `simulators.mqtt.mqtt_attacks` | `tcp://127.0.0.1:1884` | 120s |

#### CoAP Run Matrix

| Run ID Pattern | Scenario | Label | Generator | Target Ingress | Duration |
| --- | --- | --- | --- | --- | --- |
| `CP-BENIGN-R{rep}` | benign request mix | `benign` | `simulators.coap.coap_live_benign` | `udp://127.0.0.1:5684` | 120s |
| `CP-FLOOD-R{rep}` | request flood (`/.well-known/core`) | `coap_request_flood` | `simulators.coap.coap_live_attacks --attack request_flood` | `udp://127.0.0.1:5684` | 60s |
| `CP-MALFORM-R{rep}` | malformed payload burst | `coap_protocol_abuse` | `simulators.coap.coap_live_attacks --attack malformed_burst` | `udp://127.0.0.1:5684` | 120s |

#### Combined Dataset Targets (Week 3 exit criteria)

- Minimum 21 total runs: `4 MQTT scenarios × 3 reps + 3 CoAP scenarios × 3 reps`
- Minimum 10,000 total labeled records after export
- Label distribution constraint: no single class > 45% of total rows
- Protocol balance constraint: each protocol contributes at least 35% of total rows

#### Run Metadata Schema (mandatory for every export)

Each exported row must include:

- `run_id`
- `protocol` (`mqtt` / `coap`)
- `scenario`
- `label`
- `rep`
- `timestamp`

This metadata is required before starting Week 3 Step 2 (labeled feature extractor integration).

### Week 3 Completion Status (Done)

- ✅ All 21 matrix runs collected (`4 MQTT scenarios x 3 reps + 3 CoAP scenarios x 3 reps`)
- ✅ Labeled dataset exported with mandatory metadata (`run_id`, `protocol`, `scenario`, `label`, `rep`, `timestamp`)
- ✅ Exit criteria met on final dataset (`data/raw/week3_runs_labeled.csv`):
- ✅ Total rows: 11,209 (target >= 10,000)
- ✅ Label balance: max class share 29.63% (target <= 45%)
- ✅ Protocol balance: MQTT 59.50%, CoAP 40.50% (target >= 35% each)

**Week 3 Deliverables Produced:**

1. Matrix-complete labeled dataset: `data/raw/week3_runs_labeled.csv`
2. Run-aware feature extraction script: `ml-pipeline/src/export_events_to_dataset.py`

## Week 4 - completed

- Feature engineering: validate normalized feature distributions across protocols
- Measure feature alignment (KL divergence per dimension per attack class)
- Build combined normalized dataset

### Week 4 Completion Status (Done)

- ✅ Feature quality validation implemented and executed
- ✅ Per-feature distribution summaries generated (overall and by protocol)
- ✅ Cross-protocol KL alignment report generated by canonical class

**Week 4 Deliverables Produced:**

1. Validation script: `ml-pipeline/src/validate_feature_quality.py`
2. Report: `ml-pipeline/reports/week3_feature_quality.md`
3. Data tables:
- `ml-pipeline/reports/feature_summary_overall.csv`
- `ml-pipeline/reports/feature_summary_by_protocol.csv`
- `ml-pipeline/reports/kl_alignment_by_class.csv`

## Week 5 - completed

- Train candidate models (Random Forest, LightGBM, MLP) on combined dataset
- 5-fold cross-validation, per-attack-class and per-protocol evaluation
- Cross-protocol transfer experiments

### Week 5 Completion Status (Done)

- ✅ CPU-friendly baseline training pipeline implemented
- ✅ Baseline results produced for `LogisticRegression`, `RandomForest`, `MLP`, and `LightGBM`
- ✅ Official 5-fold grouped CV + cross-protocol transfer run completed
- ✅ Per-class metrics artifact exported for attack-class deep-dive analysis
- ⚠️ Cross-protocol generalization remains substantially weaker than grouped CV (carried into Week 6 model selection criteria)

**Week 5 Key Result Snapshot (official 5-fold run):**

- Best grouped CV: `LightGBM` on `full` features (`f1_macro=0.5977`, `accuracy=0.7796`)
- Near-tied grouped CV: `LightGBM` on `normalized_plus_pid` (`f1_macro=0.5974`)
- Cross-protocol transfer remains low (macro-F1 mostly in `~0.017-0.093` range; best observed `~0.093` on `logreg` in `mqtt->coap`)

**Week 5 Deliverables Produced So Far:**

1. Training script: `ml-pipeline/src/train_baselines.py`
2. Reports:
- `ml-pipeline/reports/week5_baseline_results.md`
- `ml-pipeline/reports/week5_baseline_metrics.csv`
- `ml-pipeline/reports/week5_baseline_per_class_metrics.csv`
- `ml-pipeline/reports/week5_baseline_summary.json`

``` bash

PYTHONWARNINGS=ignore OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/home/billy/X/SentriX/.venv/bin/python -u ml-pipeline/src/train_baselines.py \
  --in data/raw/week3_runs_labeled.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week5_baseline_results.md \
  --folds 5 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest,mlp,lightgbm

  ```

## Week 6 - completed

- Model selection based on accuracy-latency-generalization tradeoff
- Model compression (quantization/pruning)
- Export to ONNX

### Week 6 Completion Status (Done)

- ✅ Model selection analysis completed
- ✅ Champion model: LightGBM (full feature set) selected
- ✅ Model training and serialization complete (1.76 MB pickle)
- ✅ Feature specification document generated
- ⏳ ONNX export pending toolchain resolution (Week 7 task)

**Week 6 Key Results:**

- **Champion Model:** LightGBM with full 33-dimensional feature set
- **Accuracy:** F1-macro = 0.5977, Accuracy = 0.7796 (matches Week 5 grouped CV)
- **Model Size:** 1.76 MB (serialized pickle)
- **Inference Latency:** <0.1 ms per sample (well below 1 ms constraint)
- **Compression Potential:** Tree pruning + leaf reduction strategies documented
- **ONNX Status:** Pickle model ready; ONNX export requires onnxmltools configuration

**Week 6 Deliverables Produced:**

1. Model selection report: `ml-pipeline/reports/week6_model_selections.md`
2. Trained model (pickle): `ml-pipeline/models/lightgbm_full.pkl`
3. Feature specification: `ml-pipeline/reports/week6_feature_spec.json`
4. ONNX export infrastructure (Python scripts in src/)
5. Comprehensive status document: `ml-pipeline/reports/WEEK6_STATUS.md`

**Cross-Protocol Generalization Update:** Remains weak at ~0.09 F1-macro; addressed in Week 7+ with domain adaptation or protocol-agnostic feature improvements.

## Week 7–8

- Implement shared C++ proxy framework (normalization engine, ML inference, rule engine, metrics)
- Implement MQTT protocol module (TCP listener, MQTT parser, feature extraction)
- Implement CoAP protocol module (UDP listener, CoAP parser, feature extraction)

### Week 7 Progress Update (In Progress)

- ✅ Added shared detection scaffold in `proxy-core`:
  - `RuleEngine` (Stage 1), `InferenceEngine` (Stage 2 heuristic scaffold), `MitigationEngine` (Stage 3 action decision)
  - New files: `proxy-core/include/sentrix/detection_pipeline.hpp`, `proxy-core/src/common/detection_pipeline.cpp`
- ✅ Wired detection execution into live ingress paths before forwarding:
  - MQTT ingress path in `proxy-core/src/mqtt/mqtt_module.cpp`
  - CoAP ingress path in `proxy-core/src/coap/coap_module.cpp`
- ✅ Added detection metric increments (`addDetections`) in metrics store
- ✅ Build validated successfully (`cmake -S . -B build && cmake --build build -j`)
- ✅ ONNX Runtime inference path integrated into `InferenceEngine` with safe fallback heuristic
- ✅ ONNX-enabled native build now working via local SDK at `proxy-core/third_party/onnxruntime`
- ✅ ONNX model artifact generated: `ml-pipeline/models/lightgbm_full.onnx` (1.2 MB)
- ✅ ONNX-vs-pickle prediction agreement validated: 1.0 (`ml-pipeline/reports/week6_onnx_validation.json`)
- ✅ Replaced placeholder runtime feature extraction with the actual Python training/export mapping used for `f00..f32`
- ✅ Added shared C++ feature mapper: `proxy-core/src/common/feature_mapping.cpp`
- ✅ Upgraded MQTT parser metadata extraction:
  - control packet type decoding (`CONNECT`, `PUBLISH`, `SUBSCRIBE`, etc.)
  - wildcard subscribe detection
  - basic client-id/topic extraction
  - malformed frame marking
- ✅ Upgraded CoAP parser metadata extraction:
  - message type decoding (`CON`, `NON`, `ACK`, `RST`)
  - method/code decoding (`GET`, `POST`, `PUT`, `DELETE`)
  - URI-Path parsing
  - Observe and discovery-path detection
  - malformed option/header marking
- ✅ Runtime event logs and detection inputs now use parsed protocol semantics instead of generic route-only detail strings
- ✅ Added opt-in stateful behavioral feature mode via `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS=1`
- ✅ Added per-source runtime windows/counters for:
  - 1s message-rate tracking
  - 10s unique-resource and error-rate tracking
  - 30s reconnection/subscription-breadth tracking
  - message-size variance and CoAP type distribution tracking
- ✅ Stateful mode now computes richer live values for multiple normalized/auxiliary dimensions while preserving the same 33-feature schema

**Current status:** protocol modules now run parse -> feature extraction -> normalization -> rule/inference -> mitigation decision inline before forwarding. Two feature modes now exist:
- default: exporter-compatible legacy mapping (best match to the currently trained ONNX model)
- opt-in: stateful behavioral-window mapping enabled with `SENTRIX_ENABLE_BEHAVIORAL_WINDOWS=1` for richer live features and side-by-side evaluation

## Week 9

- Integration testing: MQTT proxy + Mosquitto, CoAP proxy + Californium
- End-to-end pipeline validation for both protocols
- Implement Next.js monitoring dashboard with per-protocol views

## Week 10

- Run all experiments and stress tests (per-protocol and cross-protocol)
- Collect latency, throughput, detection metrics
- Run cross-protocol stress tests

## Week 11

- Generate figures, tables, ROC curves, ablation results
- Statistical significance testing
- Cross-protocol generalization analysis

## Week 12

- Write and finalize paper
- Prepare reproducibility artifacts (Docker, scripts, datasets)

---

# 9. Paper Structure

1. Introduction
2. Related Work (include comparison table — see Section 12)
3. Threat Model (cross-protocol attack taxonomy)
4. Protocol Normalization Framework (core contribution)
5. System Architecture (shared framework + protocol modules)
6. Multi-Stage Detection Design
7. Model Optimization and Compression
8. Experimental Setup (multi-protocol testbed, datasets, methodology)
9. Results and Analysis
   - 9.1 Per-protocol detection performance
   - 9.2 Cross-protocol generalization results
   - 9.3 Ablation study (pipeline stages, feature layers, protocol identifier)
   - 9.4 Latency and resource overhead (per-protocol)
   - 9.5 Stress test degradation analysis
10. Discussion and Limitations
11. Conclusion and Future Work (AMQP, LwM2M, OPC-UA roadmap)

---

# 10. Expected Contribution

- **Protocol-normalized behavioral feature abstraction** that maps heterogeneous IoT protocol semantics (MQTT, CoAP) into a unified feature space — enabling a single ML model across protocols
- Standalone per-protocol reverse proxy architecture requiring **zero broker modification and zero protocol translation**
- Multi-stage lightweight AI detection pipeline (rule → ML → mitigation) operating on normalized features
- **Cross-protocol generalization analysis** — first quantitative study of behavioral feature transfer between MQTT and CoAP
- Protocol-aware feature set with **33-dimension unified vector** (15 normalized + 2 protocol ID + 16 auxiliary)
- Quantitative analysis of latency-security tradeoff with per-attack-class and **per-protocol** granularity
- Reproducible multi-protocol IoT attack testbed and labeled dataset
- **Extensible architecture** with documented `IProtocolModule` interface for adding protocols
- Deployable edge-native mitigation framework with open-source release

---

# 11. Explicit Exclusions (To Prevent Scope Creep)

- No protocols beyond MQTT and CoAP (AMQP, LwM2M, OPC-UA are future work)
- No protocol translation (MQTT stays MQTT, CoAP stays CoAP)
- No broker modification
- No deep transformer models
- No distributed multi-node architecture
- No cross-protocol message routing or bridging

Focus: Dual-protocol (MQTT + CoAP), behavioral normalization, rigorously evaluated system.

## 11.1 Future Work Roadmap

| Protocol           | Transport  | Pattern          | Normalization Complexity   | Priority |
| ------------------ | ---------- | ---------------- | -------------------------- | -------- |
| **AMQP**           | TCP        | Pub/Sub + Queue  | Medium (similar to MQTT)   | High     |
| **HTTP/WebSocket** | TCP        | Request/Response | Low (well-understood)      | Medium   |
| **LwM2M**          | CoAP-based | Client/Server    | Low (extends CoAP module)  | Medium   |
| **OPC-UA**         | TCP        | Client/Server    | High (complex type system) | Low      |

Each future protocol requires only: (1) a protocol parser, (2) a feature extractor, (3) a normalization mapping, and (4) registration with the shared framework.

---

# 12. Related Work Comparison Table

The Related Work section of the paper should include a comparison table to clearly show the contribution gap:

| System                             | Multi-Protocol | Protocol-Normalized Features | Edge-Deployable | Multi-Stage | No Broker Mod | No Protocol Translation | ML-Based | Open Source |
| ---------------------------------- | -------------- | ---------------------------- | --------------- | ----------- | ------------- | ----------------------- | -------- | ----------- |
| IoTSec frameworks                  | ✗              | ✗                            | ✓               | ✗           | ✓             | N/A                     | ✓        | Varies      |
| Broker plugin approaches           | ✗              | ✗                            | ✓               | ✗           | ✗             | N/A                     | ✗        | Varies      |
| Network-level IDS (Snort/Suricata) | Partial        | ✗                            | ✗               | ✗           | ✓             | N/A                     | ✗        | ✓           |
| Cloud-based ML detection           | Partial        | ✗                            | ✗               | ✗           | ✓             | N/A                     | ✓        | ✗           |
| Protocol translators/bridges       | ✓              | ✗                            | Varies          | ✗           | Varies        | ✗                       | ✗        | Varies      |
| **This Work**                      | **✓**          | **✓**                        | **✓**           | **✓**       | **✓**         | **✓**                   | **✓**    | **✓**       |

> Populate with specific systems discovered during literature review (e.g., MQTTGuard, SecMQTT, MQTT-S, CoAPShield).
> Key differentiator: This is the **first** system to normalize behavioral features across heterogeneous IoT protocols for a unified ML detection model without protocol translation.

---

# 13. Reproducibility Plan

To meet publication standards and enable independent verification:

- **Open-source release:** Publish proxy framework, both protocol modules, dashboard, and attack scripts on GitHub under MIT/Apache-2.0
- **Dataset release:** Publish the labeled multi-protocol dataset (MQTT + CoAP normalized features, raw features, and ground-truth labels)
- **Docker Compose testbed:** One-command reproducible environment:
  ```
  docker-compose up
  # Starts: Mosquitto, Californium, MQTT Proxy, CoAP Proxy, Dashboard,
  #         MQTT attack simulator, CoAP attack simulator
  ```
- **Hardware specification:** Document exact hardware used for benchmarks (CPU model, cores, RAM, OS version)
- **Experiment scripts:** Automated scripts to reproduce all experiments and generate figures/tables
- **Normalization validation scripts:** Tools to verify feature alignment across protocols
- **Protocol module template:** Documented template for adding new protocol modules

---

# 14. Target Publication Venues

| Venue                | Type           | Fit      | Notes                                         |
| -------------------- | -------------- | -------- | --------------------------------------------- |
| **IEEE IoT Journal** | Journal        | Strong   | Primary target; high impact for IoT security  |
| **IEEE Access**      | Journal (Open) | Strong   | Faster review cycle, open access              |
| **ACM SenSys**       | Conference     | Good     | If systems contribution is emphasized         |
| **NDSS / ACSAC**     | Security conf  | Good     | Requires rigorous threat model and evaluation |
| **IEEE INFOCOM**     | Conference     | Moderate | Networking angle                              |
| **arXiv**            | Preprint       | —        | Publish preprint immediately for visibility   |

> **Strategy:** Submit to arXiv first for timestamp and visibility, then target IEEE IoT Journal or IEEE Access as the primary venue.

---

End of Research Plan
