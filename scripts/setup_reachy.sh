#!/usr/bin/env sh
set -eu
[ "$(uname -s)" = Linux ] || { echo 'Reachy target requires Linux' >&2; exit 2; }
case "$(uname -m)" in aarch64|arm64) ;; *) echo 'Reachy Wireless target requires ARM64' >&2; exit 2;; esac
python3 -c 'import sys; assert (3,10) <= sys.version_info < (3,14), "Python 3.10-3.13 required by shared core"'
echo 'Shared-core prerequisites passed. Install/deploy the SDK app only with the current official Reachy Mini workflow.'
