from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class TOMLDecodeError(ValueError):
    pass


def load_toml(path: Path) -> dict[str, Any]:
    """Parse the conservative TOML subset used by Baymax configuration/profile files.

    Keeping this tiny parser in core preserves Python 3.10 without importing an optional package.
    Arrays, dates, multiline strings and dotted keys are deliberately rejected.
    """
    root: dict[str, Any] = {}
    current = root
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip()
            if not name or "." in name:
                raise TOMLDecodeError(f"unsupported table at line {number}")
            current = root.setdefault(name, {})
            if not isinstance(current, dict):
                raise TOMLDecodeError(f"duplicate table at line {number}")
            continue
        if "=" not in line:
            raise TOMLDecodeError(f"expected key/value at line {number}")
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if not key.replace("_", "").isalnum() or key in current:
            raise TOMLDecodeError(f"invalid or duplicate key at line {number}")
        if raw_value in {"true", "false"}:
            value: Any = raw_value == "true"
        else:
            try:
                value = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError) as exc:
                raise TOMLDecodeError(f"unsupported value at line {number}") from exc
        if not isinstance(value, (str, int, float, bool)):
            raise TOMLDecodeError(f"unsupported value type at line {number}")
        current[key] = value
    return root
