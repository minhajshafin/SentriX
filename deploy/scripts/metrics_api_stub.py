from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os


def read_metrics_snapshot(path: str) -> dict:
    default = {
        "mqtt_msgs": 0,
        "coap_msgs": 0,
        "detections": 0,
        "latency_ms_p95": 0,
    }

    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            for key, value in default.items():
                data.setdefault(key, value)
            return data
    except (OSError, json.JSONDecodeError):
        return default


METRICS_PATH = os.getenv("SENTRIX_METRICS_PATH", "/tmp/sentrix_metrics.json")
EVENTS_PATH = os.getenv("SENTRIX_EVENTS_PATH", "/tmp/sentrix_events.log")


def read_event_tail(path: str, limit: int = 100) -> list[dict]:
    if not os.path.exists(path):
        return []

    events: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8") as fp:
            for raw_line in fp:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []

    return events[-limit:]


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "metrics-api-stub",
                    "metrics_path": METRICS_PATH,
                    "events_path": EVENTS_PATH,
                }
            )
            return

        if self.path == "/metrics":
            self._send_json(read_metrics_snapshot(METRICS_PATH))
            return

        if self.path == "/events":
            self._send_json({"events": read_event_tail(EVENTS_PATH, limit=120)})
            return

        self._send_json({"error": "not_found"}, status=404)


def main():
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), Handler)
    print(f"[metrics-api-stub] serving on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
