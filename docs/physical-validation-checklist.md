# Manual physical Reachy Mini validation checklist

**Never run this checklist in CI.** Physical tests must carry the `physical` pytest marker and are
skipped unless the operator deliberately sets `BAYMAX_PHYSICAL_TESTS=1`. That variable is only a
test collection gate; it is not supervised confirmation and must not enable application movement.

Before testing:

- [ ] Record official repository commit, release tag, SDK distribution/version, and documentation URLs.
- [ ] Review the current official root `AGENTS.md` and generated app metadata.
- [ ] Implement/review the SDK wrapper using only cited Reachy Mini—not Reachy 2—APIs.
- [ ] Confirm `BAYMAX_MODE=reachy`, `BAYMAX_ROBOT_BACKEND=reachy`, supervised confirmation, and the physical checklist gate.
- [ ] Verify a reachable physical emergency stop, clear workspace, stable power, and an observing operator.
- [ ] Confirm motion starts disabled and configured duration/movement/watchdog limits are conservative.

Supervised validation:

- [ ] Verify supported local/USB connection and timeout behavior.
- [ ] Verify supported private-LAN connection without public/WAN exposure.
- [ ] Verify motor status and official safe-stop registration before movement.
- [ ] Run one minimum-range allow-listed expression and reject invalid/out-of-range commands.
- [ ] Cancel during motion; trigger watchdog, model timeout, Ollama loss, and process shutdown.
- [ ] Confirm safe-stop occurs before shutdown and emergencies cause no movement.
- [ ] Verify microphone/speaker health, bounded capture, playback cancellation, and audio deletion.
- [ ] Verify official logs, restart, update, rollback, shutdown, and app lifecycle procedures.

Record results as physical evidence. A successful SDK import or fake test is never sufficient.
