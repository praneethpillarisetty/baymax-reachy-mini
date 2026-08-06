# First physical robot checklist

- [ ] Official SDK/app revision, instructions, limits and emergency stop recorded.
- [ ] Stable table, clearance, correct assembly, cables and motors inspected.
- [ ] Supervised, short session; no unattended operation or autonomous walking.
- [ ] Low speed and conservative head/antenna/body ranges independently reviewed.
- [ ] Safe volume and local network firewall confirmed.
- [ ] Simulator, `baymax doctor`, configuration, model availability, cancellation and shutdown pass.
- [ ] Physical stop/power-off rehearsed before motor enable.
- [ ] `ReachyMiniRobot.sdk_available()` is true and the exact installed distribution/version is recorded.
- [ ] Official generated app files are present under `deploy/reachy-mini/` and reviewed against the current root `AGENTS.md`.
- [ ] `baymax robot-smoke --confirm-supervised` performs a verified connection test rather than returning the integration gate.
- [ ] Stop on collision, heat, noise, strain, unexpected motion or daemon loss.

Passing this document does not establish medical-device or physical-hardware validation.
