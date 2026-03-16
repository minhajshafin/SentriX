# SentriX — Reproducibility Artifacts

This document describes how to reproduce all results, figures, and trained models from the SentriX paper.

## Repository Structure

```
SentriX/
├── data/
│   └── raw/
│       ├── proxy_events_labeled.csv      # Full labeled dataset (11,209 rows)
│       └── proxy_events.csv              # Unlabeled raw events
├── ml-pipeline/
│   ├── src/
│   │   ├── export_events_to_dataset.py   # Feature extraction from raw events
│   │   ├── train_baselines.py            # Train and evaluate all 4 ML models
│   │   ├── validate_feature_quality.py   # KL divergence + drift analysis
│   │   ├── week11_generate_figures.py    # Reproduce all 7 paper figures
│   │   └── week11_statistical_analysis.py# Bootstrap CIs, pairwise tests
│   ├── models/
│   │   └── lightgbm_full.onnx            # Deployed ONNX model
│   ├── figures/                          # All generated PNG figures
│   └── reports/                          # CSV/JSON result summaries
├── proxy-core/                           # C++ proxy source (CMake)
│   ├── src/
│   ├── include/
│   └── CMakeLists.txt
├── simulators/                           # Traffic generation scripts
│   ├── mqtt/
│   │   ├── mqtt_benign.py
│   │   └── mqtt_attacks.py
│   └── coap/
│       ├── coap_benign.py
│       └── coap_attacks.py
├── deploy/
│   ├── docker-compose.yml                # Full testbed: broker + proxy + dashboard
│   └── mosquitto.conf
└── dashboard/                            # Next.js monitoring UI
```

## Quick Start

### 1. Prerequisites

```bash
# Python 3.10+ with .venv
python3 -m venv .venv
source .venv/bin/activate
pip install lightgbm scikit-learn pandas numpy matplotlib seaborn scipy onnx onnxmltools onnxruntime

# C++ proxy build
sudo apt-get install cmake g++ libssl-dev mosquitto-dev
cd proxy-core && mkdir -p build && cd build
cmake .. && make -j$(nproc)
```

### 2. Reproduce Baseline ML Results (Table 1)

```bash
source .venv/bin/activate
python ml-pipeline/src/train_baselines.py
# -> outputs ml-pipeline/reports/week5_baseline_metrics.csv
# -> outputs ml-pipeline/models/lightgbm_full.onnx
```

Expected: LightGBM F1-macro = 0.5977, accuracy = 0.7796

### 3. Reproduce Feature Quality Analysis

```bash
python ml-pipeline/src/validate_feature_quality.py
# -> outputs ml-pipeline/reports/kl_alignment_by_class.csv
```

### 4. Reproduce Paper Figures (Figure 1–7)

```bash
python ml-pipeline/src/week11_generate_figures.py
# -> outputs ml-pipeline/figures/fig1_model_comparison.png
# -> outputs ml-pipeline/figures/fig2_generalization_heatmap_*.png
# -> outputs ml-pipeline/figures/fig3_per_class_f1.png
# -> outputs ml-pipeline/figures/fig4_feature_drift.png
# -> outputs ml-pipeline/figures/fig5_anomaly_distribution.png
# -> outputs ml-pipeline/figures/fig6_threshold_sensitivity.png
# -> outputs ml-pipeline/figures/fig7_kl_divergence.png
```

### 5. Reproduce Statistical Analysis

```bash
python ml-pipeline/src/week11_statistical_analysis.py
# -> outputs ml-pipeline/reports/week11_statistical_analysis.json
```

Key findings:
- LightGBM F1-macro 95% CI: [0.589, 0.607]
- LightGBM vs RandomForest: p = 0.91 (not significant)
- LightGBM vs MLP: p < 0.001 (significant, ΔF1 = +0.052)
- MQTT vs CoAP runtime anomaly scores: Mann-Whitney p = 0.0001, Cohen's d = 0.206

### 6. Run the Full Testbed via Docker

```bash
cd deploy
docker-compose up -d
# Starts: Mosquitto broker (1883), Californium CoAP server (5683),
#         SentriX proxy (MQTT:1884, CoAP:5684), metrics API (8080), dashboard (3000)
```

### 7. Generate Traffic and Collect Live Vectors

```bash
# MQTT benign traffic (in separate terminal)
python simulators/mqtt/mqtt_benign.py

# CoAP benign traffic
python simulators/coap/coap_benign.py

# Feature vectors are written to /tmp/sentrix/features.jsonl by the proxy
```

### 8. Build and Run the C++ Proxy Standalone

```bash
cd proxy-core/build
./sentrix_proxy
# Listens: MQTT on :1884 -> :1883, CoAP on :5684 -> :5683
# Writes feature vectors to /tmp/sentrix/features.jsonl
# Metrics API on :8080
```

## Dataset Details

| Property | Value |
|---|---|
| Total observations | 11,209 |
| Protocols | MQTT (60%), CoAP (40%) |
| Attack classes | benign, flood, slowite, malformed, bruteforce, amplification |
| Feature dimensions | 33 (15 behavioral + 2 protocol ID + 16 auxiliary) |
| Labeling method | Simulator-controlled run labels |
| Validation | 5-fold stratified group CV (grouped by run ID) |

## Model Details

| Model | F1-Macro | Accuracy | Format |
|---|---|---|---|
| LightGBM (deployed) | 0.5977 | 0.7796 | ONNX (lightgbm_full.onnx) |
| RandomForest | 0.5969 | 0.7792 | Python (sklearn) |
| MLP | 0.5742 | 0.7395 | Python (sklearn) |
| LogisticRegression | 0.3895 | 0.5388 | Python (sklearn) |

## Live Proxy Evaluation

101 runtime vectors (87 MQTT, 14 CoAP) collected from live proxy during benign-traffic integration test:
- Mean anomaly score: 0.218 (P95: 0.458)
- Zero false positives at threshold 0.75
- Bootstrap 95% CI: MQTT 0.220 [0.197, 0.247], CoAP 0.202 [0.188, 0.226]

Raw vectors: `/tmp/sentrix/features.jsonl` (generated by proxy at runtime; not committed to repo)

## Research Paper

`Research_Paper/conference_101719.tex` — IEEEtran conference format, compilable with:
```bash
pdflatex conference_101719.tex
bibtex conference_101719
pdflatex conference_101719.tex
pdflatex conference_101719.tex
```
