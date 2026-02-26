from __future__ import annotations

import argparse
import random
import time

from simulators.common.feature_schema import FeatureRecord, append_csv, now_iso, pad_features


def random_norm_features() -> list[float]:
    return [
        random.uniform(0.05, 0.30),
        random.uniform(0.40, 0.70),
        random.uniform(0.05, 0.20),
        random.uniform(0.40, 0.80),
        random.uniform(0.10, 0.40),
        random.uniform(0.20, 0.60),
        random.choice([0.0, 0.5, 1.0]),
        random.uniform(0.30, 0.90),
        random.uniform(0.05, 0.30),
        random.uniform(0.00, 0.05),
        random.uniform(0.00, 0.30),
        random.uniform(0.00, 0.20),
        random.uniform(0.00, 0.15),
        random.uniform(0.05, 0.20),
        random.uniform(0.90, 1.00),
    ]


def random_mqtt_aux() -> list[float]:
    return [
        random.choice([0.0, 1.0]),
        random.uniform(0.0, 0.2),
        random.uniform(0.8, 1.0),
        random.uniform(0.3, 0.8),
        random.choice([0.0, 1.0]),
        random.uniform(0.9, 1.0),
        random.uniform(0.4, 0.9),
        random.uniform(0.05, 0.25),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT benign traffic feature simulator")
    parser.add_argument("--out", default="data/features/unified_features.csv")
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--sleep-ms", type=int, default=10)
    args = parser.parse_args()

    for index in range(args.count):
        record = FeatureRecord(
            timestamp=now_iso(),
            protocol="mqtt",
            source_id=f"mqtt-sensor-{index % 10}",
            attack_label="benign",
            attack_family="none",
            features=pad_features(random_norm_features(), "mqtt", random_mqtt_aux()),
        )
        append_csv(args.out, record)
        time.sleep(args.sleep_ms / 1000.0)


if __name__ == "__main__":
    main()
