from __future__ import annotations

import argparse
import random

from simulators.common.feature_schema import FeatureRecord, append_csv, now_iso, pad_features

ATTACKS = [
    "publish_flood",
    "slowite",
    "wildcard_abuse",
    "qos2_amplification",
    "malformed_packet",
]


def attack_norm_features(attack: str) -> list[float]:
    base = [
        random.uniform(0.7, 1.0),
        random.uniform(0.0, 0.3),
        random.uniform(0.6, 1.0),
        random.uniform(0.0, 0.5),
        random.uniform(0.1, 1.0),
        random.uniform(0.4, 1.0),
        random.choice([0.0, 0.5, 1.0]),
        random.uniform(0.0, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.0, 0.8),
    ]

    if attack == "slowite":
        base[1] = random.uniform(0.8, 1.0)
        base[12] = random.uniform(0.6, 1.0)

    return base


def attack_mqtt_aux(attack: str) -> list[float]:
    if attack == "wildcard_abuse":
        return [1.0, 1.0, 0.3, 0.6, 0.0, 0.4, 0.8, 0.6]
    if attack == "qos2_amplification":
        return [0.0, 0.3, 0.2, 0.5, 0.0, 0.2, 0.5, 0.7]
    return [0.0, 0.2, 0.6, 0.3, 0.0, 0.7, 0.4, 0.8]


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT attack feature simulator")
    parser.add_argument("--out", default="data/features/unified_features.csv")
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    for index in range(args.count):
        attack = random.choice(ATTACKS)
        record = FeatureRecord(
            timestamp=now_iso(),
            protocol="mqtt",
            source_id=f"mqtt-attacker-{index % 5}",
            attack_label=attack,
            attack_family="mqtt_attack",
            features=pad_features(attack_norm_features(attack), "mqtt", attack_mqtt_aux(attack)),
        )
        append_csv(args.out, record)


if __name__ == "__main__":
    main()
