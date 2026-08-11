# Documentation changelog

## Phase 7 — 2026-08-10

Added the authoritative voice manifest, reusable resumable DownloadManager, corrected browser confirmation/request/progress/error flow, separate STT/TTS controls, application-data destinations, and explicit laptop/Lite/Wireless compatibility boundaries. Hardware and live large-model downloads remain unverified in this environment.

Fixed the Phase 7 CI follow-up by annotating immutable class metadata for Ruff, sorting test imports, making TOML compatibility imports statically discoverable, and bundling the voice manifest in the Windows executable.
## Unreleased

- Fixed real voice-model progress by removing the conflicting `progress.json` path
  and mapping both approved manifest IDs to their UI components.
- Added truthful worker startup/duplicate protection, persisted background errors,
  cancellation/resume behavior, URL/content preflight, `/api/voice/debug`, live UI
  controls, and the `baymax voice-model` diagnostic/install/verify commands.
