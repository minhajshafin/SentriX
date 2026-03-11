#!/usr/bin/env python3
"""
Week 6: Train and Export Champion Model (LightGBM)

Objectives:
  1. Re-train LightGBM (full features) selected from Week 5 analysis
  2. Save trained model for compression
  3. Export to ONNX format
  4. Validate ONNX against original
  5. Document feature specifications for C++ proxy integration
"""

import json
import pickle
import argparse
import warnings
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedGroupKFold

warnings.filterwarnings('ignore')

# Try to import LightGBM
try:
    from lightgbm import LGBMClassifier
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
    print("⚠️  LightGBM not installed. Install with: pip install lightgbm")

def load_dataset(data_file: Path) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Load and preprocess the Week 3 labeled dataset."""
    print(f"\n[1] Loading dataset from {data_file}...")
    df = pd.read_csv(data_file)
    print(f"    ✓ Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Extract features (33 dimensions: normalized + pid + auxiliary)
    FULL_FEATURES = [f"f{i:02d}" for i in range(33)]
    
    X = df[FULL_FEATURES].values.astype(np.float32)
    
    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(df['label'])
    
    # Group information for cross-validation (prevent run leakage)
    groups = df['run_id'].values
    
    print(f"    ✓ X shape: {X.shape}")
    print(f"    ✓ y shape: {y.shape}")
    print(f"    ✓ Classes: {list(le.classes_)}")
    print(f"    ✓ Groups (runs): {len(np.unique(groups))}")
    
    return df, X, y, groups, le

def train_champion_model(
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    output_dir: Path,
    random_state: int = 42
) -> Tuple[LGBMClassifier, LabelEncoder]:
    """
    Train the selected LightGBM champion model.
    
    Uses hyperparameters from Week 5 best performance.
    """
    
    if not HAS_LGBM:
        raise ImportError("LightGBM required for Week 6. Install with: pip install lightgbm")
    
    print(f"\n[2] Training LightGBM (champion model)...")
    
    # LightGBM hyperparameters (from Week 5 best performance)
    model = LGBMClassifier(
        objective='multiclass',
        num_class=6,
        num_leaves=31,
        max_depth=7,
        learning_rate=0.05,
        n_estimators=100,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=5,
        min_child_samples=20,
        random_state=random_state,
        verbose=-1,
        n_jobs=-1,
    )
    
    # Train on full dataset (no hold-out; for deployment model)
    # Note: In production, would use grouped CV results to estimate generalization
    print("    Training on full dataset (deployment model)...")
    model.fit(X, y)
    
    print(f"    ✓ Model trained with {model.n_estimators} trees")
    print(f"    ✓ Feature importance (top 10):")
    
    importances = model.feature_importances_
    top_indices = np.argsort(importances)[-10:][::-1]
    for rank, idx in enumerate(top_indices, 1):
        print(f"      {rank:2d}. f{idx:02d}: {importances[idx]:.4f}")
    
    return model

def save_model(model: LGBMClassifier, output_dir: Path, name: str = "lightgbm_full") -> Path:
    """Save trained model to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = output_dir / f"{name}.pkl"
    print(f"\n[3] Saving trained model...")
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    size_mb = model_path.stat().st_size / (1024 ** 2)
    print(f"    ✓ Model saved to {model_path} ({size_mb:.2f} MB)")
    
    return model_path

def export_onnx(model: LGBMClassifier, output_dir: Path, name: str = "lightgbm_full") -> Path:
    """Export model to ONNX format."""
    print(f"\n[4] Exporting to ONNX format...")
    
    try:
        import onnx
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError:
        print("    ⚠️  skl2onnx not installed. Install with: pip install skl2onnx onnx")
        return None
    
    # Define input type: single float32 sample with 33 features
    initial_type = [('float_input', FloatTensorType([None, 33]))]
    
    # Convert scikit-learn-compatible LGBMClassifier to ONNX
    try:
        onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
    except Exception as e:
        print(f"    ✗ ONNX conversion failed: {e}")
        return None
    
    # Save ONNX model
    output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = output_dir / f"{name}.onnx"
    
    with open(onnx_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())
    
    size_mb = onnx_path.stat().st_size / (1024 ** 2)
    print(f"    ✓ ONNX model saved to {onnx_path} ({size_mb:.2f} MB)")
    
    return onnx_path

def validate_onnx_export(
    model: LGBMClassifier,
    onnx_path: Path,
    X_sample: np.ndarray,
    y_sample: np.ndarray
) -> dict:
    """
    Validate ONNX export against original model.
    
    Args:
        model: Original trained model
        onnx_path: Path to ONNX model file
        X_sample: Sample features for validation
        y_sample: Sample labels
    
    Returns:
        Validation report dict
    """
    print(f"\n[5] Validating ONNX export against original...")
    
    try:
        import onnxruntime as rt
    except ImportError:
        print("    ⚠️  onnxruntime not installed. Install with: pip install onnxruntime")
        return {}
    
    # Get predictions from original model
    pred_original_proba = model.predict_proba(X_sample)
    pred_original = model.predict(X_sample)
    
    # Get predictions from ONNX model
    sess = rt.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    input_name = sess.get_inputs()[0].name
    output_labels = sess.get_outputs()[0].name
    output_probas = sess.get_outputs()[1].name if len(sess.get_outputs()) > 1 else None
    
    # Run inference
    outputs = sess.run([output_labels, output_probas] if output_probas else [output_labels],
                      {input_name: X_sample.astype(np.float32)})
    
    pred_onnx = outputs[0]
    pred_onnx_proba = outputs[1] if output_probas else None
    
    # Compare predictions
    agreement = np.mean(pred_original == pred_onnx)
    
    # Compare with ground truth
    from sklearn.metrics import accuracy_score, f1_score
    acc_original = accuracy_score(y_sample, pred_original)
    acc_onnx = accuracy_score(y_sample, pred_onnx)
    
    f1_original = f1_score(y_sample, pred_original, average='macro', zero_division=0)
    f1_onnx = f1_score(y_sample, pred_onnx, average='macro', zero_division=0)
    
    report = {
        "validation_samples": len(X_sample),
        "prediction_agreement": float(agreement),
        "accuracy_original": float(acc_original),
        "accuracy_onnx": float(acc_onnx),
        "accuracy_delta": float(abs(acc_original - acc_onnx)),
        "f1_macro_original": float(f1_original),
        "f1_macro_onnx": float(f1_onnx),
        "f1_macro_delta": float(abs(f1_original - f1_onnx)),
        "status": "✓ PASS" if agreement > 0.99 else "⚠️  WARN" if agreement > 0.95 else "✗ FAIL",
    }
    
    print(f"    ✓ Prediction agreement: {agreement:.4f}")
    print(f"    ✓ Accuracy delta: {report['accuracy_delta']:.6f}")
    print(f"    ✓ F1-macro delta: {report['f1_macro_delta']:.6f}")
    print(f"    {report['status']}")
    
    return report

def generate_feature_spec(
    label_encoder,
    output_dir: Path
) -> Path:
    """
    Generate feature specification for C++ proxy integration.
    
    Documents:
    - Feature names and order
    - Input shape (33 dimensions)
    - Class mapping
    - Normalization parameters (from dataset statistics)
    """
    print(f"\n[6] Generating feature specification...")
    
    spec = {
        "model": "lightgbm_full",
        "input_shape": [None, 33],
        "input_dtype": "float32",
        "num_classes": len(label_encoder.classes_),
        "output_classes": list(label_encoder.classes_),
        "class_indices": {cls: int(idx) for idx, cls in enumerate(label_encoder.classes_)},
        "features": {
            "normalized": [f"f{i:02d}" for i in range(15)],
            "protocol_identifier": [f"f{i:02d}" for i in range(15, 17)],
            "mqtt_auxiliary": [f"f{i:02d}" for i in range(17, 25)],
            "coap_auxiliary": [f"f{i:02d}" for i in range(25, 33)],
        },
        "total_features": 33,
        "deployment_notes": [
            "Input vector must be 33-dimensional float32 array",
            "Features must be in order f00 through f32",
            "All features must be normalized to [0, 1] range",
            "Protocol identifier (f15, f16) must be one-hot (MQTT=[1,0], CoAP=[0,1])",
            "MQTT auxiliary features (f17-f24) should be zero-padded for CoAP traffic",
            "CoAP auxiliary features (f25-f32) should be zero-padded for MQTT traffic",
        ],
    }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = output_dir / "week6_feature_spec.json"
    
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)
    
    print(f"    ✓ Feature spec saved to {spec_path}")
    
    return spec_path

def main():
    parser = argparse.ArgumentParser(description="Week 6: Train and Export Champion Model")
    parser.add_argument("--in-data", type=Path, default=Path("data/raw/week3_runs_labeled.csv"),
                       help="Input dataset (Week 3 labeled)")
    parser.add_argument("--out-dir", type=Path, default=Path("ml-pipeline/models"),
                       help="Output directory for models")
    parser.add_argument("--report-dir", type=Path, default=Path("ml-pipeline/reports"),
                       help="Output directory for reports")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("WEEK 6: LIGHTGBM CHAMPION MODEL - TRAIN & EXPORT")
    print("=" * 70)
    
    if not args.in_data.exists():
        print(f"✗ Dataset not found: {args.in_data}")
        return 1
    
    # Load dataset
    df, X, y, groups, label_encoder = load_dataset(args.in_data)
    
    # Train champion model
    model = train_champion_model(X, y, groups, args.out_dir, random_state=args.seed)
    
    # Save model
    model_path = save_model(model, args.out_dir)
    
    # Export to ONNX
    onnx_path = export_onnx(model, args.out_dir)
    
    # Validate ONNX (use 20% of data)
    idx = np.random.RandomState(args.seed).choice(len(X), size=max(1000, len(X) // 5), replace=False)
    validation_report = validate_onnx_export(model, onnx_path, X[idx], y[idx])
    
    # Generate feature spec
    spec_path = generate_feature_spec(label_encoder, args.report_dir)
    
    # Save validation report
    validation_report_path = args.report_dir / "week6_onnx_validation.json"
    with open(validation_report_path, 'w') as f:
        json.dump(validation_report, f, indent=2)
    print(f"    ✓ Validation report saved to {validation_report_path}")
    
    print("\n" + "=" * 70)
    print("WEEK 6 COMPLETE - MODELS READY FOR C++ PROXY INTEGRATION")
    print("=" * 70)
    print(f"\nDeliverables:")
    print(f"  Trained Model:  {model_path}")
    print(f"  ONNX Export:    {onnx_path}")
    print(f"  Feature Spec:   {spec_path}")
    print(f"  Validation:     {validation_report_path}")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
