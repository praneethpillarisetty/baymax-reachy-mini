import argparse
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("path", type=Path)
parser.add_argument("--sha256")
args = parser.parse_args()
if not args.path.is_file():
    parser.error(f"file does not exist: {args.path}")
digest = hashlib.sha256(args.path.read_bytes()).hexdigest()
if args.sha256 and digest.lower() != args.sha256.lower():
    parser.error("SHA-256 mismatch")
print(f"{args.path}: {args.path.stat().st_size} bytes, sha256={digest}")
