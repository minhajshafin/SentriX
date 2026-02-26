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
                }
            )
            return

        if self.path == "/metrics":
            self._send_json(read_metrics_snapshot(METRICS_PATH))
            return

        self._send_json({"error": "not_found"}, status=404)


def main():
    host, port = "0.0.0.0", 8080
    server = HTTPServer((host, port), Handler)
    print(f"[metrics-api-stub] serving on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
