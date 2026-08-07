#!/usr/bin/env sh
set -eu
[ "$(uname -s)" = Linux ] || { echo 'Reachy target requires Linux' >&2; exit 2; }
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Reachy Wireless target requires ARM64' >&2; exit 2;; esac
python3 -c 'import sys; assert (3,10) <= sys.version_info < (3,14), "Python 3.10-3.13 required by shared core"'
echo 'Shared-core prerequisites passed. Install/deploy the SDK app only with the current official Reachy Mini workflow.'
python3 - <<'PY'
from baymax.robot.reachy_mini import ReachyMiniRobot

print(f"Reachy SDK import available: {ReachyMiniRobot.sdk_available()}")
print("No connection was attempted. Physical startup remains fail-closed until official API verification.")
PY
