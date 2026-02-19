# Edge-Native Security for IoT

## A Lightweight Multi-Stage AI Reverse Proxy for MQTT

---

# 1. Research Scope (Narrowed)

This research will focus exclusively on:

- **Protocol:** MQTT
- **Backend Broker:** Eclipse Mosquitto
- **Deployment Model:** Standalone reverse proxy (no modification to broker internals)

CoAP and other protocols are explicitly excluded from the current scope and may be considered future work.

---

# 2. Core Research Objective

Design and evaluate a **protocol-aware, multi-stage AI reverse proxy** deployed in front of an MQTT broker that:

1. Detects application-layer attacks in real time
2. Maintains low latency overhead
3. Operates within constrained edge environments
4. Requires zero modification to the broker

This research proposes and rigorously evaluates a **standalone, protocol-aware, multi-stage AI reverse proxy for MQTT** that enables real-time mitigation of application-layer attacks at the network edge without modifying broker internals.

The central hypothesis is:

> A protocol-aware, multi-stage detection architecture deployed as an external reverse proxy can achieve high application-layer attack detection performance while introducing only marginal latency and resource overhead compared to a native MQTT broker.

The work seeks to formally quantify the **security–performance tradeoff** introduced by edge-native AI-based inspection in IoT environments.

# 2.5 Threat Model

## Adversary Capabilities

- Network-level: Can send arbitrary MQTT packets to the broker's port
- Application-level: Can craft valid or malformed MQTT control packets
- No physical access to the broker or proxy host

## Attack Taxonomy (Targeted)

1. **Volumetric:** Publish flood, connection exhaustion
2. **Protocol abuse:** Malformed packets, oversized payloads, rapid re-auth
3. **Semantic:** Topic squatting, payload injection with valid structure
4. **Slow-rate:** Low-and-slow DoS (e.g., SlowITe for MQTT)
5. **MQTT-Specific Exploits:**
   - **SlowITe** — Slow CONNECT attack exploiting MQTT keep-alive timer
   - **Wildcard subscription abuse** — Using `#` or `+` wildcards to exfiltrate data across topics
   - **QoS exploitation** — Abusing QoS 2 four-step handshake for amplification
   - **Will message abuse** — Crafting malicious Last Will and Testament (LWT) payloads
   - **Client ID spoofing** — Reusing or hijacking client identifiers to disrupt sessions

## Trust Boundaries

- IoT devices are **untrusted**
- Proxy ↔ Broker link is **trusted** (localhost or secured channel)
- Dashboard is read-only and behind authentication

---

# 3. System Architecture

## 3.1 High-Level Architecture

IoT Devices → C++ AI Proxy → Mosquitto Broker → Cloud
↓
Next.js Monitoring Dashboard

## 3.2 Proxy Responsibilities

The proxy will:

- Intercept all MQTT traffic
- Parse MQTT control packets
- Extract protocol-aware features
- Run multi-stage detection
- Forward or mitigate traffic
- Log metrics for analysis and visualization

---

# 4. Multi-Stage Detection Pipeline

## Stage 1: Fast Rule-Based Filter

Lightweight, constant-time checks:

- Payload size threshold
- Publish rate anomaly
- Topic blacklist check
- Topic entropy heuristic
- Connection burst detection

Goal: Filter obvious malicious traffic with negligible overhead.

## Stage 2: Lightweight ML Classifier

### Feature Set (Protocol-Aware)

**Basic Packet Features:**

- Topic length
- Payload length
- Publish frequency
- Inter-arrival time
- QoS level
- Retain flag
- Message size variance

**Per-Client Temporal Features:**

- Session duration
- CONNECT/DISCONNECT ratio
- Average session lifetime
- Reconnection frequency
- Time since last message

**Topic Behavioral Features:**

- Unique topic count per client
- Topic depth (number of `/` separators)
- Wildcard usage (`#`, `+`) in subscriptions
- Topic entropy (Shannon entropy of topic string)

**Cross-Client Features:**

- Number of clients publishing to same topic
- Topic collision rate
- Concurrent connection count

**Payload Statistical Features:**

- Shannon entropy of payload bytes
- Payload byte distribution histogram (compressed)
- Payload-to-topic size ratio

**Protocol Compliance Features:**

- Invalid packet ratio per client
- Out-of-order control packet count
- Keep-alive violation count

### Candidate Models

- Random Forest
- LightGBM
- Small MLP (fully connected neural network)

Selection criteria:

- Detection accuracy
- F1 score
- Inference latency
- Memory footprint

Model will be exported to ONNX or lightweight C++ inference runtime.

## Stage 3: Adaptive Mitigation

Actions:

- Forward traffic
- Drop packet
- Rate limit client
- Temporary client quarantine

Mitigation decisions will be logged for evaluation.

---

# 5. Dataset & Training Strategy

## 5.1 Dataset Options

- BoT-IoT dataset (network-flow level; requires MQTT feature extraction from raw pcaps)
- CIC IoT dataset (network-flow level; same extraction requirement)
- **Custom MQTT traffic simulation (primary — see 5.3)**

> **Note:** BoT-IoT and CIC IoT are not MQTT-specific. They operate at the network-flow level and lack application-layer MQTT features. The custom testbed dataset is the primary data source; public datasets serve as supplementary baselines.

## 5.2 Training Workflow

1. Collect MQTT traffic from custom testbed (see 5.3)
2. Extract MQTT-level features per the feature set defined in Section 4
3. Label traffic using ground-truth attack scripts
4. Train candidate models in Python (scikit-learn, LightGBM)
5. Evaluate with 5-fold stratified cross-validation
6. Apply model compression (quantization/pruning)
7. Export optimized model to ONNX for C++ inference

## 5.3 Custom MQTT Testbed

Build a reproducible testbed for labeled dataset generation:

```
MQTT Clients (Eclipse Paho) → AI Proxy → Mosquitto Broker
       ↑
  Attack Scripts (mqtt-pwn, custom Python scripts)
```

**Benign traffic generation:**

- Simulated IoT sensors (temperature, humidity, motion) publishing on realistic topic hierarchies
- Varying publish rates, QoS levels, and payload sizes

**Attack traffic generation:**

- Publish flood (high-rate PUBLISH from multiple clients)
- SlowITe (slow CONNECT with extended keep-alive)
- Malformed packet injection (invalid headers, oversized payloads)
- Connection exhaustion (rapid CONNECT without DISCONNECT)
- Wildcard subscription abuse (`#` subscription to exfiltrate)
- QoS 2 amplification (incomplete PUBREL handshakes)

**Labeling:** Each attack script tags its traffic window with ground-truth labels. Proxy logs are post-processed to create the labeled feature dataset.

---

# 6. Implementation Plan

## 6.1 C++ Proxy Core

### Architecture Pattern

- Event-driven, single-threaded main loop with `epoll` (Linux) for async I/O
- Zero-copy buffer management for MQTT packet parsing where possible
- Stateful per-connection parser (handles fragmented TCP segments correctly)

### Core Components

- **TCP Listener:** Accepts inbound connections, manages connection lifecycle
- **MQTT Packet Parser:** Stateful, streaming parser for MQTT v3.1.1 (v5.0 as stretch goal)
- **Feature Extraction Module:** Computes per-packet and per-session features defined in Section 4
- **ML Inference Engine:** ONNX Runtime (C++ API) for neural models; custom native inference for tree models
- **Routing & Mitigation Logic:** Forward, drop, rate-limit, or quarantine decisions per Stage 3
- **Metrics Collector:** Aggregates throughput, latency, detection stats for export

### Dependencies

| Component     | Library                             |
| ------------- | ----------------------------------- |
| Networking    | Boost.Asio or raw `epoll`           |
| ML Inference  | ONNX Runtime C++ API                |
| Serialization | nlohmann/json or FlatBuffers        |
| Logging       | spdlog (lock-free, zero-allocation) |
| Build System  | CMake                               |

### Thread Model

- **Main thread:** Accept connections + I/O event loop + rule-based filtering (Stage 1)
- **Inference thread(s):** ML inference offloaded if per-packet latency exceeds threshold
- **Metrics thread:** Periodic stats export via REST endpoint or Unix domain socket

### MQTT Packet Types Handled

- CONNECT / CONNACK
- PUBLISH / PUBACK / PUBREC / PUBREL / PUBCOMP
- SUBSCRIBE / SUBACK
- UNSUBSCRIBE / UNSUBACK
- PINGREQ / PINGRESP
- DISCONNECT

## 6.2 Dashboard (Next.js)

Displays:

- Message throughput
- Detected attacks
- Mitigation actions
- Latency overhead
- CPU and memory usage

Dashboard connects to proxy API endpoint.

---

# 7. Experimental Evaluation Plan

## 7.1 Baselines

1. Mosquitto without proxy
2. Proxy with rule-only detection
3. Full multi-stage proxy

## 7.2 Metrics

Security Metrics:

- Detection accuracy
- Precision, Recall, F1 score (macro and per-attack-class)
- False positive rate (FPR)
- ROC-AUC curves per model
- Confusion matrix per model per attack class

Performance Metrics:

- End-to-end latency overhead: **p50, p95, p99** (not just mean)
- Throughput (messages/sec)
- CPU utilization
- Memory usage (RSS, peak)

## 7.3 Evaluation Rigor

- **5-fold stratified cross-validation** for all model comparisons
- **Per-attack-type detection rates** (not just aggregate)
- **Statistical significance testing** between models (McNemar's test or paired t-test)
- **Ablation study:** measure contribution of each pipeline stage independently
  - Stage 1 only vs. Stage 1+2 vs. Full pipeline
- **Resource profiling:** measure inference time per packet for each model

## 7.4 Stress Testing

Simulate:

- High-frequency publish flood (10k+ msg/sec)
- SlowITe attack (slow CONNECT with keep-alive exploitation)
- Malformed payload injection (invalid headers, oversized payloads)
- Connection exhaustion attack (rapid CONNECT without DISCONNECT)
- Wildcard subscription abuse (`#` topic exfiltration)
- QoS 2 amplification (incomplete handshake flood)

Measure degradation curves: throughput vs. attack intensity, latency vs. attack intensity.

---

# 8. Timeline (10 Weeks)

## Week 1

- Finalize research objective and threat model
- Review related work, build comparison table
- Define feature set

## Week 2

- Set up MQTT testbed (Mosquitto, Paho clients, attack scripts)
- Build data collection pipeline
- Begin benign + attack traffic generation

## Week 3

- Complete dataset collection and labeling
- Feature engineering and extraction pipeline

## Week 4

- Train candidate models (Random Forest, LightGBM, MLP)
- 5-fold cross-validation, per-attack-class evaluation

## Week 5

- Model selection based on accuracy-latency tradeoff
- Model compression (quantization/pruning)
- Export to ONNX

## Week 6–7

- Implement C++ proxy core (TCP listener, MQTT parser, feature extraction)
- Integrate ML inference engine (ONNX Runtime)
- Implement rule-based filter (Stage 1) and mitigation logic (Stage 3)

## Week 8

- Implement Next.js monitoring dashboard
- Integration testing (end-to-end proxy + broker + dashboard)

## Week 9

- Run all experiments and stress tests
- Collect latency, throughput, detection metrics
- Generate figures, tables, ROC curves

## Week 10

- Write and finalize paper
- Prepare reproducibility artifacts (Docker, scripts, dataset)

---

# 9. Paper Structure

1. Introduction
2. Related Work (include comparison table — see Section 12)
3. Threat Model
4. System Architecture
5. Multi-Stage Detection Design
6. Model Optimization and Compression
7. Experimental Setup (testbed, dataset, methodology)
8. Results and Analysis (per-attack-class, ablation, stress tests)
9. Discussion and Limitations
10. Conclusion and Future Work

---

# 10. Expected Contribution

- Standalone MQTT reverse proxy architecture requiring zero broker modification
- Multi-stage lightweight AI detection pipeline (rule → ML → mitigation)
- Protocol-aware feature set with 20+ MQTT-specific features
- Quantitative analysis of latency-security tradeoff with per-attack-class granularity
- Reproducible MQTT attack testbed and labeled dataset
- Deployable edge-native mitigation framework with open-source release

---

# 11. Explicit Exclusions (To Prevent Scope Creep)

- No multi-protocol support
- No broker modification
- No deep transformer models
- No distributed multi-node architecture

Focus: Single-node, MQTT-focused, rigorously evaluated system.

---

# 12. Related Work Comparison Table

The Related Work section of the paper should include a comparison table to clearly show the contribution gap:

| System                             | Protocol-Aware | Edge-Deployable | Multi-Stage | No Broker Mod | ML-Based | Open Source |
| ---------------------------------- | -------------- | --------------- | ----------- | ------------- | -------- | ----------- |
| IoTSec frameworks                  | ✗              | ✓               | ✗           | ✓             | ✓        | Varies      |
| Broker plugin approaches           | ✓              | ✓               | ✗           | ✗             | ✗        | Varies      |
| Network-level IDS (Snort/Suricata) | ✗              | ✗               | ✗           | ✓             | ✗        | ✓           |
| Cloud-based ML detection           | ✗              | ✗               | ✗           | ✓             | ✓        | ✗           |
| **This Work**                      | **✓**          | **✓**           | **✓**       | **✓**         | **✓**    | **✓**       |

> Populate with specific systems discovered during literature review (e.g., MQTTGuard, SecMQTT, MQTT-S).

---

# 13. Reproducibility Plan

To meet publication standards and enable independent verification:

- **Open-source release:** Publish proxy code, dashboard, and attack scripts on GitHub under MIT/Apache-2.0
- **Dataset release:** Publish the labeled MQTT dataset (or generation scripts if privacy constraints apply)
- **Docker Compose testbed:** One-command reproducible environment:
  ```
  docker-compose up   # Starts: Mosquitto, AI Proxy, Dashboard, Attack simulator
  ```
- **Hardware specification:** Document exact hardware used for benchmarks (CPU model, cores, RAM, OS version)
- **Experiment scripts:** Automated scripts to reproduce all experiments and generate figures/tables

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
