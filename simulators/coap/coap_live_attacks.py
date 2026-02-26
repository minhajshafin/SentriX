from __future__ import annotations

import argparse
import asyncio

from aiocoap import Context, Message, GET


async def request_flood(protocol: Context, host: str, port: int, count: int) -> None:
    uri = f"coap://{host}:{port}/.well-known/core"
    tasks = []
    for _ in range(count):
        request = Message(code=GET, uri=uri)
        tasks.append(protocol.request(request).response)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = sum(1 for result in results if isinstance(result, Exception))
    print(f"request_flood completed: sent={count}, errors={errors}")


async def malformed_payload_burst(protocol: Context, host: str, port: int, count: int) -> None:
    uri = f"coap://{host}:{port}/sensors/temp"
    bad_payload = b"\x00\xff\x00\xff" * 128

    for idx in range(count):
        request = Message(code=GET, uri=uri, payload=bad_payload)
        try:
            response = await protocol.request(request).response
            print(f"[{idx}] malformed burst -> {response.code}")
        except Exception as exc:
            print(f"[{idx}] malformed burst -> error: {exc}")


async def run(args: argparse.Namespace) -> None:
    protocol = await Context.create_client_context()
    await asyncio.sleep(1)

    if args.attack == "request_flood":
        await request_flood(protocol, args.host, args.port, args.count)
    elif args.attack == "malformed_burst":
        await malformed_payload_burst(protocol, args.host, args.port, args.count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CoAP attack-like traffic through SentriX CoAP proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5684)
    parser.add_argument("--attack", choices=["request_flood", "malformed_burst"], default="request_flood")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
