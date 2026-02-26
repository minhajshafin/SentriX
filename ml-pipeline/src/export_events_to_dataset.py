from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import urlopen


def export_events_from_lines(lines: list[str], out_csv: Path) -> int:
    rows = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        rows.append(
            {
                "timestamp": event.get("ts", ""),
                "protocol": event.get("protocol", ""),
                "direction": event.get("direction", ""),
                "event": event.get("event", ""),
                "bytes": event.get("bytes", 0),
                "detail": event.get("detail", ""),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["timestamp", "protocol", "direction", "event", "bytes", "detail"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def export_events_from_file(events_path: Path, out_csv: Path) -> int:
    if not events_path.exists():
        return 0

    lines = events_path.read_text(encoding="utf-8").splitlines()
    return export_events_from_lines(lines, out_csv)


def export_events_from_api(events_api: str, out_csv: Path) -> int:
    with urlopen(events_api, timeout=10) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))

    events = body.get("events", [])
    lines = [json.dumps(event) for event in events]
    return export_events_from_lines(lines, out_csv)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export SentriX event log JSONL to protocol-tagged CSV")
    parser.add_argument("--events", default="")
    parser.add_argument("--events-api", default="http://localhost:8080/events")
    parser.add_argument("--out", default="/home/billy/X/SentriX/data/raw/proxy_events.csv")
    args = parser.parse_args()

    output = Path(args.out)
    if args.events:
        count = export_events_from_file(Path(args.events), output)
    else:
        count = export_events_from_api(args.events_api, output)
    print(f"Exported {count} rows to {args.out}")


if __name__ == "__main__":
    main()
