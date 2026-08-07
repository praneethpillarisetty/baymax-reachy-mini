# Testing

Run `python -m pytest`, `python -m ruff check .`, `python -m mypy src/baymax`, `baymax --once hello`, and `baymax doctor`. The suite needs no robot, Ollama, LiteRT, audio device or model download. CI repeats core checks on Windows and Linux with Python 3.10–3.13.

`python scripts/benchmark_model.py MODEL --label NAME` emits file size, startup/CPU/memory and explicit nulls for unmeasured response, GPU, daemon, audio and battery values. Replace null only with a documented measurement. See `litert-models.md` for the comparison protocol.
