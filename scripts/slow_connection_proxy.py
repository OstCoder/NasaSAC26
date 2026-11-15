#!/usr/bin/env python3
"""Slow-connection simulator: a throttling TCP reverse proxy in front of the API.

The production split serves the frontend from a CDN and the API from Render, so
the client<->API link is the variable one. This proxy reproduces a constrained
link (defaults are roughly "slow 3G": ~400 kbit/s downstream, ~600 ms RTT) so the
application can be exercised end to end under it.

It sits between the Vite dev server and FastAPI:

    backend (8002)  <-  proxy (8003)  <-  `LUNANAV_API=http://127.0.0.1:8003` vite (5174)

Page assets still come from Vite directly, and backend->JPL/Moon Trek fetches
happen server-side, so only the API round trips are throttled. That is the point:
it measures how the app behaves when the API link is slow, not the CDN.

Example:

    python scripts/slow_connection_proxy.py --listen 127.0.0.1:8003 --target 127.0.0.1:8002
    cd frontend && LUNANAV_API=http://127.0.0.1:8003 npm run dev

Each finished connection prints one summary line with the bytes moved and the
effective rate, so the numbers in docs/PHASE6_PERFORMANCE.md can be re-derived.
"""

from __future__ import annotations

import argparse
import asyncio
import signal

CHUNK = 1460  # one MTU-sized step, like a real packet stream


async def pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
               bps: float, latency: float) -> tuple[int, float]:
    """Copy one direction at `bps` bytes/s, adding `latency` s before the first byte."""
    moved = 0
    started: float | None = None
    try:
        while True:
            data = await reader.read(CHUNK)
            if not data:
                break
            if started is None:
                started = asyncio.get_running_loop().time()
                await asyncio.sleep(latency)
            moved += len(data)
            writer.write(data)
            await writer.drain()
            await asyncio.sleep(len(data) / bps)  # pace: one chunk per chunk/bps
    except (ConnectionError, TimeoutError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass
    elapsed = asyncio.get_running_loop().time() - started if started else 0.0
    return moved, elapsed


async def handle(client: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                 target_host: str, target_port: int, bps: float, latency: float,
                 counter: list[int]) -> None:
    counter[0] += 1
    n = counter[0]
    try:
        target_reader, target_writer = await asyncio.open_connection(target_host, target_port)
    except OSError:
        client_writer.close()
        return
    up, down = await asyncio.gather(
        pump(client, target_writer, bps, latency),          # request body (small)
        pump(target_reader, client_writer, bps, latency),   # response (the big direction)
    )
    up_b, up_s = up
    down_b, down_s = down
    rate = down_b / down_s / 1000.0 if down_s > 0 else 0.0
    print(f"conn {n}: up {up_b} B / {up_s:.2f}s · down {down_b} B / {down_s:.2f}s "
          f"= {rate:.1f} kB/s (target {bps / 1000.0:.1f})", flush=True)


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--listen", default="127.0.0.1:8003")
    ap.add_argument("--target", default="127.0.0.1:8002")
    ap.add_argument("--rate-kbps", type=float, default=400.0,
                    help="downstream+upstream throughput in kbit/s (default 400)")
    ap.add_argument("--latency-ms", type=float, default=300.0,
                    help="one-way added delay before the first byte, ms (default 300)")
    args = ap.parse_args()

    listen_host, listen_port = args.listen.rsplit(":", 1)
    target_host, target_port = args.target.rsplit(":", 1)
    bps = args.rate_kbps * 1000.0 / 8.0
    latency = args.latency_ms / 1000.0
    counter = [0]

    async def conn(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        await handle(r, w, target_host, int(target_port), bps, latency, counter)

    server = await asyncio.start_server(conn, listen_host, int(listen_port))
    print(f"throttling proxy {args.listen} -> {args.target} at "
          f"{args.rate_kbps:.0f} kbit/s, +{args.latency_ms:.0f} ms one-way", flush=True)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, server.close)
        except NotImplementedError:
            pass
    async with server:
        try:
            await server.serve_forever()
        except asyncio.CancelledError:  # SIGINT/SIGTERM
            pass


if __name__ == "__main__":
    asyncio.run(main())
