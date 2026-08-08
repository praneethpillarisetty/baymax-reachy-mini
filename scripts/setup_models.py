from __future__ import annotations

import argparse

from baymax.cli import main

parser = argparse.ArgumentParser(description="Plan or confirm Baymax local model setup")
parser.add_argument("--target", choices=("auto", "laptop", "raspberry-pi"), default="auto")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--interactive", action="store_true")
args = parser.parse_args()
command = ["models", "install", "--target", args.target]
if args.dry_run:
    command.append("--dry-run")
elif args.interactive:
    answer = input("Review sources/licenses above, then type INSTALL to continue: ")
    if answer != "INSTALL":
        raise SystemExit("Installation cancelled; no changes made.")
    command.append("--yes")
else:
    raise SystemExit("Use --dry-run or --interactive; hidden downloads are forbidden.")
raise SystemExit(main(command))
