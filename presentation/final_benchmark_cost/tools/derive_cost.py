"""Read immutable Test attempts and derive cache-aware, explicitly estimated USD.

No environment, credentials, model clients or network calls are used.
Unknown usage is an error for this complete dataset, never an invented zero.
"""
from __future__ import annotations
from collections import defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
METHODS = ["llm_noask", "llm_gate", "jev_gate"]
D = Decimal


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def derive():
    prices = json.loads((BASE / "analysis/pricing_assumptions.json").read_text())
    old_summary = json.loads((ROOT / "outputs/three_task_v8/report/summary.json").read_text())
    rows, episodes, inputs = [], [], []
    buckets = defaultdict(list)
    for method in METHODS:
        directories = sorted((ROOT / "outputs/three_task_v8/test_runs").glob("*__" + method))
        assert len(directories) == 12
        for folder in directories:
            ep_path, path = folder / "episode.json", folder / "api_attempts.jsonl"
            ep = json.loads(ep_path.read_text())
            episodes.append({"method": method, "episode_id": folder.name,
                             "group_id": ep["group_id"], "success": ep["evaluation"]["task_success"],
                             "burden": ep["evaluation"]["clarification_burden"]})
            for src in [ep_path, path]:
                inputs.append({"path": str(src.relative_to(ROOT)), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
            for line_no, line in enumerate(path.read_text().splitlines(), 1):
                a = json.loads(line)
                assert a["status"] == "ok", a["status"]
                usage = a["response"]["usage"]
                inp, out = a["input_tokens"], a["output_tokens"]
                assert isinstance(inp, int) and isinstance(out, int)
                assert a["latency_ms"] is not None
                assert a["episode_id"] == folder.name
                row = dict(method=method, episode_id=folder.name, round=a["round"],
                           backend=a["backend"], stage=a["stage"], attempt=a["attempt"], status=a["status"],
                           configured_model=a["configured_model"], returned_model=a["returned_model"],
                           input_tokens=inp, output_tokens=out, cache_hit_tokens=None,
                           cache_miss_tokens=None, request_created_utc=None, price_bucket=None,
                           latency_ms=a["latency_ms"], estimated_usd=None,
                           hypothetical_all_peak_usd=None,
                           evidence=f"{path.relative_to(ROOT)}#L{line_no}")
                if a["backend"] == "deepseek":
                    assert a["returned_model"] == prices["deepseek"]["configured_and_returned_model"]
                    hit, miss = usage["prompt_cache_hit_tokens"], usage["prompt_cache_miss_tokens"]
                    assert hit + miss == inp == usage["prompt_tokens"]
                    assert out == usage["completion_tokens"]
                    timestamp = datetime.fromtimestamp(a["response"]["created"], timezone.utc)
                    # This dataset never intersects peak clock hours: no holiday assumption.
                    assert not any(start <= timestamp.hour < end for start, end in prices["deepseek"]["peak_hours_utc"])
                    row.update(cache_hit_tokens=hit, cache_miss_tokens=miss,
                               request_created_utc=timestamp.isoformat(), price_bucket="off_peak")
                    def ds_cost(rates):
                        return (D(hit)*D(str(rates["cache_hit_input"])) + D(miss)*D(str(rates["cache_miss_input"]))
                                + D(out)*D(str(rates["output"]))) / D(1_000_000)
                    value = ds_cost(prices["deepseek"]["off_peak_usd_per_million"])
                    peak = ds_cost(prices["deepseek"]["peak_usd_per_million"])
                else:
                    assert a["backend"] == "jev" and a["returned_model"] == prices["jev"]["returned_model"]
                    assert usage["input_tokens"] == inp and usage["output_tokens"] == out
                    rates = prices["jev"]["usd_per_million"]
                    value = (D(inp)*D(str(rates["input"])) + D(out)*D(str(rates["output"]))) / D(1_000_000)
                    peak = value
                    row["price_bucket"] = "standard"
                row.update(estimated_usd=float(value), hypothetical_all_peak_usd=float(peak))
                rows.append(row)
                buckets[(method, a["backend"], a["stage"])].append(row)
    assert len(rows) == 262 and len(episodes) == 36
    methods = []
    for method, previous in zip(METHODS, old_summary["methods"]):
        eps = [e for e in episodes if e["method"] == method]
        attempts = [r for r in rows if r["method"] == method]
        ds = [r for r in attempts if r["backend"] == "deepseek"]
        jev = [r for r in attempts if r["backend"] == "jev"]
        usd = lambda records, key="estimated_usd": float(sum((D(str(r[key])) for r in records), D(0)))
        item = dict(method=method, scored_episodes=len(eps), independent_groups=len({e["group_id"] for e in eps}),
                    successes=sum(e["success"] for e in eps), mean_burden=sum(e["burden"] for e in eps)/len(eps),
                    api_attempts=len(attempts), api_latency_s=sum(r["latency_ms"] for r in attempts)/1000,
                    deepseek_input_tokens=sum(r["input_tokens"] for r in ds),
                    deepseek_cache_hit_tokens=sum(r["cache_hit_tokens"] for r in ds),
                    deepseek_cache_miss_tokens=sum(r["cache_miss_tokens"] for r in ds),
                    deepseek_output_tokens=sum(r["output_tokens"] for r in ds),
                    jev_input_tokens=sum(r["input_tokens"] for r in jev) if jev else None,
                    jev_output_tokens=sum(r["output_tokens"] for r in jev) if jev else None,
                    estimated_deepseek_usd=usd(ds), estimated_jev_usd=usd(jev) if jev else None,
                    estimated_total_usd=usd(attempts), hypothetical_all_peak_usd=usd(attempts,"hypothetical_all_peak_usd"))
        assert previous["method"] == method and previous["successes"] == item["successes"]
        assert abs(previous["api_latency_s"] - item["api_latency_s"]) < 1e-8
        methods.append(item)
    stages = []
    for (method, backend, stage), records in sorted(buckets.items()):
        stages.append(dict(method=method, backend=backend, stage=stage, attempts=len(records),
                           input_tokens=sum(r["input_tokens"] for r in records),
                           output_tokens=sum(r["output_tokens"] for r in records),
                           total_latency_ms=sum(r["latency_ms"] for r in records),
                           mean_latency_ms=sum(r["latency_ms"] for r in records)/len(records),
                           estimated_usd=float(sum((D(str(r["estimated_usd"])) for r in records),D(0)))))
    gates = [s for s in stages if s["stage"] == "gate"]
    llm = next(s for s in gates if s["method"] == "llm_gate")
    jev = next(s for s in gates if s["method"] == "jev_gate")
    comparisons = dict(gate_mean_latency_ratio_llm_over_jev=llm["mean_latency_ms"]/jev["mean_latency_ms"],
                       total_api_latency_reduction_fraction=1-methods[2]["api_latency_s"]/methods[1]["api_latency_s"],
                       estimated_total_usd_reduction_fraction=1-methods[2]["estimated_total_usd"]/methods[1]["estimated_total_usd"],
                       estimated_gate_usd_reduction_fraction=1-jev["estimated_usd"]/llm["estimated_usd"])
    created = sorted(r["request_created_utc"] for r in rows if r["request_created_utc"])
    report = dict(schema_version="when2ask.presentation_derived_cost.v1", pricing_assumptions=prices,
                  request_time_range_utc=[created[0],created[-1]], methods=methods, stages=stages,
                  comparisons=comparisons, input_files=inputs, new_model_api_calls=0,
                  claim_boundary="Observed latency plus retrospective current-price estimates, not invoices, speed guarantees or significance claims.")
    outdir = BASE / "analysis"
    (outdir / "cost_report.json").write_text(json.dumps(report, indent=2)+"\n")
    write_csv(outdir / "attempt_costs.csv",rows)
    write_csv(outdir / "methods.csv",methods)
    write_csv(outdir / "stages.csv",stages)
    print(json.dumps({"methods":methods,"gates":gates,"comparisons":comparisons},indent=2))
    return report


if __name__ == "__main__":
    derive()
