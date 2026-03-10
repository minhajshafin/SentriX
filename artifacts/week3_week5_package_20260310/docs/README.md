# SentriX Week 3/5 Artifact Package

Date: 2026-03-10

## Contents

- data/week3_runs_labeled.csv
- reports/week3_feature_quality.md
- reports/feature_summary_overall.csv
- reports/feature_summary_by_protocol.csv
- reports/kl_alignment_by_class.csv
- reports/week5_baseline_results.md
- reports/week5_baseline_metrics.csv
- reports/week5_baseline_summary.json
- scripts/export_events_to_dataset.py
- scripts/validate_feature_quality.py
- scripts/train_baselines.py
- docs/COMMANDS.md
- docs/MANIFEST.sha256

## Quick Reproduce

1. Validate feature quality:

```bash
python ml-pipeline/src/validate_feature_quality.py \
  --in data/raw/week3_runs_labeled.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week3_feature_quality.md
```

2. Train CPU baselines:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python ml-pipeline/src/train_baselines.py \
  --in data/raw/week3_runs_labeled.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week5_baseline_results.md \
  --folds 3 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest
```
