# SentriX Dataset and Artifacts Release

## Files in This Release

| File | Size | Description |
|---|---|---|
| `week3_runs_labeled.csv` | ~3 MB | Primary labeled dataset: 11,209 records × 43 columns |
| `lightgbm_full.onnx` | 1.2 MB | Trained LightGBM champion model in ONNX format |
| `train_baselines.py` | ~12 KB | Training script: reproduces all baseline models |
| `DATASET_README.md` | 6 KB | Full feature documentation and usage guide |
| `PAPER.pdf` | ~1.8 MB | Accepted conference paper (IEEE CCNC / ISCC 2026) |

## How to Reproduce the Paper Results

### 1. Install dependencies

```bash
pip install lightgbm scikit-learn pandas numpy onnxmltools onnxruntime
```

### 2. Run baseline comparison (Table III in paper)

```bash
python train_baselines.py --data week3_runs_labeled.csv --cv grouped --folds 5
```

This reproduces the grouped 5-fold cross-validation results for all four model families (Logistic Regression, Random Forest, MLP, LightGBM) on both feature subsets.

### 3. Cross-protocol transfer evaluation

```bash
python train_baselines.py --data week3_runs_labeled.csv --cv cross_protocol
```

Runs MQTT→CoAP and CoAP→MQTT transfer experiments, reproducing the generalization gap results.

### 4. ONNX export verification

```python
import onnxruntime as rt
import numpy as np

sess = rt.InferenceSession("lightgbm_full.onnx")
# 33-dimensional zero vector (benign baseline)
x = np.zeros((1, 33), dtype=np.float32)
out = sess.run(None, {sess.get_inputs()[0].name: x})
print("ONNX output:", out)
```

## Dataset Construction

The dataset was collected from a controlled testbed running:
- Eclipse Mosquitto 2 MQTT broker (TCP/1883)
- Eclipse Californium CoAP server (UDP/5683)
- SentriX C++17 reverse proxy (MQTT TCP/1884, CoAP UDP/5684)

Traffic generators used:
- Paho MQTT Python client for MQTT scenarios
- aiocoap Python library for CoAP scenarios

Each of 21 controlled runs executes one scenario for approximately 120–300 seconds. Feature vectors are extracted per-packet at the proxy ingress. Labels are assigned at the run level (all packets in a run share the run's label).

## License

- **Dataset** (`week3_runs_labeled.csv`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Model** (`lightgbm_full.onnx`): [MIT License](https://opensource.org/licenses/MIT)
- **Code** (`train_baselines.py`): [MIT License](https://opensource.org/licenses/MIT)

## Citation

```bibtex
@inproceedings{shafin2026sentrix,
  title={{SentriX}: A Middleware-Independent Multi-Stage Security Proxy
         for Heterogeneous {IoT} Protocols},
  author={Shafin, Minhajul Haque},
  booktitle={Proc. IEEE Consumer Communications and Networking Conf. (CCNC)},
  address={Las Vegas, NV, USA},
  year={2026},
  note={Dataset and artifacts available at \url{https://doi.org/10.5281/zenodo.XXXXXXX}}
}
```

## Contact

Minhajul Haque Shafin  
East West University, Dhaka, Bangladesh  
2022-2-60-054@std.ewubd.edu
