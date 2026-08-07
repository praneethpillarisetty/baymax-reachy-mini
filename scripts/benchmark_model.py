#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

if os.name != "nt":
    import resource


def peak_memory_bytes() -> int | None:
    if os.name == "nt":
        return None
    value = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return int(value * (1 if __import__("sys").platform == "darwin" else 1024))


def timed(command: list[str]) -> tuple[float, str]:
    started = time.perf_counter()
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=600)
    return time.perf_counter() - started, completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark an explicitly installed local model")
    parser.add_argument("model", type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--tokens", type=int, help="Generated token count from the selected runtime"
    )
    parser.add_argument("--verified-platform", default="unverified")
    parser.add_argument(
        "--probe", nargs=argparse.REMAINDER, help="Optional runtime probe command; run twice"
    )
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error(f"model file does not exist: {args.model}")
    startup = latency = tokens_per_second = None
    output = ""
    if args.probe:
        startup, _ = timed(args.probe)
        latency, output = timed(args.probe)
        if args.tokens is not None and latency > 0:
            tokens_per_second = args.tokens / latency
    report = {
        "schema_version": 1,
        "label": args.label,
        "verified_platform": args.verified_platform,
        "model_file": str(args.model),
        "model_file_bytes": args.model.stat().st_size,
        "startup_seconds": startup,
        "peak_ram_bytes": peak_memory_bytes(),
        "response_latency_seconds": latency,
        "tokens_generated": args.tokens,
        "tokens_per_second": tokens_per_second,
        "probe_output_characters": len(output),
        "cpu_usage": None,
        "gpu_usage": None,
        "daemon_responsive": None,
        "audio_responsive": None,
        "battery_impact": None,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
