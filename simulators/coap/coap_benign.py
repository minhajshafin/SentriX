from __future__ import annotations

import argparse
import random
import time

from simulators.common.feature_schema import FeatureRecord, append_csv, now_iso, pad_features


def random_norm_features() -> list[float]:
    return [
        random.uniform(0.05, 0.35),
        random.uniform(0.35, 0.75),
        random.uniform(0.05, 0.20),
        random.uniform(0.35, 0.70),
        random.uniform(0.10, 0.35),
        random.uniform(0.20, 0.60),
        random.choice([0.0, 1.0]),
        random.uniform(0.10, 0.50),
        random.uniform(0.05, 0.25),
        random.uniform(0.00, 0.07),
        random.uniform(0.10, 0.40),
        random.uniform(0.00, 0.20),
        random.uniform(0.00, 0.20),
        random.uniform(0.05, 0.20),
        random.uniform(0.90, 1.00),
    ]


def random_coap_aux() -> list[float]:
    return [
        random.uniform(0.5, 0.9),
        random.uniform(0.1, 0.4),
        random.uniform(0.0, 0.1),
        random.uniform(0.0, 0.1),
        random.choice([0.0, 1.0]),
        random.choice([0.0, 1.0]),
        random.uniform(0.0, 0.2),
        random.uniform(0.1, 0.4),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="CoAP benign traffic feature simulator")
    parser.add_argument("--out", default="data/features/unified_features.csv")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--sleep-ms", type=int, default=10)
    args = parser.parse_args()

    for index in range(args.count):
        record = FeatureRecord(
            timestamp=now_iso(),
            protocol="coap",
            source_id=f"coap-sensor-{index % 10}",
            attack_label="benign",
            attack_family="none",
            features=pad_features(random_norm_features(), "coap", random_coap_aux()),
        )
        append_csv(args.out, record)
        time.sleep(args.sleep_ms / 1000.0)


if __name__ == "__main__":
    main()
