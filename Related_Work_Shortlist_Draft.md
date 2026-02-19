# Related Work Shortlist Draft (for Section 12)

This draft is structured to help you quickly populate the comparison table in `Research_plan.md` Section 12.

---

## 1) How to Use This Draft

- Treat this as a **screening list** of high-relevance categories and candidate systems.
- For each candidate, confirm final details from the original paper/repository before submission.
- Use the mapping matrix in Section 3 to score each system against your columns:
  - Multi-Protocol
  - Protocol-Normalized Features
  - Edge-Deployable
  - Multi-Stage
  - No Broker Mod
  - No Protocol Translation
  - ML-Based
  - Open Source

---

## 2) Candidate Systems by Category

## A. MQTT-focused security systems (closest protocol-level baseline)

### A1. MQTTGuard (candidate)
- Likely positioning: MQTT-focused intrusion/anomaly detection for broker traffic.
- Why relevant: Strong baseline for protocol-aware but single-protocol detection.
- Expected gaps vs your work:
  - Not cross-protocol (MQTT-only)
  - No unified MQTT+CoAP normalization layer

### A2. SecMQTT (candidate)
- Likely positioning: Secure MQTT architecture / monitoring / broker-side defense.
- Why relevant: Good baseline for security-hardening and detection in MQTT ecosystem.
- Expected gaps vs your work:
  - Typically broker-coupled or protocol-specific
  - Usually no heterogeneous normalization objective

### A3. MQTT-S / MQTT IDS variants (candidate family)
- Likely positioning: Rule-based or ML-assisted MQTT abuse detection.
- Why relevant: Baseline for attacks like flood, malformed packets, wildcard abuse.
- Expected gaps vs your work:
  - Mostly MQTT-only
  - Often no explicit edge reverse-proxy abstraction across protocols

## B. CoAP-focused security systems

### B1. CoAPShield (candidate)
- Likely positioning: CoAP attack detection/mitigation (Observe abuse, flooding, malformed options).
- Why relevant: CoAP-side baseline against your CoAP module.
- Expected gaps vs your work:
  - CoAP-only
  - No shared model with MQTT

### B2. CoAP IDS / DTLS-aware CoAP defenses (candidate family)
- Likely positioning: Rule/behavioral detection around CoAP semantics.
- Why relevant: Captures protocol-native abuse classes in your threat model.
- Expected gaps vs your work:
  - No protocol-normalized feature space across heterogeneous protocols

## C. Broker-plugin and broker-integrated approaches

### C1. Broker plugin defenses (Mosquitto/EMQX/HiveMQ plugin ecosystems)
- Likely positioning: Authentication, ACL, rate limiting, custom hooks.
- Why relevant: Strong practical baselines used in production.
- Expected gaps vs your work:
  - Requires broker-level integration/modification path
  - Usually not protocol-agnostic or cross-protocol

### C2. Broker-side anomaly modules (vendor/community)
- Likely positioning: In-broker policy and behavioral checks.
- Why relevant: Competes directly on deployment practicality.
- Expected gaps vs your work:
  - Tied to broker internals
  - Harder to generalize across MQTT and CoAP backends uniformly

## D. Network-level IDS/IPS baselines

### D1. Snort
- Why relevant: Common signature baseline.
- Expected gaps vs your work:
  - Limited application-semantic normalization across MQTT/CoAP behavior dimensions

### D2. Suricata
- Why relevant: Modern network IDS/IPS with protocol parsers and high throughput.
- Expected gaps vs your work:
  - Primarily packet/signature/flow-oriented; not your explicit normalized behavioral abstraction

### D3. Zeek
- Why relevant: Rich network telemetry and scripting for anomaly logic.
- Expected gaps vs your work:
  - Typically network-monitor architecture, not dedicated per-protocol reverse-proxy ML pipeline

## E. Cloud/centralized IoT ML anomaly detection

### E1. Cloud-side IoT anomaly frameworks (generic category)
- Why relevant: Useful ML baselines for accuracy comparisons.
- Expected gaps vs your work:
  - Not edge-native
  - Often protocol-agnostic at flow level but not protocol-semantic normalization for in-line mitigation

## F. Protocol gateways/translators/bridges

### F1. MQTT-CoAP bridges and IoT gateways (generic category)
- Why relevant: Frequently claimed as “multi-protocol.”
- Expected gaps vs your work:
  - Multi-protocol through translation, not through unified behavioral abstraction
  - Can violate your “no protocol translation” design constraint

---

## 3) Draft Mapping Matrix (Fill after paper-level verification)

Use this matrix as a working sheet before finalizing your camera-ready table.

| System / Family | Multi-Protocol | Protocol-Normalized Features | Edge-Deployable | Multi-Stage | No Broker Mod | No Protocol Translation | ML-Based | Open Source | Notes to verify |
|---|---|---|---|---|---|---|---|---|---|
| MQTTGuard (candidate) | ✗ | ✗ | ✓ | ? | ? | N/A | ? | ? | Confirm architecture and artifact availability |
| SecMQTT (candidate) | ✗ | ✗ | ✓ | ? | ? | N/A | ? | ? | Confirm whether plugin/in-broker |
| MQTT IDS variants | ✗ | ✗ | ✓ | ? | ? | N/A | varies | varies | Pick 1–2 canonical references |
| CoAPShield (candidate) | ✗ | ✗ | ✓ | ? | ? | N/A | ? | ? | Confirm specific mitigation scope |
| CoAP IDS variants | ✗ | ✗ | ✓ | ? | ? | N/A | varies | varies | Include Observe/token abuse handling |
| Broker plugin approaches | ✗ | ✗ | ✓ | ✗ | ✗ | N/A | varies | varies | Mosquitto/EMQX/HiveMQ plugin examples |
| Snort | Partial | ✗ | ✗/Partial | ✗ | ✓ | N/A | ✗ | ✓ | Clarify deployment mode used in your baseline |
| Suricata | Partial | ✗ | ✗/Partial | ✗ | ✓ | N/A | ✗ | ✓ | Note protocol parser limitations for semantics |
| Zeek | Partial | ✗ | ✗/Partial | ✗ | ✓ | N/A | ✗/Partial | ✓ | Scripted analytics but not your architecture |
| Cloud IoT ML systems | Partial | ✗ | ✗ | ✗ | ✓ | N/A | ✓ | varies | Select one representative paper |
| Protocol translators/bridges | ✓ | ✗ | varies | ✗ | varies | ✗ | ✗/Partial | varies | Distinguish translation vs normalization |
| **This Work** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** | Unified model over normalized MQTT+CoAP behavior |

---

## 4) Suggested “Final 8” for the Paper Table

To keep Section 12 concise, use one representative from each bucket:

1. MQTT-specific ML/IDS paper (representative)
2. CoAP-specific IDS/mitigation paper (representative)
3. Broker plugin approach (representative)
4. Snort
5. Suricata (or Zeek, choose one if table space is tight)
6. Cloud IoT ML anomaly framework (representative)
7. Protocol translator/bridge framework (representative)
8. **This Work**

This avoids a bloated table and makes your novelty argument cleaner.

---

## 5) Fast Literature Query Strings (for verification pass)

Use these search strings to lock final references quickly:

- "MQTT intrusion detection machine learning broker"
- "MQTT wildcard subscription abuse detection"
- "CoAP intrusion detection Observe attack"
- "CoAP token exhaustion detection"
- "IoT broker plugin security MQTT Mosquitto"
- "Suricata MQTT CoAP protocol parser"
- "Zeek MQTT CoAP analysis"
- "IoT anomaly detection edge vs cloud"
- "MQTT CoAP gateway protocol translation security"

---

## 6) Draft Positioning Paragraph (Drop-in for Related Work)

Existing IoT security systems are predominantly either protocol-specific (e.g., MQTT-only or CoAP-only), broker-integrated (plugin-based), or network-level IDS frameworks that operate on packet/flow semantics rather than protocol-normalized behavioral abstractions. Multi-protocol systems typically rely on protocol translation or gateway bridging rather than preserving protocol-native traffic while learning in a unified feature space. In contrast, this work introduces per-protocol reverse proxies with no broker modification and no protocol translation, coupled through a normalized behavioral feature layer that enables a single joint ML model across MQTT and CoAP.

---

## 7) Finalization Checklist

- Replace each “candidate” with a verified citation (paper title, venue, year)
- Confirm open-source status and repository link
- Confirm whether architecture is edge deployable or cloud-centric
- Confirm whether system requires broker modification
- Confirm whether “multi-protocol” means translation (bridge) vs unified detection model
- Freeze table values only after source-level verification

---

Prepared for: `Cross-Protocol Behavioral Anomaly Detection at the Edge` project.
