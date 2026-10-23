"""Local configuration. Credential values never participate in repr or reports."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class Config:
    deepseek_key: str = field(default="", repr=False)
    typesafe_key: str = field(default="", repr=False)
    deepseek_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    typesafe_url: str = "https://api.typesafe.ai"
    jev_model: str = "jev-latest"
    threshold: float = .5
    timeout_s: float = 40
    max_retries: int = 1
    max_tokens: int = 500

    @classmethod
    def load(cls, root: Path = ROOT):
        env = read_env(root / ".env")
        def get(name, default=""):
            return os.environ.get(name, env.get(name, default))
        return cls(get("DEEPSEEK_API_KEY"), get("TYPESAFE_API_KEY"),
                   get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                   get("DEEPSEEK_MODEL", "deepseek-flash"),
                   get("TYPESAFE_BASE_URL", "https://api.typesafe.ai"),
                   get("JEV_MODEL", "jev-latest"), float(get("JEV_THRESHOLD", ".5")))

    def sanitize(self, value):
        text = json.dumps(value, ensure_ascii=False, default=str)
        for secret in (self.deepseek_key, self.typesafe_key):
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"(?:sk-[A-Za-z0-9_-]{16,}|apikey_[A-Za-z0-9_]{20,})", "[REDACTED]", text)
        return json.loads(text)

    def public_config(self):
        return dict(deepseek_model=self.deepseek_model, jev_model=self.jev_model,
                    jev_threshold=self.threshold, timeout_s=self.timeout_s,
                    max_retries=self.max_retries, max_tokens=self.max_tokens,
                    thinking="disabled", response_format="json_object")
