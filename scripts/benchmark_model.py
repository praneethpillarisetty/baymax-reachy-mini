#!/usr/bin/env python3
import argparse
import json
import os
import resource
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--label", required=True)
p.add_argument("--tokens", type=int)
a = p.parse_args()
path = Path(a.model)
started = time.perf_counter()
before = resource.getrusage(resource.RUSAGE_SELF)
size = path.stat().st_size if path.exists() else None
elapsed = time.perf_counter() - started
after = resource.getrusage(resource.RUSAGE_SELF)
print(
    json.dumps(
        {
            "label": a.label,
            "model_file_bytes": size,
            "startup_seconds": elapsed,
            "peak_memory_kb": after.ru_maxrss,
            "cpu_user_seconds": after.ru_utime - before.ru_utime,
            "cpu_system_seconds": after.ru_stime - before.ru_stime,
            "response_latency_seconds": None,
            "tokens_per_second": None,
            "gpu_usage": None,
            "daemon_responsive": None,
            "audio_responsive": None,
            "battery_impact": None,
            "pid": os.getpid(),
        },
        indent=2,
    )
)
