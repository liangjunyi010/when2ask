"""Offline diagnostics by default; authenticated requests require explicit live mode."""
from __future__ import annotations

import importlib.metadata
import json
import stat
from pathlib import Path

from .accounting import Audit, SessionLedger
from .api import DeepSeekClient, JevClient, SchemaError
from .config import Config, ROOT


def doctor(live=False, session_dir=None):
    config = Config.load()
    envfile = ROOT / ".env"
    report = dict(live=live, credentials=dict(deepseek=bool(config.deepseek_key), jev=bool(config.typesafe_key)),
                  env_mode=oct(stat.S_IMODE(envfile.stat().st_mode)) if envfile.exists() else None,
                  configuration=config.public_config(),
                  packages={k: importlib.metadata.version(k) for k in ("pybullet", "numpy", "pillow", "pytest")})
    if not live:
        print(json.dumps(report, indent=2))
        return report
    directory = Path(session_dir or ROOT / "result/phase2_live")
    ledger = SessionLedger(directory)
    audit = Audit("api_smoke", config, ledger, directory / "api_smoke_attempts.jsonl", limit=200)
    clients = dict(deepseek=DeepSeekClient(config, audit), jev=JevClient(config, audit))
    results = {}
    for name, client in clients.items():
        result = {}
        try:
            result["models"] = client.models()
        except Exception as exc:
            result["models_error"] = config.sanitize(str(exc))
        try:
            if name == "deepseek":
                def validate(value):
                    if value != {"ok": True}:
                        raise SchemaError('Expected JSON {"ok":true}')
                    return value
                value = client.json('Return only JSON. Example: {"ok":true}.',
                                     {"request": "Return ok=true in JSON."}, stage="smoke",
                                     validator=validate, max_tokens=64)
            else:
                value = client.noul({"instruction": "Put one block in the box.",
                                     "observation": "Green and yellow blocks are available.",
                                     "history": "No block preference has been disclosed."},
                                    "Does missing user preference information prevent choosing a block now?",
                                    stage="smoke")
            row = audit.records[-1]
            result.update(success=True, schema_valid=True, value=value,
                          configured_model=row["configured_model"], returned_model=row["returned_model"],
                          input_tokens=row["input_tokens"], output_tokens=row["output_tokens"],
                          usage_present=row["input_tokens"] is not None and row["output_tokens"] is not None,
                          latency_ms=row["latency_ms"])
        except Exception as exc:
            result.update(success=False, error=config.sanitize(str(exc)))
        results[name] = result
    report.update(backends=results, cost=audit.summary(), session=ledger.snapshot())
    report = config.sanitize(report)
    (directory / "api_smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report
