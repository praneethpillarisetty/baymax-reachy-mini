# Reachy Mini Wireless installation gate

No Windows executable is deployed to the robot. The intended target is the official generated Reachy Mini app package containing the shared `baymax` core and a Linux ARM64 adapter. `scripts/setup_reachy.sh` checks only platform/Python preconditions; it does not pretend to deploy.

Before filling `deploy/reachy-mini`, verify the official root `AGENTS.md`, package/import/version constraint, supported onboard Python, app generator, entry-point/lifecycle contract, daemon connection method, camera/microphone/speaker APIs, motion limits, Wireless filesystem and deployment/update/log/safe-stop commands. Generate the official template, preserve its metadata, and add dependency injection to `ReachyMiniRobot`. Test first in the official simulator and then supervised hardware. Current status: **not deployed and not physical-hardware-tested**.

On 2026-08-08 both permitted retrieval paths were retried: the documentation tool returned HTTP 401 and direct GitHub/Hugging Face HTTPS returned HTTP 403. The SDK is not installed in the build image. Consequently there is still no verified package version, Python matrix, generator command, daemon command, constructor, media/motion API, app lifecycle, deployment command, filesystem path, or log command to record. `ReachyMiniRobot` can be imported and inspected without connecting, but `connect()` fails closed even if an SDK later appears; replace that gate only in an environment where the official sources and supervised robot are available.

The adapter validates only the local choreography vocabulary (`greeting`, `listening`, `thinking`, `caring`, `concern`, `reminder`, and `neutral`) and cancellation state. It intentionally sends no SDK movement command. This boundary is simulator-tested, not official-simulator-tested or physical-robot-tested.

The setup dashboard reports SDK discovery and the supervised checklist boundary only. It exposes no
movement control and cannot activate physical mode. Model installation never changes the simulator
robot default.

## Phase 7 connection boundary

Lite and Wireless are separate profiles. The production adapter must import `ReachyMini` from `reachy_mini` and use only connection modes confirmed by the installed official SDK. Auto/local/network discovery must not move hardware; host reachability is only a candidate signal. This checkout still fails closed because official API verification and physical hardware tests were unavailable.
