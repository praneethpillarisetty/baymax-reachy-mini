# Simulator and fake validation

Run the offline validation from the repository root:

```console
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m mypy src/baymax
python -m baymax.cli --once "hello"
python -m baymax.cli robot-status
python -m baymax.cli safe-stop
```

The built-in simulator is deterministic and hardware-independent; it is not the official Reachy
Mini graphical simulator. `tests/integration/test_simulator_end_to_end.py` covers fake microphone →
safety → deterministic model → fake speaker plus cancellation. It also verifies that emergencies
bypass the model and produce no robot expression. `tests/unit/test_reachy_sdk_boundary.py` uses only
a Baymax-owned fake wrapper to validate version rejection, connection timeouts, allow-listed and
bounded commands, watchdog safe-stop, and cleanup.

Mock HTTP tests validate Ollama request/response, timeout, retry, and cancellation without a daemon.
Model/UI suites validate registry cards, transactional activation/rollback, installation states,
refresh persistence, failure recovery, and localhost-only binding. Voice tests use synthetic WAV
files and assert temporary inputs/outputs are removed after success and failure.

Passing these checks establishes offline control-plane behavior only. It does not establish SDK,
Raspberry Pi, audio-hardware, network-security, or physical-motion compatibility.
