#!/usr/bin/env python3

import json
import numpy as np
from pathlib import Path

DEBUG_PATH = Path("/tmp/sentrix-week8/features.jsonl")


def analyze_feature_drift() -> dict:
    """Compare legacy vs behavioral feature vectors from capture."""
    if not DEBUG_PATH.exists():
        return {"error": "no feature debug file found"}

    rows = [
        json.loads(line) for line in DEBUG_PATH.read_text().splitlines() if line.strip()
    ]

    if not rows:
        return {"error": "no rows in feature debug file"}

    # Extract vectors
    legacy_vecs = np.array([row["legacy"] for row in rows])
    behavioral_vecs = np.array([row["behavioral"] for row in rows])

    # Feature analysis
    drift_per_dim = {}
    for i in range(len(legacy_vecs[0])):
        legacy_col = legacy_vecs[:, i]
        behavioral_col = behavioral_vecs[:, i]
        drift = np.abs(behavioral_col - legacy_col)
        drift_per_dim[f"f{i:02d}"] = {
            "legacy_mean": float(np.mean(legacy_col)),
            "legacy_std": float(np.std(legacy_col)),
            "behavioral_mean": float(np.mean(behavioral_col)),
            "behavioral_std": float(np.std(behavioral_col)),
            "drift_mean": float(np.mean(drift)),
            "drift_max": float(np.max(drift)),
        }

    # Sort by drift magnitude
    top_drift = sorted(
        drift_per_dim.items(), key=lambda x: x[1]["drift_mean"], reverse=True
    )[:5]

    report = {
        "total_packets": len(rows),
        "feature_dimensions": len(legacy_vecs[0]),
        "packets_with_behavioral_active": sum(1 for r in rows if r.get("behavioral_enabled")),
        "top_drifting_features": dict(top_drift),
        "all_feature_drift": drift_per_dim,
    }

    return report


if __name__ == "__main__":
    result = analyze_feature_drift()
    
    output_path = Path("/tmp/sentrix-week8/feature_drift_analysis.json")
    output_path.write_text(json.dumps(result, indent=2))
    print(f"Feature drift analysis saved to {output_path}")
    print(json.dumps(result, indent=2)[:1000] + "...")
