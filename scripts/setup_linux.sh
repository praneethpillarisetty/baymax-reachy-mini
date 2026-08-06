#!/usr/bin/env sh
set -eu
python3 -c 'import sys; assert (3,10) <= sys.version_info < (3,14), "Python 3.10-3.13 required"'
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
