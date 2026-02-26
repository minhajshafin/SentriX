from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
import csv
import os

NORMALIZED_DIM = 15
PROTOCOL_ID_DIM = 2
MQTT_AUX_DIM = 8
COAP_AUX_DIM = 8
TOTAL_DIM = NORMALIZED_DIM + PROTOCOL_ID_DIM + MQTT_AUX_DIM + COAP_AUX_DIM

FEATURE_COLUMNS = [f"f{i:02d}" for i in range(TOTAL_DIM)]


@dataclass
class FeatureRecord:
    timestamp: str
    protocol: str
    source_id: str
    attack_label: str
    attack_family: str
    features: List[float]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def protocol_id(protocol: str) -> List[float]:
    if protocol == "mqtt":
        return [1.0, 0.0]
    if protocol == "coap":
        return [0.0, 1.0]
    raise ValueError(f"unsupported protocol: {protocol}")


def pad_features(normalized: List[float], protocol: str, aux: List[float]) -> List[float]:
    if len(normalized) != NORMALIZED_DIM:
        raise ValueError(f"normalized feature length must be {NORMALIZED_DIM}")
    if len(aux) != 8:
        raise ValueError("aux feature length must be 8")

    pid = protocol_id(protocol)

    if protocol == "mqtt":
        mqtt_aux = aux
        coap_aux = [0.0] * COAP_AUX_DIM
    elif protocol == "coap":
        mqtt_aux = [0.0] * MQTT_AUX_DIM
        coap_aux = aux
    else:
        raise ValueError(f"unsupported protocol: {protocol}")

    return normalized + pid + mqtt_aux + coap_aux


def append_csv(path: str, record: FeatureRecord) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    exists = os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        if not exists:
            writer.writerow([
                "timestamp",
                "protocol",
                "source_id",
                "attack_label",
                "attack_family",
                *FEATURE_COLUMNS,
            ])

        writer.writerow([
            record.timestamp,
            record.protocol,
            record.source_id,
            record.attack_label,
            record.attack_family,
            *record.features,
        ])
