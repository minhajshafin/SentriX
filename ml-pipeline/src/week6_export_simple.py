#!/usr/bin/env python3
"""
Week 6: Export LightGBM to ONNX (Simplified)

Uses onnxmltools for LightGBM conversion or provides manual ONNX creation.
"""

import pickle
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

def main():
    """Export and validate LightGBM ONNX model."""
    print("\n" + "="*70)
    print("Week 6: ONNX Export and Validation")
    print("="*70)
    
    # Load trained model
    print("\n[1] Loading trained LightGBM model...")
    model_path = Path("ml-pipeline/models/lightgbm_full.pkl")
    if not model_path.exists():
        print(f"✗ Model not found: {model_path}")
        return 1
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    model_size_mb = model_path.stat().st_size / (1024**2)
    print(f"✓ Model loaded ({model_size_mb:.2f} MB)")
    print(f"  Type: {type(model)}")
    print(f"  Features: {model.n_features_in_}")
    print(f"  Classes: {len(model.classes_)}")
    
    # Try to export ONNX
    print("\n[2] Exporting to ONNX format...")
    onnx_path = Path("ml-pipeline/models/lightgbm_full.onnx")
    onnx_created = False
    
    try:
        # Method 1: Try onnxmltools
        try:
            import onnxmltools
            print("  Using onnxmltools for conversion...")
            
            # Convert LightGBM to ONNX
            onnx_model = onnxmltools.convert_lightgbm(model)
            onnxmltools.utils.save_model(onnx_model, str(onnx_path))
            onnx_created = True
            print(f"✓ ONNX export successful")
            print(f"  Path: {onnx_path}")
            print(f"  Size: {onnx_path.stat().st_size / (1024**2):.2f} MB")
            
        except ImportError:
            print("  onnxmltools not available, trying skl2onnx...")
            
            # Method 2: Try skl2onnx with proper LightGBM wrapper
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            
            print("  Using skl2onnx for conversion...")
            initial_type = [('float_input', FloatTensorType([None, 33]))]
            onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
            
            with open(onnx_path, 'wb') as f:
                f.write(onnx_model.SerializeToString())
            onnx_created = True
            print(f"✓ ONNX export successful")
            print(f"  Path: {onnx_path}")
            print(f"  Size: {onnx_path.stat().st_size / (1024**2):.2f} MB")
            
    except Exception as e:
        print(f"⚠️  ONNX export not possible with current toolchain:")
        print(f"  Error: {e}")
        print(f"\n  To enable ONNX export, install: pip install onnxmltools")
        print(f"  The pickle model ({model_size_mb:.2f} MB) is still available for deployment.")
    
    # Load dataset for validation
    print("\n[3] Loading validation dataset...")
    data_path = Path("data/raw/week3_runs_labeled.csv")
    if not data_path.exists():
        print(f"✗ Dataset not found: {data_path}")
        return 1
    
    df = pd.read_csv(data_path)
    FULL_FEATURES = [f"f{i:02d}" for i in range(33)]
    X = df[FULL_FEATURES].values.astype(np.float32)
    
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y = le.fit_transform(df['label'])
    
    # Use subset for faster validation
    np.random.seed(42)
    idx = np.random.choice(len(X), min(2000, len(X)), replace=False)
    X_val, y_val = X[idx], y[idx]
    
    print(f"✓ Loaded {len(X_val)} validation samples")
    print(f"  Classes: {list(le.classes_)}")
    print(f"  Y distribution: {np.bincount(y_val)}")
    
    # Validate ONNX if created
    if onnx_created:
        print("\n[4] Validating ONNX predictions...")
        try:
            import onnxruntime as rt
            
            # Original model predictions
            pred_orig = model.predict(X_val)
            
            # ONNX predictions
            sess = rt.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
            input_name = sess.get_inputs()[0].name
            output_names = [o.name for o in sess.get_outputs()]
            
            outputs = sess.run(output_names, {input_name: X_val})
            pred_onnx = outputs[0].astype(np.int64)
            
            # Compare
            agreement = np.mean(pred_orig == pred_onnx)
            
            from sklearn.metrics import accuracy_score, f1_score
            acc_orig = accuracy_score(y_val, pred_orig)
            acc_onnx = accuracy_score(y_val, pred_onnx)
            f1_orig = f1_score(y_val, pred_orig, average='macro', zero_division=0)
            f1_onnx = f1_score(y_val, pred_onnx, average='macro', zero_division=0)
            
            print(f"✓ Validation complete:")
            print(f"  Prediction agreement: {agreement:.4f} ({100*agreement:.1f}%)")
            print(f"  Original accuracy: {acc_orig:.4f}")
            print(f"  ONNX accuracy: {acc_onnx:.4f}")
            print(f"  Accuracy delta: {abs(acc_orig - acc_onnx):.6f}")
            print(f"  Original F1-macro: {f1_orig:.4f}")
            print(f"  ONNX F1-macro: {f1_onnx:.4f}")
            print(f"  F1-macro delta: {abs(f1_orig - f1_onnx):.6f}")
            
            status = "✓ PASS" if agreement > 0.99 else "⚠️  WARN" if agreement > 0.95 else "✗ FAIL"
            print(f"  Validation Status: {status}")
            
            # Save validation report
            validation_report = {
                "validation_samples": int(len(X_val)),
                "prediction_agreement": float(agreement),
                "accuracy_original": float(acc_orig),
                "accuracy_onnx": float(acc_onnx),
                "accuracy_delta": float(abs(acc_orig - acc_onnx)),
                "f1_macro_original": float(f1_orig),
                "f1_macro_onnx": float(f1_onnx),
                "f1_macro_delta": float(abs(f1_orig - f1_onnx)),
                "status": status,
            }
            
            report_path = Path("ml-pipeline/reports/week6_onnx_validation.json")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                json.dump(validation_report, f, indent=2)
            print(f"\n✓ Validation report saved to {report_path}")
            
        except ImportError:
            print("⚠️  onnxruntime not installed (optional). Skipping validation.")
        except Exception as e:
            print(f"⚠️  Validation failed: {e}")
    else:
        print("\n[4] Skipping ONNX validation (ONNX not created)")
        print("  The pickle model is available for Python-based deployments")
    
    # Generate feature spec
    print("\n[5] Generating feature specification...")
    spec = {
        "model": "lightgbm_full",
        "pickle_path": str(model_path),
        "onnx_path": str(onnx_path) if onnx_created else None,
        "input_shape": [None, 33],
        "input_dtype": "float32",
        "num_classes": len(le.classes_),
        "output_classes": list(le.classes_),
        "class_indices": {cls: int(idx) for idx, cls in enumerate(le.classes_)},
        "model_info": {
            "n_features": int(model.n_features_in_),
            "n_classes": len(model.classes_),
            "pkl_size_mb": round(model_size_mb, 2),
        },
        "features": {
            "normalized": [f"f{i:02d}" for i in range(15)],
            "protocol_identifier": [f"f{i:02d}" for i in range(15, 17)],
            "mqtt_auxiliary": [f"f{i:02d}" for i in range(17, 25)],
            "coap_auxiliary": [f"f{i:02d}" for i in range(25, 33)],
        },
        "deployment_notes": [
            "Input vector: 33-dimensional float32 array",
            "Features in order: f00 through f32",
            "All features must be normalized to [0,1] range",
            "Protocol ID (f15,f16): one-hot [1,0] for MQTT, [0,1] for CoAP",
            "MQTT aux (f17-f24): zero-pad for CoAP traffic",
            "CoAP aux (f25-f32): zero-pad for MQTT traffic",
        ],
    }
    
    spec_path = Path("ml-pipeline/reports/week6_feature_spec.json")
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"✓ Feature spec saved to {spec_path}")
    
    # Summary
    print("\n" + "="*70)
    print("Week 6 Export Complete")
    print("="*70)
    print(f"\nDeliverables:")
    print(f"  Pickle Model: ml-pipeline/models/lightgbm_full.pkl ({model_size_mb:.2f} MB)")
    if onnx_created:
        print(f"  ONNX Model:   ml-pipeline/models/lightgbm_full.onnx")
        print(f"  Validation:   ml-pipeline/reports/week6_onnx_validation.json")
    print(f"  Feature Spec: ml-pipeline/reports/week6_feature_spec.json")
    print(f"  Analysis:     ml-pipeline/reports/week6_model_selections.md")
    
    print(f"\nNext Steps:")
    print(f"  1. Review model selection analysis")
    print(f"  2. Integrate pickle model into Python-based deployments")
    if onnx_created:
        print(f"  3. Integrate ONNX model into C++ proxy (Week 7)")
    else:
        print(f"  3. Install onnxmltools and re-run for C++ integration")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
