# Reachy Mini Wireless installation gate

No Windows executable is deployed to the robot. The intended target is the official generated Reachy Mini app package containing the shared `baymax` core and a Linux ARM64 adapter. `scripts/setup_reachy.sh` checks only platform/Python preconditions; it does not pretend to deploy.

Before filling `deploy/reachy-mini`, verify the official root `AGENTS.md`, package/import/version constraint, supported onboard Python, app generator, entry-point/lifecycle contract, daemon connection method, camera/microphone/speaker APIs, motion limits, Wireless filesystem and deployment/update/log/safe-stop commands. Generate the official template, preserve its metadata, and add dependency injection to `ReachyMiniRobot`. Test first in the official simulator and then supervised hardware. Current status: **not deployed and not physical-hardware-tested**.
