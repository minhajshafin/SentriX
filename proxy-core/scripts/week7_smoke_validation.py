#!/usr/bin/env python3

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROXY_ROOT = ROOT / "proxy-core"
DEFAULT_PROXY = PROXY_ROOT / "build-onnx" / "sentrix_proxy"
DEFAULT_MODEL = ROOT / "ml-pipeline" / "models" / "lightgbm_full.onnx"
DEFAULT_ONNX_LIB = PROXY_ROOT / "third_party" / "onnxruntime" / "lib"
DEFAULT_SUMMARY = ROOT / "ml-pipeline" / "reports" / "week7_proxy_smoke_validation.json"
DEFAULT_ARTIFACT_DIR = ROOT / "ml-pipeline" / "reports" / "week7_proxy_smoke"


def require_file(path: Path, description: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing {description}: {path}")
    return path


class TcpEchoServer:
    def __init__(self, host: str, port: int) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((host, port))
        self._sock.listen(5)
        self._sock.settimeout(0.2)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            try:
                conn, _addr = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break

            thread = threading.Thread(target=self._handle, args=(conn,), daemon=True)
            thread.start()

    def _handle(self, conn: socket.socket) -> None:
        with conn:
            while self._running:
                try:
                    data = conn.recv(4096)
                except OSError:
                    return
                if not data:
                    return
                try:
                    conn.sendall(data)
                except OSError:
                    return

    def stop(self) -> None:
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass
        self._thread.join(timeout=1.0)


class UdpEchoServer:
    def __init__(self, host: str, port: int) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, port))
        self._sock.settimeout(0.2)
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(2048)
            except TimeoutError:
                continue
            except OSError:
                break
            try:
                self._sock.sendto(data, addr)
            except OSError:
                return

    def stop(self) -> None:
        self._running = False
        try:
            self._sock.close()
        except OSError:
            pass
        self._thread.join(timeout=1.0)


def mqtt_connect_packet(client_id: str) -> bytes:
    client_id_bytes = client_id.encode("utf-8")
    variable_header = b"\x00\x04MQTT\x04\x02\x00<"
    payload = len(client_id_bytes).to_bytes(2, "big") + client_id_bytes
    remaining_length = len(variable_header) + len(payload)
    return bytes([0x10, remaining_length]) + variable_header + payload


def coap_get_packet(message_id: int, path: str) -> bytes:
    segments = [segment for segment in path.split("/") if segment]
    packet = bytearray([0x40, 0x01, (message_id >> 8) & 0xFF, message_id & 0xFF])
    previous_option = 0
    for segment in segments:
        option_number = 11
        delta = option_number - previous_option
        value = segment.encode("utf-8")
        if delta > 12 or len(value) > 12:
            raise ValueError("path segment too large for simple smoke packet")
        packet.append((delta << 4) | len(value))
        packet.extend(value)
        previous_option = option_number
    return bytes(packet)


def wait_for_tcp_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise TimeoutError(f"port {host}:{port} did not become ready")


def wait_for_debug_entries(path: Path, timeout: float = 5.0) -> list[dict]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.stat().st_size > 0:
            with path.open("r", encoding="utf-8") as handle:
                rows = [json.loads(line) for line in handle if line.strip()]
            if rows:
                return rows
        time.sleep(0.1)
    raise TimeoutError(f"debug export was not written to {path}")


def main() -> int:
    proxy_bin = require_file(Path(os.environ.get("SENTRIX_PROXY_BIN", DEFAULT_PROXY)), "proxy binary")
    model_path = require_file(Path(os.environ.get("SENTRIX_ONNX_MODEL_PATH", DEFAULT_MODEL)), "ONNX model")
    summary_output_path = Path(os.environ.get("SENTRIX_WEEK7_SUMMARY_PATH", DEFAULT_SUMMARY))
    artifact_dir = Path(os.environ.get("SENTRIX_WEEK7_ARTIFACT_DIR", DEFAULT_ARTIFACT_DIR))

    onnx_lib_dir = Path(os.environ.get("SENTRIX_ONNX_LIB_DIR", DEFAULT_ONNX_LIB))
    with tempfile.TemporaryDirectory(prefix="sentrix-week7-") as temp_dir:
        temp = Path(temp_dir)
        metrics_path = temp / "metrics.json"
        events_path = temp / "events.jsonl"
        debug_path = temp / "features.jsonl"
        proxy_log_path = temp / "proxy.log"

        mqtt_backend = TcpEchoServer("127.0.0.1", 2883)
        coap_backend = UdpEchoServer("127.0.0.1", 6683)
        mqtt_backend.start()
        coap_backend.start()

        env = os.environ.copy()
        env.update(
            {
                "SENTRIX_MQTT_BROKER_HOST": "127.0.0.1",
                "SENTRIX_MQTT_BROKER_PORT": "2883",
                "SENTRIX_MQTT_PROXY_PORT": "2884",
                "SENTRIX_COAP_BACKEND_HOST": "127.0.0.1",
                "SENTRIX_COAP_BACKEND_PORT": "6683",
                "SENTRIX_COAP_PROXY_PORT": "6684",
                "SENTRIX_METRICS_PATH": str(metrics_path),
                "SENTRIX_EVENTS_PATH": str(events_path),
                "SENTRIX_FEATURE_DEBUG_PATH": str(debug_path),
                "SENTRIX_ONNX_MODEL_PATH": str(model_path),
                "SENTRIX_ENABLE_BEHAVIORAL_WINDOWS": "1",
            }
        )
        if onnx_lib_dir.exists():
            env["LD_LIBRARY_PATH"] = (
                f"{onnx_lib_dir}:{env['LD_LIBRARY_PATH']}" if env.get("LD_LIBRARY_PATH") else str(onnx_lib_dir)
            )

        with proxy_log_path.open("w", encoding="utf-8") as proxy_log:
            proxy = subprocess.Popen(
                [str(proxy_bin)],
                cwd=str(PROXY_ROOT),
                env=env,
                stdout=proxy_log,
                stderr=subprocess.STDOUT,
            )

            try:
                wait_for_tcp_port("127.0.0.1", 2884)
                time.sleep(0.5)

                with socket.create_connection(("127.0.0.1", 2884), timeout=2.0) as sock:
                    sock.sendall(mqtt_connect_packet("week7-test"))
                    echo = sock.recv(64)
                    if not echo:
                        raise RuntimeError("mqtt echo was empty")

                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2.0)
                    sock.sendto(coap_get_packet(0x1234, ".well-known/core"), ("127.0.0.1", 6684))
                    response, _addr = sock.recvfrom(2048)
                    if not response:
                        raise RuntimeError("coap echo was empty")

                debug_rows = wait_for_debug_entries(debug_path)
                time.sleep(1.2)
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

                protocols = sorted({row["protocol"] for row in debug_rows})
                if protocols != ["coap", "mqtt"]:
                    raise RuntimeError(f"unexpected protocols in debug export: {protocols}")
                if metrics.get("mqtt_msgs", 0) < 1 or metrics.get("coap_msgs", 0) < 1:
                    raise RuntimeError(f"unexpected metrics snapshot: {metrics}")

                artifact_dir.mkdir(parents=True, exist_ok=True)
                persisted_metrics = artifact_dir / "metrics.json"
                persisted_events = artifact_dir / "events.jsonl"
                persisted_debug = artifact_dir / "features.jsonl"
                persisted_proxy_log = artifact_dir / "proxy.log"
                shutil.copy2(metrics_path, persisted_metrics)
                shutil.copy2(events_path, persisted_events)
                shutil.copy2(debug_path, persisted_debug)
                shutil.copy2(proxy_log_path, persisted_proxy_log)

                summary = {
                    "status": "PASS",
                    "proxy_binary": str(proxy_bin),
                    "onnx_model": str(model_path),
                    "protocols_seen": protocols,
                    "metrics": metrics,
                    "debug_rows": len(debug_rows),
                    "artifact_dir": str(artifact_dir),
                    "metrics_path": str(persisted_metrics),
                    "debug_path": str(persisted_debug),
                    "events_path": str(persisted_events),
                    "proxy_log_path": str(persisted_proxy_log),
                }
                summary_output_path.parent.mkdir(parents=True, exist_ok=True)
                summary_output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(json.dumps(summary, indent=2))
                return 0
            finally:
                if proxy.poll() is None:
                    proxy.send_signal(signal.SIGTERM)
                    try:
                        proxy.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proxy.kill()
                        proxy.wait(timeout=5)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"week7 smoke validation failed: {exc}", file=sys.stderr)
        sys.exit(1)