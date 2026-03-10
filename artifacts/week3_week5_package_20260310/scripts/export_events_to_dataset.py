from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulators.common.feature_schema import FEATURE_COLUMNS, pad_features

OUTPUT_COLUMNS = [
    "run_id",
    "scenario",
    "label",
    "rep",
    "timestamp",
    "protocol",
    "direction",
    "event",
    "bytes",
    "detail",
    *FEATURE_COLUMNS,
]


def _to_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return fallback


def _norm(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return max(0.0, min(value / cap, 1.0))


def _event_to_features(event: dict) -> list[float]:
    protocol = str(event.get("protocol", "")).strip().lower()
    direction = str(event.get("direction", "")).strip().lower()
    event_type = str(event.get("event", "")).strip().lower()
    detail = str(event.get("detail", "")).strip().lower()
    byte_count = _to_float(event.get("bytes", 0))

    msg_rate = 1.0 if event_type == "traffic" else 0.2
    inter_arrival = 0.5
    payload_size = _norm(math.log1p(max(byte_count, 0.0)), math.log1p(4096.0))
    payload_entropy = 0.5 if byte_count > 0 else 0.0

    if protocol == "mqtt":
        resource_depth = 0.25
        resource_entropy = 0.45
        qos_level = 0.5
        session_duration = 0.5
        unique_resource_count = 0.2
        error_rate = 0.6 if "error" in detail or "abuse" in detail else 0.05
        handshake_complexity = 0.6 if event_type == "connection_open" else 0.2
        subscription_breadth = 0.7 if "wildcard" in detail else 0.15
        reconnection_rate = 0.8 if event_type == "connection_open" else 0.2
        payload_to_resource_ratio = _norm(byte_count / 20.0, 50.0)
        compliance = 0.3 if "malform" in detail else 0.95
        aux = [
            0.0,
            1.0 if "wildcard" in detail else 0.0,
            1.0 if event_type == "connection_open" else 0.2,
            0.6,
            0.0,
            0.2,
            0.5,
            _norm(byte_count, 2048.0),
        ]
    else:
        resource_depth = 0.3
        resource_entropy = 0.5
        qos_level = 1.0 if "con" in detail else 0.0
        session_duration = 0.3
        unique_resource_count = 0.25
        error_rate = 0.6 if "error" in detail or "abuse" in detail else 0.05
        handshake_complexity = 0.6 if direction == "outgoing" else 0.2
        subscription_breadth = 0.4
        reconnection_rate = 0.3
        payload_to_resource_ratio = _norm(byte_count / 16.0, 64.0)
        compliance = 0.3 if "malform" in detail else 0.95
        aux = [0.0] * 8

    normalized = [
        msg_rate,
        inter_arrival,
        payload_size,
        payload_entropy,
        resource_depth,
        resource_entropy,
        qos_level,
        session_duration,
        unique_resource_count,
        error_rate,
        handshake_complexity,
        subscription_breadth,
        reconnection_rate,
        payload_to_resource_ratio,
        compliance,
    ]

    return pad_features(normalized, protocol, aux)


def _read_events_from_lines(lines: list[str]) -> list[dict]:
    events: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _build_rows(events: list[dict], run_id: str, scenario: str, label: str, rep: int) -> list[dict]:
    rows: list[dict] = []

    for event in events:
        protocol = str(event.get("protocol", "")).strip().lower()
        if protocol not in {"mqtt", "coap"}:
            continue

        feature_values = _event_to_features(event)

        row = {
            "run_id": run_id,
            "scenario": scenario,
            "label": label,
            "rep": rep,
            "timestamp": event.get("ts", ""),
            "protocol": protocol,
            "direction": event.get("direction", ""),
            "event": event.get("event", ""),
            "bytes": int(_to_float(event.get("bytes", 0))),
            "detail": event.get("detail", ""),
        }

        for feature_name, feature_value in zip(FEATURE_COLUMNS, feature_values, strict=True):
            row[feature_name] = feature_value

        rows.append(row)

    return rows


def _write_rows(rows: list[dict], out_csv: Path, append: bool) -> int:
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    file_exists = out_csv.exists()
    mode = "a" if append else "w"
    with out_csv.open(mode, newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_COLUMNS)
        if not append or not file_exists:
            writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def _read_events_from_file(events_path: Path) -> list[dict]:
    if not events_path.exists():
        return []
    return _read_events_from_lines(events_path.read_text(encoding="utf-8").splitlines())


def _read_events_from_api(events_api: str) -> list[dict]:
    with urlopen(events_api, timeout=10) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
    return body.get("events", [])


def extract_labeled_features(
    *,
    events_path: Path | None,
    events_api: str,
    out_csv: Path,
    run_id: str,
    scenario: str,
    label: str,
    rep: int,
    append: bool,
) -> int:
    events = _read_events_from_file(events_path) if events_path else _read_events_from_api(events_api)
    rows = _build_rows(events, run_id=run_id, scenario=scenario, label=label, rep=rep)
    return _write_rows(rows, out_csv=out_csv, append=append)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract labeled SentriX feature rows (run-aware, 33-dim) from events source"
    )
    parser.add_argument("--events", default="")
    parser.add_argument("--events-api", default="http://localhost:8080/events")
    parser.add_argument("--out", default="/home/billy/X/SentriX/data/raw/proxy_events.csv")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    count = extract_labeled_features(
        events_path=Path(args.events) if args.events else None,
        events_api=args.events_api,
        out_csv=Path(args.out),
        run_id=args.run_id,
        scenario=args.scenario,
        label=args.label,
        rep=args.rep,
        append=args.append,
    )

    print(
        f"Extracted {count} labeled rows to {args.out} "
        f"(run_id={args.run_id}, scenario={args.scenario}, label={args.label}, rep={args.rep})"
    )


if __name__ == "__main__":
    main()
