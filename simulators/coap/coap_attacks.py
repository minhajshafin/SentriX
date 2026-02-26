from __future__ import annotations

import argparse
import random

from simulators.common.feature_schema import FeatureRecord, append_csv, now_iso, pad_features

ATTACKS = [
    "request_flood",
    "observe_amplification",
    "token_exhaustion",
    "blockwise_abuse",
    "resource_discovery_flood",
]


def attack_norm_features(attack: str) -> list[float]:
    features = [
        random.uniform(0.75, 1.0),
        random.uniform(0.0, 0.3),
        random.uniform(0.3, 0.9),
        random.uniform(0.0, 0.5),
        random.uniform(0.2, 1.0),
        random.uniform(0.3, 1.0),
        random.choice([0.0, 1.0]),
        random.uniform(0.0, 0.8),
        random.uniform(0.4, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.3, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.2, 1.0),
        random.uniform(0.0, 0.8),
    ]

    if attack == "observe_amplification":
        features[11] = random.uniform(0.7, 1.0)

    return features


def attack_coap_aux(attack: str) -> list[float]:
    if attack == "observe_amplification":
        return [0.7, 0.2, 0.1, 0.0, 1.0, 0.0, 0.5, 0.4]
    if attack == "token_exhaustion":
        return [0.4, 0.5, 0.1, 0.0, 0.0, 0.0, 1.0, 0.6]
    return [0.6, 0.2, 0.2, 0.0, 0.0, 1.0, 0.3, 0.7]


def main() -> None:
    parser = argparse.ArgumentParser(description="CoAP attack feature simulator")
    parser.add_argument("--out", default="data/features/unified_features.csv")
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    for index in range(args.count):
        attack = random.choice(ATTACKS)
        record = FeatureRecord(
            timestamp=now_iso(),
            protocol="coap",
            source_id=f"coap-attacker-{index % 5}",
            attack_label=attack,
            attack_family="coap_attack",
            features=pad_features(attack_norm_features(attack), "coap", attack_coap_aux(attack)),
        )
        append_csv(args.out, record)


if __name__ == "__main__":
    main()
