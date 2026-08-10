# Current development phase

**Phase 7 — real local voice setup and Reachy Mini deployment preparation.**

Implemented and fake-server tested: allow-listed manifest parsing, HTTPS downloads, redirect support through urllib, bounded retries/timeouts, Range resume with 200 fallback, partial files, persisted progress, disk/size limits, cancellation, duplicate protection, checksum verification when available, atomic rename, and visible UI operation JSON. The simulator, mocks, safety boundary, and local UI work without Reachy hardware.

Not verified here: live Hugging Face downloads, real Ollama, host microphone/speaker, Piper binaries, official SDK connection modes, Lite USB/daemon detection, Wireless network/daemon identity, ARM64 Piper, CM4 STT performance, and physical movement. Those stay fail-closed.
