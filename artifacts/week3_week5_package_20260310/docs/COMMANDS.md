# Commands Used For Final Baseline

## Step 4 Feature Validation

```bash
/home/billy/X/SentriX/.venv/bin/python ml-pipeline/src/validate_feature_quality.py \
  --in data/raw/week3_runs_labeled.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week3_feature_quality.md
```

## Step 5 Baseline Training (Official)

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/home/billy/X/SentriX/.venv/bin/python -u ml-pipeline/src/train_baselines.py \
  --in data/raw/week3_runs_labeled.csv \
  --out-dir ml-pipeline/reports \
  --report ml-pipeline/reports/week5_baseline_results.md \
  --folds 3 \
  --seed 42 \
  --feature-sets normalized_plus_pid,full \
  --models logreg,random_forest
```
