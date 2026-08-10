# Raspberry Pi / CM4 deployment

Use `deploy/linux-arm64` only as a dry-run planning package. A deployment preflight must report target, `uname -m`, Python, free storage, SDK/daemon state, model compatibility, planned URLs/destinations, rollback, and a redacted report. It must require explicit confirmation and must not assume SSH credentials, install laptop models, enable LAN access, or move the robot. Current CM4 voice candidates are blocked in the manifest pending real-hardware verification.
