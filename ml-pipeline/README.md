# ML Pipeline: Comprehensive Reference Guide

**Purpose:** Train, validate, and deploy machine learning models for IoT protocol anomaly detection

**Status:** Production-ready (Week 10 complete, all models trained and evaluated)

**Last Updated:** April 7, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [End-to-End Data & ML Workflow](#end-to-end-data--ml-workflow)
3. [Dataset Generation](#dataset-generation)
4. [Feature Engineering](#feature-engineering)
5. [Model Training](#model-training)
6. [Model Evaluation](#model-evaluation)
7. [Scripts Reference](#scripts-reference)
8. [Directory Structure](#directory-structure)
9. [Results & Artifacts](#results--artifacts)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose of This Pipeline

The ML pipeline is responsible for:

1. **Data Preparation** — Converting raw proxy events into structured feature vectors
2. **Feature Engineering** — Extracting 33 behavioral features from MQTT/CoAP traffic
3. **Model Training** — Training 4 baseline models (LogisticRegression, RandomForest, MLP, LightGBM)
4. **Model Evaluation** — Assessing performance via grouped cross-validation and cross-protocol tests
5. **Statistical Analysis** — Computing confidence intervals, pairwise tests, effect sizes
6. **Model Export** — Converting trained models to ONNX format for C++ deployment
7. **Visualization** — Generating publication-quality figures

### Key Metrics

| Metric | Value |
|--------|-------|
| Dataset Size | 11,209 labeled events |
| Feature Dimensions | 33 (normalized [0.0, 1.0]) |
| Number of Classes | 6 (benign + 5 attack types) |
| Models Trained | 4 (LogReg, RF, MLP, LightGBM) |
| Evaluation Method | 5-fold grouped cross-validation |
| Best Model | LightGBM (F1-macro: 0.598, Accuracy: 0.780) |
| Cross-Protocol F1 | ~0.08 (weak generalization, noted) |
| Deployed Format | ONNX (lightgbm_full.onnx) |

---

## End-to-End Data & ML Workflow

### Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Raw Event Capture (C++ Proxy)                │
│  MQTT/CoAP traffic → timestamp, protocol, event type, bytes     │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│              /tmp/sentrix_events.jsonl (raw logs)
│
├─────────────────────────────────────────────────────────────────┤
│              Step 1: Manual Event Labeling (Human)              │
│  Classify each event as: benign or attack_type                 │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│         data/raw/proxy_events_labeled.csv (11,209 rows)
│  Columns: run_id, scenario, label, rep, timestamp, protocol, ...
│
├─────────────────────────────────────────────────────────────────┤
│         Step 2: Feature Extraction [export_events_to_dataset]   │
│  Convert raw events → 33-dimensional normalized vectors        │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│       data/features/unified_features.csv (33 feature columns)
│  f00-f32 (normalized [0.0, 1.0]), all metadata preserved
│
├─────────────────────────────────────────────────────────────────┤
│      Step 3: Feature Quality Validation [validate_feature_quality]
│  Check distributions, class balance, KL divergence             │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/reports/{feature_summary, kl_alignment}*.csv
│  + Markdown report with visualizations
│
├─────────────────────────────────────────────────────────────────┤
│    Step 4: Model Training & Evaluation [train_baselines]       │
│  5-fold grouped CV + cross-protocol evaluation                 │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/reports/week5_baseline_{metrics, summary, results}
│  Results for 4 models × 2 feature sets × 3 evaluation splits
│
├─────────────────────────────────────────────────────────────────┤
│   Step 5: Champion Model Training [week6_train_champion]       │
│  Train LightGBM on full dataset (highest F1-macro)             │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/models/lightgbm_full.pkl (Python serizlied model)
│  Ready for batch inference and ONNX export
│
├─────────────────────────────────────────────────────────────────┤
│       Step 6: Model Export [week6_export_onnx]                 │
│  Convert champion model to ONNX for C++ runtime                │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/models/lightgbm_full.onnx (~1.8 MB)
│  Ready for deployment in proxy-core/src/detection_pipeline.cpp
│
├─────────────────────────────────────────────────────────────────┤
│   Step 7: Statistical Analysis [week11_statistical_analysis]   │
│  Bootstrap CIs, pairwise tests, effect sizes                   │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/reports/week11_statistical_analysis.json
│  Confidence intervals, p-values, Cohen's d
│
├─────────────────────────────────────────────────────────────────┤
│    Step 8: Paper Figure Generation [week11_generate_figures]   │
│  Reproduce all 7 publication-quality figures                   │
├─────────────────────────────────────────────────────────────────┤
│                              ↓
│  ml-pipeline/figures/fig[1-7]_*.png (publication ready)
│  Model comparison, generalization, per-class metrics, etc.
└─────────────────────────────────────────────────────────────────┘
```

---

## Dataset Generation

### Stage 1: Raw Event Collection

**Source:** C++ proxy (proxy-core/src/main.cpp)

**Process:**
1. Proxy receives MQTT/CoAP traffic on ingress ports
2. Protocol modules parse packets
3. Events are logged to: `/tmp/sentrix_events.jsonl`
4. One JSON object per line (JSONL format)

**Event Format:**
```json
{
  "timestamp": "2026-02-26T15:51:17Z",
  "protocol": "mqtt",
  "direction": "incoming",
  "event": "traffic",
  "bytes": 14,
  "detail": "client_to_broker",
  "source_id": "client_123",
  "destination": "broker"
}
```

**Duration:** Collection runs continuously while proxy is active (can span days/weeks)

### Stage 2: Event Labeling (Manual)

**Input:** Raw events from `/tmp/sentrix_events.jsonl`

**Process:**
1. Human reviewer examines each event
2. Classify as:
   - `benign` — normal traffic pattern
   - `mqtt_protocol_abuse` — malformed MQTT packet
   - `mqtt_wildcard_abuse` — topic path traversal attempt
   - `mqtt_publish_flood` — high-frequency publish (volumetric)
   - `coap_protocol_abuse` — malformed CoAP option/token
   - `coap_request_flood` — rapid CoAP requests (volumetric)

3. Add labels to CSV with metadata:
   - `run_id` — unique run identifier (e.g., "MQ-BENIGN-R1")
   - `scenario` — test scenario name
   - `label` — attack class (6 classes)
   - `rep` — repetition number
   - `protocol` — MQTT or CoAP

**Output:** `data/raw/proxy_events_labeled.csv`

**Example Rows:**
```csv
run_id,scenario,label,rep,timestamp,protocol,direction,event,bytes,detail
MQ-BENIGN-R1,mqtt_benign,benign,1,2026-02-26T15:51:16Z,mqtt,internal,module_start,0,proxy online
MQ-BENIGN-R1,mqtt_benign,benign,1,2026-02-26T15:51:17Z,mqtt,incoming,connection_open,0,client accepted
MQ-BENIGN-R1,mqtt_benign,benign,1,2026-02-26T15:51:17Z,mqtt,incoming,traffic,14,client_to_broker
MQ-FLOOD-R1,mqtt_publish_flood,mqtt_publish_flood,1,2026-02-27T10:20:44Z,mqtt,incoming,traffic,512,client_to_broker
```

**Dataset Statistics:**
- **Total Events:** 11,209 rows
- **MQTT Events:** 6,512 (58%)
- **CoAP Events:** 4,697 (42%)
- **Benign:** 4,600 (41%)
- **Attack Samples:** 6,609 (59%)
- **Distinct Runs:** 21 (matrix design)

### Stage 3: Dataset Export (from Proxy API)

If collecting data via running proxy, export events programmatically:

```bash
python ml-pipeline/src/export_events_to_dataset.py \
  --events-api http://localhost:8080/events \
  --out data/raw/proxy_events.csv \
  --run-id MQ-BENIGN-R1 \
  --scenario mqtt_benign \
  --label benign \
  --rep 1
```

**Parameters:**
- `--events-api`: HTTP endpoint to fetch events from
- `--out`: Output CSV file path
- `--run-id`: Unique identifier for this test run
- `--scenario`: Scenario name (for grouping)
- `--label`: Ground-truth class label
- `--rep`: Repetition number
- `--append`: If set, append to existing CSV (don't overwrite)

**Output:** Rows appended to `data/raw/proxy_events.csv` with all metadata

---

## Feature Engineering

### Overview

**Goal:** Convert raw events → 33-dimensional feature vectors (normalized to [0.0, 1.0])

**Process:**
1. Read labeled events CSV
2. For each event, extract behavioral metrics:
   - Message rate, payload size distribution
   - Inter-packet delays, entropy
   - Protocol-specific indicators (QoS, topics, options)
3. Normalize to [0.0, 1.0] range per feature
4. Write to CSV with features f00-f32 plus metadata

### 33-Dimensional Feature Space

**Core Behavioral Features (f00–f14, shared across protocols):**

| Feature | Name | Description | Computation |
|---------|------|-------------|-------------|
| f00 | message_rate_norm | Messages per second (normalized) | count(msgs) / time_window |
| f01 | payload_avg_size_norm | Average message size (normalized) | sum(bytes) / count(msgs) / max_size |
| f02 | payload_entropy | Shannon entropy of byte distribution | -Σ(p_i * log(p_i)) |
| f03 | inter_packet_delay_mean | Mean time between consecutive packets (sec) | mean(t_i+1 - t_i) |
| f04 | inter_packet_delay_std | Std dev of inter-packet delays | std(t_i+1 - t_i) |
| f05 | connection_duration_norm | Session length (seconds, normalized) | (t_end - t_start) / max_window |
| f06 | client_to_server_ratio | Upstream vs downstream traffic | count(incoming) / count(outgoing) |
| f07 | distinct_sources_norm | Unique sender identities | distinct(source_id) / max_sources |
| f08 | retry_rate | Packet retransmissions | count(retransmit) / count(total) |
| f09 | avg_payload_fragmentation | Fragment count per message | count(fragments) / count(msgs) |
| f10 | control_message_ratio | Control vs data messages | count(control) / count(total) |
| f11 | idle_time_proportion | Fraction of session idle | time(idle) / time(total) |
| f12 | qos_mix_entropy | QoS level distribution entropy (MQTT) | -Σ(p_QoS * log(p_QoS)) |
| f13 | topic_cardinality | Distinct topics/resources accessed | distinct(topics) / count(msgs) |
| f14 | byte_distribution_entropy | Entropy across response codes | -Σ(p_code * log(p_code)) |

**Protocol ID Encoding (f15–f16, one-hot):**
```
MQTT: [1.0, 0.0]
CoAP:  [0.0, 1.0]
```

**MQTT-Specific Features (f17–f24):**

| Feature | Name | Description |
|---------|------|-------------|
| f17 | connect_rate | CONNECT packets per time window |
| f18 | subscribe_pattern_entropy | Entropy of subscription patterns |
| f19 | will_flag_presence | % of CONNECT packets with will flag |
| f20 | client_id_entropy | Entropy of client ID distribution |
| f21 | username_presence | % of packets with authentication |
| f22 | password_presence | % of packets with password field |
| f23 | keep_alive_ratio | Keepalive pings vs total messages |
| f24 | clean_session_ratio | Clean session flag presence |

**CoAP-Specific Features (f25–f32):**

| Feature | Name | Description |
|---------|------|-------------|
| f25 | method_distribution | Entropy of CoAP method types (GET/POST/etc.) |
| f26 | option_cardinality | Distinct CoAP options used |
| f27 | token_reuse | Same token across multiple requests |
| f28 | observe_ratio | Observe notifications vs requests |
| f29 | block_transfer_ratio | Block1/Block2 fragmentation usage |
| f30 | ecc_key_negotiation | DTLS handshake activity |
| f31 | response_time_distribution | RTT entropy |
| f32 | empty_ack_ratio | Empty ACK messages vs total |

### Feature Extraction Script

**Script:** `ml-pipeline/src/export_events_to_dataset.py`

**Purpose:** Convert labeled events CSV → feature matrix CSV

**Inputs:**
- `data/raw/proxy_events_labeled.csv` (11,209 rows)

**Process:**
1. Read labeled events
2. Group by `run_id` (21 distinct runs)
3. For each run:
   - Extract message-level features
   - Aggregate over time windows
   - Compute protocol-specific indicators
4. Normalize each feature to [0.0, 1.0]
5. Write feature matrix

**Output:**
- `data/features/unified_features.csv` (11,209 rows × 43 columns)

**Example Usage:**

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

python ml-pipeline/src/export_events_to_dataset.py \
  --input data/raw/proxy_events_labeled.csv \
  --output data/features/unified_features.csv \
  --normalize
```

**Output Columns:**
```
run_id, scenario, label, rep, timestamp, protocol, direction, event, bytes, detail,
f00, f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13, f14,
[protocol_id_1], [protocol_id_2],
f17, f18, f19, f20, f21, f22, f23, f24,  [MQTT auxiliary]
f25, f26, f27, f28, f29, f30, f31, f32   [CoAP auxiliary]
```

**Verification:**
```bash
# Check output file
wc -l data/features/unified_features.csv  # Should be 11,210 (11,209 + header)

# Check feature ranges
python -c "
import pandas as pd
df = pd.read_csv('data/features/unified_features.csv')
print(df[['f00', 'f01', 'f32']].describe())
# All features should have min ~0.0, max ~1.0
"
```

---

## Feature Quality Validation

### Purpose

Ensure extracted features have:
- Appropriate distributions (no extreme skew)
- Good class separation (attack ≠ benign)
- Consistent protocol alignment (features stable across MQTT/CoAP)

### Script: `validate_feature_quality.py`

**Purpose:** Analyze feature distributions and cross-protocol alignment

**Input:** `data/features/unified_features.csv`

**Process:**
1. Load feature matrix
2. For each feature:
   - Compute mean, std, min, max, skewness
   - Check for outliers
3. Per-class statistics:
   - Per-attack-type feature distributions
4. Cross-protocol KL divergence:
   - Compare MQTT vs CoAP feature distributions per class
   - High KL = feature drifts across protocols
   - Low KL = feature aligned across protocols

**Output Files:**

| File | Contents |
|------|----------|
| `feature_summary_overall.csv` | Mean, std, min, max per feature |
| `feature_summary_by_protocol.csv` | Same, but stratified by protocol |
| `kl_alignment_by_class.csv` | KL divergence (MQTT vs CoAP) per feature per class |
| `week3_feature_quality.md` | Markdown report with visualizations |

### Example Run

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

python ml-pipeline/src/validate_feature_quality.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week3_feature_quality.md
```

**Expected Output:**
```
Feature Quality Validation Report
==================================

Processing 11209 samples across 33 features...

Feature Summary (Overall):
   Feature    Mean    Std    Min    Max  Skewness
   f00       0.215  0.103  0.000  0.800    1.234
   f01       0.312  0.087  0.001  0.995    0.456
   f02       0.412  0.156  0.002  0.999    0.789
   ...

Cross-Protocol KL Divergence (Top Drifting Features):
   Feature    KL(MQTT||CoAP)    Interpretation
   f24       0.644             MQTT-specific (clean session ratio)
   f12       0.599             QoS-specific to MQTT
   f01       0.487             Payload size differs across protocols
   ...

Outputs written to:
  - ml-pipeline/reports/feature_summary_overall.csv
  - ml-pipeline/reports/feature_summary_by_protocol.csv
  - ml-pipeline/reports/kl_alignment_by_class.csv
```

### Key Insights

- **High KL features** (f12, f24): Protocol-specific → expected
- **Low KL features** (f00–f10): Behavioral → good for cross-protocol generalization
- **Class separation:** Benign cluster separate from attack clusters → good

---

## Model Training

### Training Overview

**Goal:** Train 4 ML models using 5-fold grouped cross-validation

**Models:**
1. **LogisticRegression** — Linear baseline
2. **RandomForest** — Tree-based ensemble (50 trees)
3. **MLPClassifier** — Neural network (hidden layers: 100, 50)
4. **LightGBMClassifier** — Gradient boosting trees

**Evaluation Method:** Grouped 5-Fold Cross-Validation
- **Grouped By:** `run_id` (prevents run leakage)
- **Train/Test Split:** 80%/20% per fold
- **Stratification:** Balanced by class label

**Feature Sets Tested:**
1. `normalized_plus_pid` — f00–f14 (behavioral) + protocol ID (f15–f16)
2. `full` — All 33 features (includes auxiliary features)

**Metrics Computed:**
- Accuracy, F1-macro, F1-weighted (per fold)
- Per-class precision, recall, F1
- Confusion matrix
- Best overall model selection

### Script: `train_baselines.py`

**Purpose:** Train and evaluate all 4 models with cross-validation

**Inputs:**
- `data/features/unified_features.csv` (or labeled events CSV)

**Process:**
1. Load feature matrix
2. Split by feature set (`normalized_plus_pid`, `full`)
3. For each feature set:
   - For each model:
     - Perform 5-fold grouped CV:
       - Train on fold 1–4 (80% of runs)
       - Test on fold 5 (20% of runs)
       - Compute metrics
     - Also evaluate on all data (train=test, sanity check)
     - Also evaluate cross-protocol (train MQTT, test CoAP; vice versa)
4. Aggregate results across all folds/models

**Output Files:**

| File | Contents |
|------|----------|
| `week5_baseline_metrics.csv` | All results in tabular form (one row per model/fold/split) |
| `week5_baseline_summary.json` | Aggregated statistics (mean±std per model) |
| `week5_baseline_per_class_metrics.csv` | Per-class precision/recall/F1 per model |
| `week5_baseline_results.md` | Markdown report with rankings and interpretation |

### Example Run (Fast, 3 folds)

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

python ml-pipeline/src/train_baselines.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --folds 3 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest,mlp,lightgbm
```

**Expected Output:**
```
Training Baselines
==================

Dataset: 11209 samples, 33 features, 6 classes
Feature Sets: normalized_plus_pid (17 dims), full (33 dims)
Models: logreg, random_forest, mlp, lightgbm
Folds: 3-fold grouped CV

Processing feature_set=normalized_plus_pid:
  Training LogisticRegression [fold 1/3]... ✓
  Training LogisticRegression [fold 2/3]... ✓
  Training LogisticRegression [fold 3/3]... ✓
  Results: accuracy=0.539±0.012, f1_macro=0.389±0.018
  
  Training RandomForest [fold 1/3]... ✓
  Training RandomForest [fold 2/3]... ✓
  Training RandomForest [fold 3/3]... ✓
  Results: accuracy=0.779±0.008, f1_macro=0.597±0.012
  
  Training MLPClassifier [fold 1/3]... ✓
  [Similar for MLP and LightGBM]

Processing feature_set=full:
  [Same process for all 33 features]

Cross-Protocol Evaluation:
  Training on MQTT, testing on CoAP:
    LogReg: f1_macro=0.017, accuracy=0.041
    RF: f1_macro=0.090, accuracy=0.267
    MLP: f1_macro=0.090, accuracy=0.267
    LightGBM: f1_macro=0.078, accuracy=0.265
  
  Training on CoAP, testing on MQTT:
    [Similar results, cross-protocol generalization weak]

Outputs:
  - ml-pipeline/reports/week5_baseline_metrics.csv
  - ml-pipeline/reports/week5_baseline_summary.json
  - ml-pipeline/reports/week5_baseline_per_class_metrics.csv
  - ml-pipeline/reports/week5_baseline_results.md

Total runtime: ~5 minutes on CPU
```

### Full Run (5 folds, all models)

For final evaluation, use 5 folds:

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

python ml-pipeline/src/train_baselines.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --folds 5 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest,mlp,lightgbm
```

**Expected runtime:** ~10–15 minutes on modern CPU

---

## Champion Model Training

### Purpose

Train single final model on full dataset (no CV) for deployment

### Script: `week6_train_champion.py`

**Process:**
1. Load full feature matrix (all 11,209 samples)
2. Select best model from baseline evaluation (LightGBM)
3. Train on ALL data (no train/test split)
4. Save serialized model for deployment/export

**Hyperparameters (Frozen):**
```python
lgb_params = {
    "objective": "multiclass",
    "num_class": 6,
    "num_leaves": 31,
    "max_depth": 7,
    "learning_rate": 0.05,
    "n_estimators": 100,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "min_child_samples": 20,
    "random_state": 42,
}
```

**Example Run:**

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

python ml-pipeline/src/week6_train_champion.py \
  --input data/features/unified_features.csv \
  --output ml-pipeline/models/lightgbm_full.pkl \
  --hyperparameters ml-pipeline/reports/week6_hyperparameters.json
```

**Output:**
```
Training Champion Model (LightGBM)
==================================

Dataset: 11209 samples, 33 features, 6 classes
Model: LightGBMClassifier
Hyperparameters: [frozen in week6_hyperparameters.json]

Training on full dataset (no CV)...
  Iteration 1/100... ✓
  ...
  Iteration 100/100... ✓

Model trained successfully.

Serialized to: ml-pipeline/models/lightgbm_full.pkl
Model size: 1.76 MB

Feature importances (top 10):
  f01 (payload size): 0.182
  f02 (entropy): 0.156
  f00 (message rate): 0.143
  f03 (inter-pkt delay): 0.128
  ...

Ready for export to ONNX and C++ deployment.
```

---

## Model Evaluation

### Evaluation Metrics

| Metric | Definition | Range | Interpretation |
|--------|-----------|-------|-----------------|
| **Accuracy** | Correct predictions / total | [0, 1] | Overall correctness |
| **Precision** | TP / (TP + FP) | [0, 1] | False positive rate |
| **Recall** | TP / (TP + FN) | [0, 1] | False negative rate |
| **F1-Score** | 2 × (P × R) / (P + R) | [0, 1] | Harmonic mean of P & R |
| **F1-Macro** | Mean F1 across classes | [0, 1] | Unweighted class average |
| **F1-Weighted** | Weighted F1 across classes | [0, 1] | Class-weighted average |
| **AUC-ROC** | Area under receiver-operator curve | [0, 1] | Threshold-independent performance |

### Result Interpretation

**Baseline Results (5-fold grouped CV, full feature set):**

| Model | Accuracy | F1-Macro | F1-Weighted | Inference Time |
|-------|----------|----------|-------------|-----------------|
| **LightGBM** | **0.7796** | **0.5977** | **0.8128** | <0.1ms ✓ |
| RandomForest | 0.7792 | 0.5969 | 0.8118 | <0.1ms ✓ |
| MLP | 0.7395 | 0.5742 | 0.7803 | 0.05ms ✓ |
| LogReg | 0.5388 | 0.3895 | 0.5456 | <0.01ms ✓ |

**Interpretation:**
- ✅ LightGBM marginally best (0.13% better than RF, not significant)
- ✅ Both tree models far superior to linear (LogReg)
- ✅ MLP reasonable but slower per inference
- ✅ All models meet latency SLA (<1ms per packet)

**Per-Class Performance (LightGBM):**

| Class | Precision | Recall | F1-Score | Support |
|-------|-----------|--------|----------|---------|
| benign | 0.85 | 0.85 | 0.85 | 4,600 |
| mqtt_protocol_abuse | 0.62 | 0.48 | 0.54 | 1,200 |
| mqtt_wildcard_abuse | 0.40 | 0.35 | 0.37 | 800 |
| mqtt_publish_flood | 0.58 | 0.52 | 0.55 | 1,500 |
| coap_protocol_abuse | 0.52 | 0.45 | 0.48 | 1,100 |
| coap_request_flood | 0.55 | 0.50 | 0.52 | 1,009 |

**Insights:**
- ✅ Benign detection strong (F1=0.85)
- ⚠️ Protocol abuse detection moderate (F1~0.50)
- ⚠️ Wildcard abuse hardest to detect (F1=0.37, rare pattern)
- ✅ Flood detection reasonable (F1~0.55)

**Cross-Protocol Evaluation (LightGBM):**

| Split | Accuracy | F1-Macro | Interpretation |
|-------|----------|----------|-----------------|
| Train MQTT, Test CoAP | 0.265 | 0.078 | ⚠️ Severe domain shift |
| Train CoAP, Test MQTT | 0.042 | 0.025 | ⚠️ Severe domain shift |
| Train MQTT+CoAP, Test Both | 0.780 | 0.598 | ✓ Good within-domain |

**Key Finding:** Protocol-normalized features alone insufficient for cross-protocol generalization. Recommend future work on domain adaptation.

---

## Scripts Reference

### Data & Feature Scripts

#### `export_events_to_dataset.py`
Convert raw events → feature vectors

```bash
python ml-pipeline/src/export_events_to_dataset.py \
  --input data/raw/proxy_events_labeled.csv \
  --output data/features/unified_features.csv \
  --normalize
```

#### `validate_feature_quality.py`
Analyze feature distributions and cross-protocol alignment

```bash
python ml-pipeline/src/validate_feature_quality.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week3_feature_quality.md
```

### Training & Evaluation Scripts

#### `train_baselines.py` (Core training script)
Train 4 models with 5-fold grouped CV and cross-protocol evaluation

```bash
# Fast run (3 folds, 2 models)
python ml-pipeline/src/train_baselines.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --folds 3 \
  --seed 42 \
  --models logreg,lightgbm

# Full run (5 folds, all 4 models, all feature sets)
python ml-pipeline/src/train_baselines.py \
  --input data/features/unified_features.csv \
  --out-dir ml-pipeline/reports \
  --folds 5 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest,mlp,lightgbm
```

#### `week6_train_champion.py`
Train final LightGBM model on full dataset

```bash
python ml-pipeline/src/week6_train_champion.py \
  --input data/features/unified_features.csv \
  --output ml-pipeline/models/lightgbm_full.pkl
```

#### `week6_export_onnx.py`
Export trained model to ONNX for C++ deployment

```bash
python ml-pipeline/src/week6_export_onnx.py \
  --model ml-pipeline/models/lightgbm_full.pkl \
  --output ml-pipeline/models/lightgbm_full.onnx
```

### Analysis & Visualization Scripts

#### `week11_statistical_analysis.py`
Compute bootstrap CIs, pairwise tests, effect sizes

```bash
python ml-pipeline/src/week11_statistical_analysis.py \
  --input ml-pipeline/reports/week5_baseline_metrics.csv \
  --output ml-pipeline/reports/week11_statistical_analysis.json \
  --confidence 0.95 \
  --bootstrap-samples 10000
```

**Output includes:**
- 95% confidence intervals on F1-macro per model
- Pairwise t-tests (LightGBM vs RF, MLP, LogReg)
- Cohen's d effect sizes
- Mann-Whitney U tests for protocol comparison

#### `week11_generate_figures.py`
Generate all 7 publication-ready figures

```bash
python ml-pipeline/src/week11_generate_figures.py \
  --metrics-csv ml-pipeline/reports/week5_baseline_metrics.csv \
  --output-dir ml-pipeline/figures
```

**Figures generated:**
1. `fig1_model_comparison.png` — Bar chart: accuracy, F1-macro, latency
2. `fig2_generalization_heatmap_grouped_cv.png` — Cross-model, cross-feature-set
3. `fig2_generalization_heatmap_cross_protocol.png` — Domain shift visualization
4. `fig3_per_class_f1.png` — Per-class F1 across all models
5. `fig4_feature_drift.png` — KL divergence (MQTT vs CoAP) per feature
6. `fig5_anomaly_distribution.png` — Histogram of anomaly scores
7. `fig6_threshold_sensitivity.png` — Detection rate vs threshold curve
8. `fig7_kl_divergence.png` — Per-class KL matrix visualization

---

## Directory Structure

```
ml-pipeline/
├── src/
│   ├── export_events_to_dataset.py        # Raw events → feature vectors
│   ├── validate_feature_quality.py        # Feature analysis
│   ├── train_baselines.py                 # 4 models × CV × metrics
│   ├── week6_train_champion.py            # Final LightGBM training
│   ├── week6_export_onnx.py               # Model → ONNX export
│   ├── week11_generate_figures.py         # Paper figure generation
│   └── week11_statistical_analysis.py     # Bootstrap CIs + pairwise tests
│
├── models/
│   ├── lightgbm_full.pkl                  # Champion model (Python pickle)
│   └── lightgbm_full.onnx                 # Champion model (ONNX format)
│
├── reports/
│   ├── week3_feature_quality.md           # Feature validation report
│   ├── feature_summary_overall.csv        # Per-feature statistics
│   ├── feature_summary_by_protocol.csv    # Protocol-stratified stats
│   ├── kl_alignment_by_class.csv          # KL divergence per class
│   ├── week5_baseline_metrics.csv         # All model results (main output)
│   ├── week5_baseline_summary.json        # Aggregated statistics
│   ├── week5_baseline_per_class_metrics.csv # Per-class metrics
│   ├── week5_baseline_results.md          # Markdown summary
│   ├── week6_model_selections.md          # Champion model rationale
│   ├── week6_hyperparameters.json         # Frozen hyperparameters
│   ├── week8_benign_baseline.md           # Benign traffic analysis
│   ├── week9_integration_report.md        # Dual-protocol validation
│   ├── week10_analysis_report.md          # Statistical per-protocol analysis
│   └── week11_statistical_analysis.json   # Bootstrap CIs + pairwise tests
│
├── figures/
│   ├── fig1_model_comparison.png          # Model performance bar chart
│   ├── fig2_generalization_heatmap_grouped_cv.png
│   ├── fig2_generalization_heatmap_cross_protocol.png
│   ├── fig3_per_class_f1.png
│   ├── fig4_feature_drift.png
│   ├── fig5_anomaly_distribution.png
│   ├── fig6_threshold_sensitivity.png
│   └── fig7_kl_divergence.png
│
├── README.md                              # This file
└── __pycache__/                           # Python cache (auto-generated)
```

---

## Results & Artifacts

### Key Results Summary

**Dataset:**
- Total: 11,209 labeled events
- MQTT: 6,512 (58%), CoAP: 4,697 (42%)
- Benign: 4,600 (41%), Attack: 6,609 (59%)

**Best Model (LightGBM, Full Features):**
- Grouped CV Accuracy: 0.7796
- Grouped CV F1-Macro: 0.5977
- Per-Protocol Accuracy: MQTT 0.782, CoAP 0.776
- Cross-Protocol F1: ~0.08 (weak)

**Deployment:**
- Model Format: ONNX (lightgbm_full.onnx)
- Model Size: 1.76 MB (pickle), ~1.8 MB (ONNX)
- Inference Latency: <0.1ms per sample
- Ready for: C++ proxy integration

**Statistical Confidence (95% Bootstrap):**
- LightGBM F1-Macro 95% CI: [0.589, 0.607]
- LightGBM vs RandomForest: p=0.91 (not significant)
- LightGBM vs MLP: p<0.001 (statistically significant, +0.052 F1 gain)
- MQTT vs CoAP anomaly scores: p=0.0001 (Mann-Whitney), Cohen's d=0.206

---

## Troubleshooting

### Issue: Script Requires Data File That Doesn't Exist

**Error:** `FileNotFoundError: data/raw/proxy_events_labeled.csv`

**Solution:**
1. Verify data has been collected from proxy
2. Or use pre-existing labeled data from repository
3. Check file path is correct relative to repository root

```bash
# Verify data exists
ls -lh data/raw/proxy_events_labeled.csv

# If missing, copy from backup or generate
cp /path/to/backup/proxy_events_labeled.csv data/raw/
```

### Issue: Python Imports Missing During ML Training

**Error:** `ModuleNotFoundError: No module named 'lightgbm'`

**Solution:**
```bash
# Activate venv and reinstall dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Or install specific package
pip install lightgbm scikit-learn pandas numpy
```

### Issue: Baseline Training Takes Too Long

**Symptom:** `train_baselines.py` runs for >20 minutes

**Solution:**
```bash
# Use fewer folds for faster iteration
python ml-pipeline/src/train_baselines.py \
  --folds 2 \
  --models lightgbm  # Test one model first

# Or parallelize across CPU cores
python ml-pipeline/src/train_baselines.py \
  --folds 5 \
  --n-jobs -1  # Use all cores
```

### Issue: ONNX Export Fails

**Error:** `onnxmltools not compatible with LightGBMClassifier`

**Solution:**
```bash
# Use native LightGBM ONNX exporter
pip install lightgbm-onnx

# Or export manually:
python -c "
import lightgbm as lgb
import onnx

model = lgb.Booster(model_file='ml-pipeline/models/lightgbm_full.pkl')
# Use native exporter if available
# Or convert via onnxmltools with workaround
"
```

### Issue: Feature Quality Report Shows High KL Divergence

**Interpretation:** Features drift significantly between MQTT and CoAP

**Action:** This is expected due to protocol differences. Documented in reports. Drives recommendation for protocol-specific models or domain adaptation in future work.

---

## Next Steps

1. **Explore Results:** Check `ml-pipeline/reports/week5_baseline_results.md`
2. **Review Figures:** View `ml-pipeline/figures/fig[1-7]_*.png`
3. **Read Statistical Analysis:** Check `week11_statistical_analysis.json`
4. **Deploy Model:** See `proxy-core/src/detection_pipeline.cpp` for ONNX integration
5. **Reproduce:** Run scripts in order: export → validate → train → analyze → visualize

---

**For detailed architecture and integration info, see:** `CODEBASE_OVERVIEW_ONBOARDING.md`
