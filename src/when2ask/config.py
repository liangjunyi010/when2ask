"""Local configuration. Credential values never participate in repr or reports."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = next((p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()), Path.cwd())


def read_env(path: Path) -> dict[str, str]:
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
            if match:
                value = match[2].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                else:
                    value = value.split(" #", 1)[0].rstrip()
                values[match[1]] = value
    return values
