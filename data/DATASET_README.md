# SentriX Dual-Protocol IoT Attack Dataset

## Overview

This dataset accompanies the paper:

> **SentriX: A Middleware-Independent Multi-Stage Security Proxy for Heterogeneous IoT Protocols**
> Minhajul Haque Shafin, East West University, 2026.

It contains **11,209 labeled network event records** collected from a controlled dual-protocol IoT testbed spanning MQTT (TCP) and CoAP (UDP) traffic. Each record includes a 33-dimensional normalized behavioral feature vector, protocol metadata, and a ground-truth attack label.

## Dataset Statistics

| Property | Value |
|---|---|
| Total records | 11,209 |
| Features per record | 33 (f00–f32) |
| Metadata columns | 10 (run_id, scenario, label, rep, timestamp, protocol, direction, event, bytes, detail) |
| Total columns | 43 |
| Protocols | MQTT (6,669 records, 59.5%), CoAP (4,540 records, 40.5%) |
| Controlled runs | 21 |
| Collection period | March 2026 |

## Label Distribution

| Label | Count | Protocol | Description |
|---|---|---|---|
| `benign` | 3,321 | Both | Normal telemetry and request traffic |
| `mqtt_protocol_abuse` | 1,765 | MQTT | Malformed packets, SlowITe-style keepalive abuse |
| `mqtt_wildcard_abuse` | 1,605 | MQTT | Rapid wildcard subscription cycling (#, +) |
| `mqtt_publish_flood` | 1,518 | MQTT | High-rate PUBLISH flooding |
| `coap_request_flood` | 1,500 | CoAP | Rapid GET flooding against /.well-known/core |
| `coap_protocol_abuse` | 1,500 | CoAP | Malformed payloads, protocol violations |

## Run Structure

Each scenario was executed across **3 independent runs** (R1, R2, R3) to support grouped cross-validation. The `run_id` column uniquely identifies each run.

| Prefix | Protocol | Scenario |
|---|---|---|
| `MQ-BENIGN-R{1,2,3}` | MQTT | Benign telemetry publishing |
| `MQ-FLOOD-R{1,2,3}` | MQTT | Publish flood attack |
| `MQ-WILDCARD-R{1,2,3}` | MQTT | Wildcard subscription abuse |
| `MQ-MALFORM-R{1,2,3}` | MQTT | Protocol abuse / malformed packets |
| `CP-BENIGN-R{1,2,3}` | CoAP | Benign request mix |
| `CP-FLOOD-R{1,2,3}` | CoAP | Request flood |
| `CP-MALFORM-R{1,2,3}` | CoAP | Protocol abuse / malformed payloads |

## Feature Description

### Shared Behavioral Features (f00–f14, 15 dimensions)

| Feature | Name | Description | Normalization |
|---|---|---|---|
| f00 | msg_rate | Messages per second | min-max to [0,1] |
| f01 | payload_size | Message payload bytes | log1p to [0,1] |
| f02 | payload_entropy | Shannon entropy of byte distribution | [0,1] |
| f03 | inter_arrival_mean | Mean inter-packet delay | z-score clipped to [0,1] |
| f04 | inter_arrival_std | Std dev of inter-packet delay | z-score clipped to [0,1] |
| f05 | session_duration | Active session time (seconds) | clipped to [0,1] |
| f06 | qos_level | Quality-of-service abstraction | [0,1] |
| f07 | reconnection_rate | Reconnect frequency | [0,1] |
| f08 | unique_resource_count | Distinct topics/URIs in window | [0,1] |
| f09 | error_rate | Error response ratio | [0,1] |
| f10 | handshake_complexity | Connection setup overhead | [0,1] |
| f11 | subscription_breadth | Subscription/observe scope | [0,1] |
| f12 | resource_path_depth | Topic/URI hierarchy depth | [0,1] |
| f13 | resource_path_entropy | Shannon entropy of resource names | [0,1] |
| f14 | protocol_compliance | Well-formed message ratio | [0,1] |

### Protocol Identifier (f15–f16, 2 dimensions, one-hot)

| Feature | Name | Description |
|---|---|---|
| f15 | protocol_mqtt | 1.0 if MQTT, 0.0 otherwise |
| f16 | protocol_coap | 1.0 if CoAP, 0.0 otherwise |

### MQTT Auxiliary Features (f17–f24, 8 dimensions, zero-padded for CoAP)

| Feature | Name | Description |
|---|---|---|
| f17 | mqtt_retain_flag | Retain flag usage ratio |
| f18 | mqtt_wildcard_depth | Max wildcard nesting depth |
| f19 | mqtt_connect_disconnect_ratio | CONNECT/DISCONNECT ratio |
| f20 | mqtt_keep_alive_normalized | Keep-alive timer (normalized) |
| f21 | mqtt_will_message_presence | Will message flag ratio |
| f22 | mqtt_qos2_completion_ratio | QoS-2 handshake completion rate |
| f23 | mqtt_client_id_entropy | Shannon entropy of client IDs |
| f24 | mqtt_payload_size_variance | Payload size variance (normalized) |

### CoAP Auxiliary Features (f25–f32, 8 dimensions, zero-padded for MQTT)

| Feature | Name | Description |
|---|---|---|
| f25 | coap_con_ratio | Confirmable message ratio |
| f26 | coap_non_ratio | Non-confirmable message ratio |
| f27 | coap_ack_ratio | Acknowledgement ratio |
| f28 | coap_rst_ratio | Reset message ratio |
| f29 | coap_observe_registration_flag | Observe active flag |
| f30 | coap_blockwise_in_progress | Block-wise transfer active |
| f31 | coap_token_reuse_ratio | Token reuse frequency |
| f32 | coap_option_count | Average CoAP options per message |

## Collection Environment

- **MQTT Broker**: Eclipse Mosquitto v2 (TCP/1883)
- **CoAP Server**: Eclipse Californium (UDP/5683)
- **Proxy**: SentriX C++17 reverse proxy (MQTT TCP/1884, CoAP UDP/5684)
- **Attack Generators**: Python scripts using Paho MQTT and aiocoap
- **Infrastructure**: Docker Compose (5 services), deterministic local networking
- **OS**: Linux

## File Manifest

| File | Description |
|---|---|
| `week3_runs_labeled.csv` | Primary labeled dataset (11,209 records × 43 columns) |
| `lightgbm_full.onnx` | Trained LightGBM model exported to ONNX format (1.2 MB) |
| `train_baselines.py` | Training script for reproducing baseline model comparison |

## Usage

```python
import pandas as pd
from sklearn.model_selection import GroupKFold
from lightgbm import LGBMClassifier

df = pd.read_csv("week3_runs_labeled.csv")
feature_cols = [f"f{i:02d}" for i in range(33)]
X = df[feature_cols].values
y = df["label"].values
groups = df["run_id"].values

gkf = GroupKFold(n_splits=5)
for train_idx, test_idx in gkf.split(X, y, groups):
    model = LGBMClassifier(n_estimators=100, max_depth=7, num_leaves=31)
    model.fit(X[train_idx], y[train_idx])
    # evaluate on X[test_idx], y[test_idx]
```

## License

This dataset is released under the [Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

## Citation

If you use this dataset, please cite:

```bibtex
@inproceedings{shafin2026sentrix,
  title={SentriX: A Middleware-Independent Multi-Stage Security Proxy for Heterogeneous IoT Protocols},
  author={Shafin, Minhajul Haque},
  booktitle={Proc. IEEE Consumer Communications and Networking Conf. (CCNC)},
  year={2026}
}
```
