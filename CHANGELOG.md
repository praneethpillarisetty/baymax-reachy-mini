# Changelog

## Phase 7 CI packaging repair - 2026-08-11

- Made TOML compatibility imports statically discoverable to PyInstaller and bundled the approved voice manifest in the Windows executable.
- Fixed Ruff `RUF012` and import-order failures without disabling rules.

## 0.3.1 - 2026-08-06

- Restored model adapters and the example profile that were accidentally excluded by an over-broad `models/` ignore rule.
- Added strict Ollama configured-model health checks, Reachy adapter import/smoke gates, and audio artifact diagnostics.
- Re-recorded the blocked official Reachy documentation verification without introducing guessed hardware APIs.

## 0.3.0 - 2026-08-06

- Added checksummed portable profile v2 with secret redaction, v1 migration, explicit personality/safety data, optional reminder import, and registry transfer.
- Expanded doctor diagnostics, LiteRT registry/inspection, generic local command voice adapters, and supervised hardware fail-closed checks.
- Added Windows executable/installer build automation, CI package builds and smoke tests, and measurable benchmark probes.

## 0.2.0 - 2026-08-06

- Migrated to a `src/baymax` shared-core layout with distinct Windows, Linux ARM64, simulator, and gated Reachy targets.
- Added nested CLI diagnostics/config/data/profile commands, versioned safe transfer, LAN protection, Ollama health/retries, TOML LiteRT profiles and platform CI.
- Added Windows/Linux setup and packaging recipes plus comprehensive platform, model, voice and readiness documentation.

## 0.1.0 - 2026-08-06

- Added simulator-first local companion architecture, safety, structured local tools, SQLite, model/audio/robot adapters, tests, benchmark skeleton, and deployment documentation.
- Physical Reachy Mini and exact LiteRT candidates remain unverified due to source-network restrictions.

## Phase 7 voice download repair - 2026-08-10

- Added an authoritative voice manifest and application-data-only reusable DownloadManager.
- Repaired confirmed browser install requests, visible JSON errors/progress, verification/activation gates, and separate voice controls.
- Documented conservative Laptop, Reachy Lite, Wireless, and CM4 compatibility boundaries.
