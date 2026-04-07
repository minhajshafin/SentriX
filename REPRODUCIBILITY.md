# SentriX Reproducibility Guide

This document provides a complete protocol to reproduce SentriX artifacts end-to-end:
- datasets and feature reports
- baseline ML metrics
- statistical analysis outputs
- paper figures
- deployable model artifacts
- runtime validation in the full testbed

## Scope

This guide covers two reproduction modes:

1. Offline artifact reproduction (fast, paper-focused)
2. Live system reproduction (proxy + brokers + monitoring + traffic)

## Canonical Artifacts

Core reproducibility targets:

- Baseline metrics: [ml-pipeline/reports/week5_baseline_metrics.csv](ml-pipeline/reports/week5_baseline_metrics.csv)
- Baseline summary: [ml-pipeline/reports/week5_baseline_summary.json](ml-pipeline/reports/week5_baseline_summary.json)
- Per-class metrics: [ml-pipeline/reports/week5_baseline_per_class_metrics.csv](ml-pipeline/reports/week5_baseline_per_class_metrics.csv)
- Feature quality: [ml-pipeline/reports/kl_alignment_by_class.csv](ml-pipeline/reports/kl_alignment_by_class.csv)
- Statistical tests: [ml-pipeline/reports/week11_statistical_analysis.json](ml-pipeline/reports/week11_statistical_analysis.json)
- Figures: [ml-pipeline/figures](ml-pipeline/figures)
- Deployed ONNX model: [ml-pipeline/models/lightgbm_full.onnx](ml-pipeline/models/lightgbm_full.onnx)

## Repository Map

```text
SentriX/
├── data/
│   └── raw/
│       ├── proxy_events_labeled.csv
│       └── proxy_events.csv
├── ml-pipeline/
│   ├── src/
│   ├── reports/
│   ├── models/
│   └── figures/
├── proxy-core/
├── simulators/
├── deploy/
└── dashboard/
```

## Reproducibility Environment

### OS and Toolchain

- Linux/macOS (validated on Linux)
- Python 3.10+
- CMake 3.16+
- C++17 compiler (g++/clang)
- Docker + Docker Compose v2
- Node.js 18+ (for dashboard/API tooling)

### Python Environment Setup

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install lightgbm scikit-learn pandas numpy matplotlib seaborn scipy onnx onnxmltools onnxruntime
```

Optional lockfile for exact replay:

```bash
pip freeze > requirements-repro.txt
```

### Build Proxy Core (for live reproduction)

```bash
cd proxy-core
cmake -S . -B build
cmake --build build -j
```

## Mode A: Offline Artifact Reproduction

Use this when you only need paper numbers, reports, and figures.

### Step A1: Validate Input Dataset

```bash
cd /home/billy/X/SentriX
source .venv/bin/activate

python - <<'PY'
import pandas as pd
df = pd.read_csv('data/raw/proxy_events_labeled.csv')
print('rows:', len(df))
print('cols:', len(df.columns))
print('protocol_counts:', df['protocol'].value_counts().to_dict())
print('label_counts:', df['label'].value_counts().to_dict())
PY
```

Expected:
- rows near 11,209
- protocol split approximately MQTT 60% / CoAP 40%

### Step A2: Feature Quality Validation

```bash
python ml-pipeline/src/validate_feature_quality.py \
	--in data/raw/proxy_events_labeled.csv \
	--out-dir ml-pipeline/reports \
	--report ml-pipeline/reports/week3_feature_quality.md
```

Expected outputs:
- [ml-pipeline/reports/week3_feature_quality.md](ml-pipeline/reports/week3_feature_quality.md)
- [ml-pipeline/reports/feature_summary_overall.csv](ml-pipeline/reports/feature_summary_overall.csv)
- [ml-pipeline/reports/feature_summary_by_protocol.csv](ml-pipeline/reports/feature_summary_by_protocol.csv)
- [ml-pipeline/reports/kl_alignment_by_class.csv](ml-pipeline/reports/kl_alignment_by_class.csv)

### Step A3: Baseline Model Training

Fast run:

```bash
python ml-pipeline/src/train_baselines.py \
	--in data/raw/proxy_events_labeled.csv \
	--out-dir ml-pipeline/reports \
	--report ml-pipeline/reports/week5_baseline_results.md \
	--folds 3 \
	--seed 42 \
	--feature-sets normalized_plus_pid,full \
	--models logreg,random_forest,mlp,lightgbm
```

Paper-level run:

```bash
python ml-pipeline/src/train_baselines.py \
	--in data/raw/proxy_events_labeled.csv \
	--out-dir ml-pipeline/reports \
	--report ml-pipeline/reports/week5_baseline_results.md \
	--folds 5 \
	--seed 42 \
	--feature-sets normalized_plus_pid,full \
	--models logreg,random_forest,mlp,lightgbm
```

Expected outputs:
- [ml-pipeline/reports/week5_baseline_metrics.csv](ml-pipeline/reports/week5_baseline_metrics.csv)
- [ml-pipeline/reports/week5_baseline_summary.json](ml-pipeline/reports/week5_baseline_summary.json)
- [ml-pipeline/reports/week5_baseline_per_class_metrics.csv](ml-pipeline/reports/week5_baseline_per_class_metrics.csv)
- [ml-pipeline/reports/week5_baseline_results.md](ml-pipeline/reports/week5_baseline_results.md)

Target headline:
- LightGBM grouped-CV macro-F1 approximately 0.5977
- LightGBM grouped-CV accuracy approximately 0.7796

### Step A4: Statistical Analysis

```bash
python ml-pipeline/src/week11_statistical_analysis.py
```

Expected output:
- [ml-pipeline/reports/week11_statistical_analysis.json](ml-pipeline/reports/week11_statistical_analysis.json)

Expected key findings:
- LightGBM macro-F1 95% CI near [0.589, 0.607]
- LightGBM vs RandomForest p-value near 0.91 (not significant)
- LightGBM vs MLP p-value < 0.001 (significant)
- MQTT vs CoAP runtime anomaly distributions differ (small effect)

### Step A5: Figure Generation

```bash
python ml-pipeline/src/week11_generate_figures.py
```

Expected outputs in [ml-pipeline/figures](ml-pipeline/figures):
- `fig1_model_comparison.png`
- `fig2_generalization_heatmap_*.png`
- `fig3_per_class_f1.png`
- `fig4_feature_drift.png`
- `fig5_anomaly_distribution.png`
- `fig6_threshold_sensitivity.png`
- `fig7_kl_divergence.png`

## Mode B: Live System Reproduction

Use this mode to reproduce runtime behavior and live metrics.

### Step B1: Start Docker Testbed

```bash
cd deploy
docker compose up -d
docker compose ps
```

Expected running services:
- `sentrix-mosquitto` (`1883/tcp`)
- `sentrix-coap-backend` (`5683/udp`)
- `sentrix-proxy-core` (`1884/tcp`, `5684/udp`)
- `sentrix-metrics-api` (`8080/tcp`)

### Step B2: Verify Health and Metrics

```bash
curl http://localhost:8080/health
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/events | python -m json.tool | head -n 60
```

### Step B3: Generate Traffic

From repo root:

```bash
source .venv/bin/activate

# MQTT benign
python -m simulators.mqtt.mqtt_benign --count 100

# MQTT attack-like
python -m simulators.mqtt.mqtt_attacks --count 100

# CoAP benign
python -m simulators.coap.coap_benign --count 100

# CoAP attack-like
python -m simulators.coap.coap_attacks --count 100
```

Then re-check metrics/events:

```bash
curl http://localhost:8080/metrics | python -m json.tool
curl http://localhost:8080/events | python -m json.tool | head -n 80
```

### Step B4: Export Live Events to Dataset CSV

```bash
python ml-pipeline/src/export_events_to_dataset.py \
	--events-api http://localhost:8080/events \
	--out data/raw/proxy_events.csv \
	--run-id LIVE-RUN-R1 \
	--scenario mixed_runtime \
	--label benign \
	--rep 1
```

Append subsequent runs:

```bash
python ml-pipeline/src/export_events_to_dataset.py \
	--events-api http://localhost:8080/events \
	--out data/raw/proxy_events.csv \
	--run-id LIVE-RUN-R2 \
	--scenario mixed_runtime \
	--label benign \
	--rep 2 \
	--append
```

## Runtime Proxy (Standalone Host Mode)

Use host mode when debugging C++ runtime directly.

```bash
cd deploy
docker compose up -d mosquitto californium-backend

cd ../proxy-core
SENTRIX_MQTT_BROKER_HOST=127.0.0.1 \
SENTRIX_MQTT_BROKER_PORT=1883 \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 \
SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884 \
SENTRIX_COAP_PROXY_PORT=5684 \
SENTRIX_METRICS_PATH=/tmp/sentrix_metrics.json \
SENTRIX_EVENTS_PATH=/tmp/sentrix_events.log \
./build/sentrix_proxy
```

Important:
- Do not run host proxy and Docker `proxy-core` simultaneously on the same ports.

## Validation Checklist

After reproduction, confirm:

1. Baseline metric files exist in [ml-pipeline/reports](ml-pipeline/reports)
2. Figure files exist in [ml-pipeline/figures](ml-pipeline/figures)
3. ONNX model exists at [ml-pipeline/models/lightgbm_full.onnx](ml-pipeline/models/lightgbm_full.onnx)
4. Key metrics are close to reference values:
	 - LightGBM accuracy ~0.7796
	 - LightGBM macro-F1 ~0.5977
5. Statistical report contains expected CI and significance patterns

Quick sanity script:

```bash
python - <<'PY'
import json
import pandas as pd

m = pd.read_csv('ml-pipeline/reports/week5_baseline_metrics.csv')
lgb = m[(m['model'] == 'lightgbm') & (m['split'] == 'grouped_cv')]
print('lightgbm grouped_cv accuracy mean:', round(lgb['accuracy'].mean(), 4))
print('lightgbm grouped_cv f1_macro mean:', round(lgb['f1_macro'].mean(), 4))

with open('ml-pipeline/reports/week11_statistical_analysis.json', 'r', encoding='utf-8') as f:
		stats = json.load(f)
print('stats keys:', list(stats.keys())[:8])
PY
```

## Dataset and Model Reference

### Dataset

| Property | Value |
|---|---|
| Labeled observations | 11,209 |
| Protocols | MQTT and CoAP |
| Feature dimensionality | 33 |
| Validation style | Grouped CV (run-id aware) |

### Model Comparison (Reference)

| Model | Macro-F1 | Accuracy |
|---|---:|---:|
| LightGBM | 0.5977 | 0.7796 |
| RandomForest | 0.5969 | 0.7792 |
| MLP | 0.5742 | 0.7395 |
| LogisticRegression | 0.3895 | 0.5388 |

## Common Failure Modes

### Missing Python dependencies

```bash
source .venv/bin/activate
pip install --upgrade pip
pip install lightgbm scikit-learn pandas numpy matplotlib seaborn scipy onnx onnxmltools onnxruntime
```

### Docker services not healthy

```bash
cd deploy
docker compose logs --tail=120
docker compose down
docker compose up -d --build
```

### Port conflicts

```bash
lsof -i :1883
lsof -i :1884
lsof -i :5683
lsof -i :5684
lsof -i :8080
```

## Research Paper Build

Manuscript source:
- [Research_Paper/conference_101719.tex](Research_Paper/conference_101719.tex)

Compile:

```bash
cd Research_Paper
pdflatex conference_101719.tex
bibtex conference_101719
pdflatex conference_101719.tex
pdflatex conference_101719.tex
```

## Related Docs

- Top-level overview: [README.md](README.md)
- Setup and runbook: [SETUP_CODING.md](SETUP_CODING.md)
- ML internals: [ml-pipeline/README.md](ml-pipeline/README.md)
- Demo script: [DEMO_CHEATSHEET_5MIN.md](DEMO_CHEATSHEET_5MIN.md)

