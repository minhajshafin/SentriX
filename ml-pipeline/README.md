# ML Pipeline (Scaffold)

Planned contents:
- Feature validation and distribution checks
- Training scripts (RF, LightGBM, MLP)
- Cross-protocol evaluation scripts
- ONNX export utilities

Current dataset source:
- `../data/features/unified_features.csv`

## Step 4 Feature Quality Validation

Run:

```bash
python ml-pipeline/src/validate_feature_quality.py \
	--in data/raw/week3_runs_labeled.csv \
	--out-dir ml-pipeline/reports \
	--report ml-pipeline/reports/week3_feature_quality.md
```

Outputs:
- `ml-pipeline/reports/week3_feature_quality.md`
- `ml-pipeline/reports/feature_summary_overall.csv`
- `ml-pipeline/reports/feature_summary_by_protocol.csv`
- `ml-pipeline/reports/kl_alignment_by_class.csv`

## Step 5 Baseline Training (CPU)

Run:

```bash
python ml-pipeline/src/train_baselines.py \
	--in data/raw/week3_runs_labeled.csv \
	--out-dir ml-pipeline/reports \
	--report ml-pipeline/reports/week5_baseline_results.md \
	--folds 3 \
	--seed 42 \
	--feature-sets normalized_plus_pid,full \
	--models logreg,random_forest
```

Optional heavier run:

```bash
python ml-pipeline/src/train_baselines.py --models logreg,random_forest,hist_gb --folds 5
```

Outputs:
- `ml-pipeline/reports/week5_baseline_metrics.csv`
- `ml-pipeline/reports/week5_baseline_summary.json`
- `ml-pipeline/reports/week5_baseline_results.md`
