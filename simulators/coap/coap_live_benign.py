from __future__ import annotations

import argparse
import asyncio
import random

from aiocoap import Context, Message, PUT, GET


async def run(args: argparse.Namespace) -> None:
    protocol = await Context.create_client_context()
    await asyncio.sleep(1)

    base = f"coap://{args.host}:{args.port}"
    resources = [
        ("/health", GET, None),
        ("/sensors/temp", GET, None),
        ("/sensors/temp", PUT, "24.3"),
        ("/actuators/valve", PUT, "open"),
    ]

    for index in range(args.count):
        path, method, payload = random.choice(resources)

        request = Message(
            code=method,
            uri=f"{base}{path}",
            payload=(payload or "").encode("utf-8"),
        )

        try:
            response = await protocol.request(request).response
            print(f"[{index}] {method} {path} -> {response.code}")
        except Exception as exc:
            print(f"[{index}] {method} {path} -> error: {exc}")

        await asyncio.sleep(max(args.interval_ms, 0) / 1000.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benign CoAP traffic through SentriX CoAP proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5684)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--interval-ms", type=int, default=150)
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
