"""Fail without printing credential values if secrets enter files about to be published."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from when2ask.config import Config, ROOT


def main():
    config = Config.load()
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    failures = []
    pattern = re.compile(rb"(?:sk-[A-Za-z0-9_-]{24,}|apikey_[A-Za-z0-9_]{40,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
    for name in filter(None, paths.decode().split("\0")):
        path = ROOT / name
        if not path.is_file():
            continue
        content = path.read_bytes()
        exact = any(secret and secret.encode() in content for secret in (config.deepseek_key, config.typesafe_key))
        if exact or pattern.search(content):
            failures.append(name)
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0
    private = not (ROOT / ".env").exists() or (ROOT / ".env").stat().st_mode & 0o777 == 0o600
    if failures or not ignored or not private:
        print("Secret scan FAILED; affected paths:", failures, "env_ignored:", ignored, "env_private:", private)
        return 1
    print("Secret scan passed; no credential values found; .env ignored and private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
