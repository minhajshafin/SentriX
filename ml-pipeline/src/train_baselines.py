from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


NORM_FEATURES = [f"f{i:02d}" for i in range(15)]
NORM_PLUS_PID_FEATURES = [f"f{i:02d}" for i in range(17)]
FULL_FEATURES = [f"f{i:02d}" for i in range(33)]


@dataclass
class EvalResult:
    feature_set: str
    model: str
    split: str
    accuracy: float
    f1_macro: float
    f1_weighted: float


def _load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"run_id", "protocol", "label", *FULL_FEATURES}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"dataset missing required columns: {sorted(missing)}")
    return df


def _feature_sets() -> dict[str, list[str]]:
    return {
        "normalized": NORM_FEATURES,
        "normalized_plus_pid": NORM_PLUS_PID_FEATURES,
        "full": FULL_FEATURES,
    }


def _model_builders(random_state: int) -> dict[str, Pipeline]:
    return {
        "logreg": Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=1200,
                        class_weight="balanced",
                        solver="lbfgs",
                        n_jobs=None,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=250,
            max_depth=None,
            min_samples_leaf=2,
            n_jobs=-1,
            class_weight="balanced_subsample",
            random_state=random_state,
        ),
        "hist_gb": HistGradientBoostingClassifier(
            learning_rate=0.07,
            max_depth=8,
            max_iter=180,
            l2_regularization=1e-3,
            random_state=random_state,
        ),
    }


def _grouped_cv_splits(df: pd.DataFrame, y: np.ndarray, n_splits: int, random_state: int):
    groups = df["run_id"].to_numpy()
    try:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        return splitter.split(df, y, groups)
    except Exception:
        splitter = GroupKFold(n_splits=n_splits)
        return splitter.split(df, y, groups)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    return (
        accuracy_score(y_true, y_pred),
        f1_score(y_true, y_pred, average="macro", zero_division=0),
        f1_score(y_true, y_pred, average="weighted", zero_division=0),
    )


def _evaluate_grouped_cv(
    df: pd.DataFrame,
    features: list[str],
    model_name: str,
    model,
    n_splits: int,
    random_state: int,
) -> EvalResult:
    x = df[features].to_numpy(dtype=np.float32)
    y = df["label"].to_numpy()

    fold_scores: list[tuple[float, float, float]] = []
    for train_idx, test_idx in _grouped_cv_splits(df, y, n_splits=n_splits, random_state=random_state):
        model.fit(x[train_idx], y[train_idx])
        pred = model.predict(x[test_idx])
        fold_scores.append(_metrics(y[test_idx], pred))

    avg = np.mean(np.asarray(fold_scores), axis=0)
    return EvalResult(
        feature_set="",
        model=model_name,
        split="grouped_cv",
        accuracy=float(avg[0]),
        f1_macro=float(avg[1]),
        f1_weighted=float(avg[2]),
    )


def _evaluate_cross_protocol(
    df: pd.DataFrame,
    features: list[str],
    model_name: str,
    model,
) -> list[EvalResult]:
    x = df[features].to_numpy(dtype=np.float32)
    y = df["label"].to_numpy()
    protocol = df["protocol"].to_numpy()

    results: list[EvalResult] = []
    directions = [
        ("mqtt", "coap", "cross_mqtt_to_coap"),
        ("coap", "mqtt", "cross_coap_to_mqtt"),
    ]

    for train_proto, test_proto, split_name in directions:
        train_idx = np.where(protocol == train_proto)[0]
        test_idx = np.where(protocol == test_proto)[0]
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        model.fit(x[train_idx], y[train_idx])
        pred = model.predict(x[test_idx])
        acc, f1m, f1w = _metrics(y[test_idx], pred)
        results.append(
            EvalResult(
                feature_set="",
                model=model_name,
                split=split_name,
                accuracy=float(acc),
                f1_macro=float(f1m),
                f1_weighted=float(f1w),
            )
        )

    return results


def train_baselines(
    *,
    in_csv: Path,
    out_dir: Path,
    n_splits: int,
    random_state: int,
    selected_feature_sets: list[str],
    selected_models: list[str],
) -> pd.DataFrame:
    df = _load_dataset(in_csv)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    all_feature_sets = _feature_sets()
    all_models = _model_builders(random_state=random_state)
    feature_sets = {name: all_feature_sets[name] for name in selected_feature_sets}
    model_builders = {name: all_models[name] for name in selected_models}

    for feature_set_name, features in feature_sets.items():
        for model_name, model in model_builders.items():
            print(f"[train] feature_set={feature_set_name} model={model_name}", flush=True)
            cv_result = _evaluate_grouped_cv(
                df=df,
                features=features,
                model_name=model_name,
                model=model,
                n_splits=n_splits,
                random_state=random_state,
            )
            cv_result.feature_set = feature_set_name
            rows.append(cv_result.__dict__)

            cross_results = _evaluate_cross_protocol(df=df, features=features, model_name=model_name, model=model)
            for result in cross_results:
                result.feature_set = feature_set_name
                rows.append(result.__dict__)
            print(
                f"[done] feature_set={feature_set_name} model={model_name} "
                f"cv_f1_macro={cv_result.f1_macro:.4f}",
                flush=True,
            )

    result_df = pd.DataFrame(rows).sort_values(["split", "f1_macro", "accuracy"], ascending=[True, False, False])
    result_df.to_csv(out_dir / "week5_baseline_metrics.csv", index=False)

    grouped = result_df[result_df["split"] == "grouped_cv"].sort_values("f1_macro", ascending=False)
    best = grouped.iloc[0].to_dict() if not grouped.empty else {}

    summary = {
        "dataset_rows": int(len(df)),
        "run_count": int(df["run_id"].nunique()),
        "label_counts": df["label"].value_counts().to_dict(),
        "protocol_counts": df["protocol"].value_counts().to_dict(),
        "best_grouped_cv": best,
    }
    (out_dir / "week5_baseline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return result_df


def _write_markdown(result_df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    grouped = result_df[result_df["split"] == "grouped_cv"].sort_values("f1_macro", ascending=False)
    cross = result_df[result_df["split"] != "grouped_cv"].sort_values(["split", "f1_macro"], ascending=[True, False])

    def _table(df: pd.DataFrame) -> list[str]:
        if df.empty:
            return ["No rows."]
        lines = ["| feature_set | model | split | accuracy | f1_macro | f1_weighted |", "| --- | --- | --- | ---: | ---: | ---: |"]
        for _, row in df.iterrows():
            lines.append(
                "| "
                f"{row['feature_set']} | {row['model']} | {row['split']} | "
                f"{row['accuracy']:.4f} | {row['f1_macro']:.4f} | {row['f1_weighted']:.4f} |"
            )
        return lines

    lines = [
        "# Week 5 Baseline Training Results",
        "",
        "## Grouped CV (run_id-safe)",
        "",
        *_table(grouped),
        "",
        "## Cross-Protocol Generalization",
        "",
        *_table(cross),
        "",
        "Artifacts:",
        "- `week5_baseline_metrics.csv`",
        "- `week5_baseline_summary.json`",
    ]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CPU-friendly baseline models for SentriX Week 5")
    parser.add_argument("--in", dest="in_csv", default="/home/billy/X/SentriX/data/raw/week3_runs_labeled.csv")
    parser.add_argument("--out-dir", dest="out_dir", default="/home/billy/X/SentriX/ml-pipeline/reports")
    parser.add_argument("--report", dest="report", default="/home/billy/X/SentriX/ml-pipeline/reports/week5_baseline_results.md")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--feature-sets",
        default="normalized_plus_pid,full",
        help="Comma-separated: normalized,normalized_plus_pid,full",
    )
    parser.add_argument(
        "--models",
        default="logreg,random_forest",
        help="Comma-separated: logreg,random_forest,hist_gb",
    )
    args = parser.parse_args()

    selected_feature_sets = [item.strip() for item in args.feature_sets.split(",") if item.strip()]
    selected_models = [item.strip() for item in args.models.split(",") if item.strip()]

    valid_features = set(_feature_sets().keys())
    valid_models = set(_model_builders(random_state=args.seed).keys())
    bad_features = [name for name in selected_feature_sets if name not in valid_features]
    bad_models = [name for name in selected_models if name not in valid_models]
    if bad_features:
        raise ValueError(f"unknown feature sets: {bad_features}; valid={sorted(valid_features)}")
    if bad_models:
        raise ValueError(f"unknown models: {bad_models}; valid={sorted(valid_models)}")

    result_df = train_baselines(
        in_csv=Path(args.in_csv),
        out_dir=Path(args.out_dir),
        n_splits=args.folds,
        random_state=args.seed,
        selected_feature_sets=selected_feature_sets,
        selected_models=selected_models,
    )
    _write_markdown(result_df, out_path=Path(args.report))
    print(f"Wrote baseline metrics to {Path(args.out_dir) / 'week5_baseline_metrics.csv'}")
    print(f"Wrote report to {args.report}")


if __name__ == "__main__":
    main()
