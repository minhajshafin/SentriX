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
