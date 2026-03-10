from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence, TypedDict


FEATURE_COLUMNS = [f"f{i:02d}" for i in range(33)]
NORMALIZED_FEATURE_COLUMNS = [f"f{i:02d}" for i in range(15)]
PROTOCOL_ID_COLUMNS = ("f15", "f16")


class KlRow(TypedDict):
    attack_class: str
    feature: str
    mqtt_count: int
    coap_count: int
    kl_mqtt_to_coap: float
    kl_coap_to_mqtt: float
    kl_symmetric: float


class FeatureQualitySummary(TypedDict):
    row_count: int
    run_count: int
    protocol_counts: dict[str, int]
    label_counts: dict[str, int]
    normalized_out_of_range: dict[str, int]
    protocol_id_violations: int
    mean_kl_by_class: dict[str, float]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float], mean_value: float) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum((value - mean_value) ** 2 for value in values) / len(values))


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = (len(sorted_values) - 1) * q
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return sorted_values[lower]
    weight = idx - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _canonical_attack_class(label: str) -> str:
    label = label.strip().lower()
    if label == "benign":
        return "benign"
    if "flood" in label:
        return "flood"
    if "protocol_abuse" in label:
        return "protocol_abuse"
    if "wildcard" in label:
        return "wildcard"
    return "other"


def _histogram(values: list[float], *, bins: int = 20, low: float = 0.0, high: float = 1.0) -> list[float]:
    if not values:
        return [0.0] * bins

    counts = [0.0] * bins
    width = high - low
    if width <= 0:
        return [0.0] * bins

    for value in values:
        clipped = min(max(value, low), high)
        if clipped == high:
            idx = bins - 1
        else:
            idx = int(((clipped - low) / width) * bins)
            idx = min(max(idx, 0), bins - 1)
        counts[idx] += 1.0

    total = sum(counts)
    if total == 0:
        return [0.0] * bins
    return [count / total for count in counts]


def _kl_divergence(p: list[float], q: list[float], *, epsilon: float = 1e-12) -> float:
    score = 0.0
    for pv, qv in zip(p, q, strict=True):
        pp = pv + epsilon
        qq = qv + epsilon
        score += pp * math.log(pp / qq)
    return score


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_feature_quality(in_csv: Path, out_dir: Path) -> FeatureQualitySummary:
    rows = _read_rows(in_csv)
    if not rows:
        raise ValueError(f"dataset is empty: {in_csv}")

    protocol_counts: dict[str, int] = defaultdict(int)
    label_counts: dict[str, int] = defaultdict(int)
    run_counts: dict[str, int] = defaultdict(int)
    feature_values: dict[str, list[float]] = {feature: [] for feature in FEATURE_COLUMNS}
    feature_values_by_protocol: dict[str, dict[str, list[float]]] = {
        "mqtt": {feature: [] for feature in FEATURE_COLUMNS},
        "coap": {feature: [] for feature in FEATURE_COLUMNS},
    }

    normalized_out_of_range: dict[str, int] = {feature: 0 for feature in NORMALIZED_FEATURE_COLUMNS}
    protocol_id_violations = 0

    for row in rows:
        protocol = row.get("protocol", "").strip().lower()
        label = row.get("label", "").strip().lower()
        run_id = row.get("run_id", "").strip()

        protocol_counts[protocol] += 1
        label_counts[label] += 1
        run_counts[run_id] += 1

        f15 = _to_float(row.get(PROTOCOL_ID_COLUMNS[0], "0"))
        f16 = _to_float(row.get(PROTOCOL_ID_COLUMNS[1], "0"))
        if protocol == "mqtt" and not (f15 == 1.0 and f16 == 0.0):
            protocol_id_violations += 1
        if protocol == "coap" and not (f15 == 0.0 and f16 == 1.0):
            protocol_id_violations += 1

        for feature in FEATURE_COLUMNS:
            value = _to_float(row.get(feature, "0"))
            feature_values[feature].append(value)
            if protocol in {"mqtt", "coap"}:
                feature_values_by_protocol[protocol][feature].append(value)

        for feature in NORMALIZED_FEATURE_COLUMNS:
            value = _to_float(row.get(feature, "0"))
            if value < 0.0 or value > 1.0:
                normalized_out_of_range[feature] += 1

    stats_rows: list[dict[str, object]] = []
    for feature in FEATURE_COLUMNS:
        values = feature_values[feature]
        mean_value = _mean(values)
        stats_rows.append(
            {
                "feature": feature,
                "count": len(values),
                "min": min(values) if values else 0.0,
                "p25": _quantile(values, 0.25),
                "median": _quantile(values, 0.50),
                "p75": _quantile(values, 0.75),
                "max": max(values) if values else 0.0,
                "mean": mean_value,
                "std": _std(values, mean_value),
            }
        )

    protocol_stats_rows: list[dict[str, object]] = []
    for protocol in ("mqtt", "coap"):
        for feature in FEATURE_COLUMNS:
            values = feature_values_by_protocol[protocol][feature]
            mean_value = _mean(values)
            protocol_stats_rows.append(
                {
                    "protocol": protocol,
                    "feature": feature,
                    "count": len(values),
                    "min": min(values) if values else 0.0,
                    "p25": _quantile(values, 0.25),
                    "median": _quantile(values, 0.50),
                    "p75": _quantile(values, 0.75),
                    "max": max(values) if values else 0.0,
                    "mean": mean_value,
                    "std": _std(values, mean_value),
                }
            )

    class_protocol_feature_values: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: {"mqtt": {feature: [] for feature in NORMALIZED_FEATURE_COLUMNS}, "coap": {feature: [] for feature in NORMALIZED_FEATURE_COLUMNS}}
    )

    for row in rows:
        protocol = row.get("protocol", "").strip().lower()
        if protocol not in {"mqtt", "coap"}:
            continue
        canonical_class = _canonical_attack_class(row.get("label", ""))
        for feature in NORMALIZED_FEATURE_COLUMNS:
            class_protocol_feature_values[canonical_class][protocol][feature].append(_to_float(row.get(feature, "0")))

    kl_rows: list[KlRow] = []
    for canonical_class in sorted(class_protocol_feature_values.keys()):
        mqtt_has = any(class_protocol_feature_values[canonical_class]["mqtt"][feature] for feature in NORMALIZED_FEATURE_COLUMNS)
        coap_has = any(class_protocol_feature_values[canonical_class]["coap"][feature] for feature in NORMALIZED_FEATURE_COLUMNS)
        if not (mqtt_has and coap_has):
            continue

        for feature in NORMALIZED_FEATURE_COLUMNS:
            mqtt_values = class_protocol_feature_values[canonical_class]["mqtt"][feature]
            coap_values = class_protocol_feature_values[canonical_class]["coap"][feature]
            p = _histogram(mqtt_values)
            q = _histogram(coap_values)
            kl_mqtt_to_coap = _kl_divergence(p, q)
            kl_coap_to_mqtt = _kl_divergence(q, p)
            kl_rows.append(
                {
                    "attack_class": canonical_class,
                    "feature": feature,
                    "mqtt_count": len(mqtt_values),
                    "coap_count": len(coap_values),
                    "kl_mqtt_to_coap": kl_mqtt_to_coap,
                    "kl_coap_to_mqtt": kl_coap_to_mqtt,
                    "kl_symmetric": 0.5 * (kl_mqtt_to_coap + kl_coap_to_mqtt),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        out_dir / "feature_summary_overall.csv",
        stats_rows,
        ["feature", "count", "min", "p25", "median", "p75", "max", "mean", "std"],
    )
    _write_csv(
        out_dir / "feature_summary_by_protocol.csv",
        protocol_stats_rows,
        ["protocol", "feature", "count", "min", "p25", "median", "p75", "max", "mean", "std"],
    )
    _write_csv(
        out_dir / "kl_alignment_by_class.csv",
        kl_rows,
        ["attack_class", "feature", "mqtt_count", "coap_count", "kl_mqtt_to_coap", "kl_coap_to_mqtt", "kl_symmetric"],
    )

    mean_kl_by_class: dict[str, float] = {}
    for canonical_class in sorted({row["attack_class"] for row in kl_rows}):
        class_rows = [row for row in kl_rows if row["attack_class"] == canonical_class]
        mean_kl_by_class[canonical_class] = _mean([row["kl_symmetric"] for row in class_rows])

    return {
        "row_count": len(rows),
        "run_count": len(run_counts),
        "protocol_counts": dict(sorted(protocol_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "normalized_out_of_range": normalized_out_of_range,
        "protocol_id_violations": protocol_id_violations,
        "mean_kl_by_class": mean_kl_by_class,
    }


def _write_markdown_report(summary: FeatureQualitySummary, out_path: Path) -> None:
    normalized_violations = summary["normalized_out_of_range"]
    top_violations = sorted(normalized_violations.items(), key=lambda item: item[1], reverse=True)

    lines = [
        "# Week 3 Step 4 Feature Quality Validation",
        "",
        "## Dataset Coverage",
        "",
        f"- Rows: **{summary['row_count']}**",
        f"- Distinct runs: **{summary['run_count']}**",
        f"- Protocol counts: `{summary['protocol_counts']}`",
        f"- Label counts: `{summary['label_counts']}`",
        "",
        "## Feature Sanity Checks",
        "",
        f"- Protocol one-hot violations (`f15`,`f16`): **{summary['protocol_id_violations']}**",
        "- Normalized feature out-of-range counts (`f00..f14`):",
    ]

    for feature, count in top_violations:
        lines.append(f"  - `{feature}`: {count}")

    lines.extend(
        [
            "",
            "## Cross-Protocol Alignment (KL)",
            "",
            "Mean symmetric KL divergence per canonical class:",
        ]
    )

    mean_kl_by_class: dict[str, float] = summary["mean_kl_by_class"]
    if mean_kl_by_class:
        for canonical_class, kl_value in sorted(mean_kl_by_class.items()):
            lines.append(f"- `{canonical_class}`: {kl_value:.6f}")
    else:
        lines.append("- No shared classes found between MQTT and CoAP for KL computation.")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `feature_summary_overall.csv`",
            "- `feature_summary_by_protocol.csv`",
            "- `kl_alignment_by_class.csv`",
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate normalized feature quality and cross-protocol alignment")
    parser.add_argument("--in", dest="in_csv", default="/home/billy/X/SentriX/data/raw/week3_runs_labeled.csv")
    parser.add_argument("--out-dir", dest="out_dir", default="/home/billy/X/SentriX/ml-pipeline/reports")
    parser.add_argument("--report", dest="report", default="/home/billy/X/SentriX/ml-pipeline/reports/week3_feature_quality.md")
    args = parser.parse_args()

    summary = validate_feature_quality(in_csv=Path(args.in_csv), out_dir=Path(args.out_dir))
    _write_markdown_report(summary, out_path=Path(args.report))

    print(f"Validated feature quality for {summary['row_count']} rows and {summary['run_count']} runs")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
