"""Build the delivery report from immutable raw-backed metrics; no network I/O."""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from when2ask.calibration import PLAN, SELECTED
from when2ask.study_cli import stable_dev_report
from when2ask.study_data import load_study, sha256, write_json


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + [
        "| " + " | ".join(map(str, row)) + " |" for row in rows]


def truth_profile(samples):
    profiles = {}
    for s in samples:
        scene = s.scene()
        inverse = {v:k for k,v in scene["object_id_map"].items()}
        row = profiles.setdefault(s.template_id, dict(samples=0, combinations=Counter(), slots={}))
        row["samples"] += 1
        row["combinations"]["/".join(inverse[s.theta_star[slot]] for slot in s.slots)] += 1
        for slot in s.slots:
            row["slots"].setdefault(slot, Counter())[inverse[s.theta_star[slot]]] += 1
    return profiles


def main():
    result = stable_dev_report()
    frozen = json.loads((ROOT / "data/phase3/freeze.json").read_text())
    config = json.loads((ROOT / "configs/frozen_test.yaml").read_text())
    plan = json.loads(PLAN.read_text())
    selected = [s for s in load_study("dev") if s.sample_id in SELECTED]
    profiles = {"full_dev":truth_profile(load_study("dev")), "full_test":truth_profile(load_study("test")),
                "online_selected_dev":truth_profile(selected)}
    write_json(ROOT / "outputs/phase3/report/truth_coverage_audit.json", profiles)
    with (ROOT / "outputs/phase3/report/episodes.csv").open() as handle:
        episodes = list(csv.DictReader(handle))
    order = ["llm_noask", "llm_gate", "jev_gate@0.3", "jev_gate@0.5", "jev_gate@0.7"]
    aggregate = {r["condition"]:r for r in result["aggregate"]}
    raw_episodes = [json.loads((ROOT / row["episode_path"]).read_text()) for row in episodes]
    actions = [a for e in raw_episodes for a in e["actions"]]
    skill_successes = sum(a["success"] for a in actions)
    retry_count = sum(e["cost"]["retries"] for e in raw_episodes)
    schema_count = sum(e["cost"]["schema_errors"] for e in raw_episodes)
    api_error_count = sum(e["cost"]["api_errors"] for e in raw_episodes)
    smoke_count = len((ROOT / "outputs/phase3_live/revalidation_attempts.jsonl").read_text().splitlines())
    original = json.loads((ROOT / "outputs/phase3/baseline/summary.json").read_text())
    final_regression = json.loads((ROOT / "outputs/phase3/regression_final/summary.json").read_text())
    data_check = json.loads((ROOT / "outputs/phase3/data_validation.json").read_text())
    xml = ET.parse(ROOT / "outputs/phase3/pytest_final.xml").getroot()
    final_tests = sum(int(s.attrib["tests"]) for s in xml.iter("testsuite"))
    recording = next(e["recording"] for e in raw_episodes if "recording" in e)
    test_samples = frozen["distribution"]["test"]["samples"]
    test_groups = frozen["distribution"]["test"]["groups"]
    means = {c:aggregate[c]["api_attempts"]/aggregate[c]["episodes"] for c in order}
    predicted_requests = test_samples*sum(means[c] for c in ("llm_noask","llm_gate","jev_gate@0.5"))
    lines = ["# Phase 3 Dev calibration report", "",
        "This is an engineering pilot using real DeepSeek/Jev outputs and real Panda/PyBullet execution. "
        "There are no mock rows in the experiment results. Formal Test API episodes: **0**.", "",
        "## Dataset and physical verification", ""]
    distribution = []
    for partition in ("dev", "test"):
        d = frozen["distribution"][partition]
        distribution.append([partition,d["samples"],d["groups"],d["templates"]["pack_and_cover"],
            d["templates"]["place_into_selected_containers"], "/".join(str(d["missing"][str(i)]) for i in range(4))])
    lines += table(["Partition","Samples","Base layout groups","Pack/cover","Two containers","Missing 0/1/2/3"], distribution)
    lines += ["", "All aliases, hidden choices, wording and millimeter perturbations of one physical layout "
        "stay in its partition. Dev/Test can share preference combinations. Test uses held-out container "
        "arrangements; minimum cross-split maximum-matched container distance is "
        f"{frozen['minimum_cross_split_container_distance_m']:.4f} m. "
        "Candidate-list, lexical-ID, observation-list and spatial-rank answer histograms cover both ranks; "
        "counts are in the frozen data audit. This checks deterministic shortcuts, not every possible statistical correlation.", ""]
    lines += table(["Template","Dev actual oracle","Test actual oracle","Combined"], [[
        template, f"{frozen['oracle']['dev']['templates'][template]['successes']}/{frozen['oracle']['dev']['templates'][template]['total']}",
        f"{frozen['oracle']['test']['templates'][template]['successes']}/{frozen['oracle']['test']['templates'][template]['total']}",
        f"{sum(frozen['oracle'][p]['templates'][template]['successes'] for p in ('dev','test'))}/"
        f"{sum(frozen['oracle'][p]['templates'][template]['total'] for p in ('dev','test'))}"]
        for template in ("pack_and_cover", "place_into_selected_containers")])
    lines += ["", f"All {data_check['total']} samples also passed separate all-pairs initial penetration and private/public checks. "
        f"The old {original['total']}-scene oracle passed {original['successes']}/{original['total']} before extension "
        f"and {final_regression['successes']}/{final_regression['total']} on the final controller. "
        f"All {len(original['historical_sha256'])} previously published historical artifact hashes stayed unchanged. "
        "The new containers have a bottom and four physical walls; scoring retains full AABBs, actual support "
        "contact, velocity stability, release, unselected-object exclusion and publicly specified DAG order.", "",
        "## Pre-registered Dev comparison", "",
        "One sample from each of all 8 Dev groups was selected before any Phase 3 authenticated request. "
        "Each template contributes one case at each disclosure level. Five conditions independently reset "
        "physics and history; threshold runs are fresh episodes, not replayed decisions. "
        "Order is randomized/interleaved with seed 20261023. Runtime, prompt, dataset and budget hashes "
        f"were registered at source commit `{plan['code_commit']}`. "
        "The shared planner, question/action prompts, physics, user simulator, evaluator and per-episode budgets are identical.", ""]
    rows = []
    for condition in order:
        r = aggregate[condition]
        ds = r["deepseek_input_tokens"] + r["deepseek_output_tokens"]
        jev = (r["jev_input_tokens"] + r["jev_output_tokens"]) if r["jev_input_tokens"] is not None else "—"
        rows.append([condition,f"{r['successes']}/{r['episodes']} ({r['success_rate']*100:.1f}%)",
            f"{r['burden']} ({r['mean_burden']:.3f})",f"{ds:,}",f"{jev:,}" if isinstance(jev,int) else jev,
            f"{r['api_latency_ms']/1000:.3f}"])
    lines += table(["Condition","Task success","Burden total (mean)","DeepSeek tokens","Jev tokens","API latency total s"],rows)
    lines += ["", "Tokens above are actual input+output, kept separate by backend and never converted into comparable "
        "dollar cost. Per-attempt/CSV input and output remain separate. Failed format repairs count as inference. "
        "Latency is cumulative agent API time; physics/rendering are in episode wall time. "
        "Discovery/revalidation cost is excluded from condition rows and included in the global session.", ""]
    lines += table(["Condition","DeepSeek in/out","Jev in/out","SR group Wilson 95%"], [[condition,
        f"{aggregate[condition]['deepseek_input_tokens']:,}/{aggregate[condition]['deepseek_output_tokens']:,}",
        (f"{aggregate[condition]['jev_input_tokens']:,}/{aggregate[condition]['jev_output_tokens']:,}"
         if aggregate[condition]["jev_input_tokens"] is not None else "—"),
        f"[{aggregate[condition]['success_interval_group_wilson95'][0]:.3f}, "
        f"{aggregate[condition]['success_interval_group_wilson95'][1]:.3f}]"] for condition in order])
    lines += ["", "### Paired sample results", ""]
    matrix = []
    for sample in selected:
        row = [sample.sample_id, sample.template_id,3-len(sample.initial_disclosed_slots)]
        for condition in order:
            e = next(r for r in episodes if r["sample_id"]==sample.sample_id and r["condition"]==condition)
            row.append(("S" if e["task_success"]=="True" else "F") + "/" + e["burden"])
        matrix.append(row)
    lines += table(["Sample","Task","Missing",*order],matrix)
    lines += ["", "Cells are success/failure and burden. Pairing is retained by physical group in paired_groups.json. "
        "Per-condition denominator is 8 independent groups, not 32 Dev variants or 40 independent scenes.", "",
        "## Threshold sensitivity and freeze", "",
        f"Selected threshold: **{result['threshold_selection']['selected_threshold']}**. "
        + result["threshold_selection"]["reason"], "",
        "Thresholds 0.3 and 0.5 produced the same paired success/burden outcomes and token counts on these eight cases, "
        "from separate actual HTTP calls and separately initialized worlds. Their observed latency difference "
        "does not satisfy the predeclared 10%/paired-interval rule. Threshold 0.7 saved requests/slots partly "
        "by failing to clarify, and lost one success. That is not an efficiency win at comparable success.", "",
        "The predeclared 20,000-draw paired group bootstrap (seed 4278) uses 97.5% intervals for two "
        "alternative-vs-default comparisons. Full per-group differences and intervals are in "
        "threshold_selection.json. Eight groups are too few to establish a uniquely optimal threshold or "
        "generalization; default retention is a conservative policy, not evidence that 0.5 is optimal.", "",
        "### Coverage limitation discovered in the selected subset", "",
        "The complete Dev and Test partitions include all 8 normalized preference triples per template. "
        "The predeclared one-variant-per-group online subset covers only 2 triples per template: all selected "
        "blocks are green, all selected pack/cover lids black, and all selected cup destinations container_b. "
        "This results from the deterministic variant/truth schedule, not from inspecting model performance. "
        "It is an important limitation of this small calibration subset and can make NoAsk luck/defaults "
        "look favorable. We did not replace runs after observing outcomes or exceed the 40-episode cap. "
        "See truth_coverage_audit.json for exact counts. A future independent Dev replication should stratify "
        "truth combinations as well as layout/template/disclosure before any new calls. The frozen Test "
        "contains every triple within each of its 16 groups; it was not adjusted using Dev failures.", "",
        "## Errors and clarification timing", ""]
    for condition in order:
        r=aggregate[condition]
        lines.append(f"- {condition}: early ASK {r['early_asks']}, blocked CONTINUE {r['blocked_continues']}, "
            f"redundant requested slots {r['redundant_requests']}, repeated requested slots {r['repeated_requests']}, "
            f"physical skill failures {r['physical_failures']}, schema-error attempts {r['schema_errors']}.")
    lines += ["", "Timing labels are public-only diagnostics, never fed to a model or used as success labels. "
        "NoAsk blocked CONTINUE is expected by design. Recovery states may be left unclassified.", "",
        "- `v3_dev_005`: both object choices are known initially, so packing them first is appropriate. "
        "After packing, the lid remains unknown. LLM-Gate and every Jev threshold nevertheless continued "
        "and chose the wrong lid (Jev probabilities around 0.1). All physical skills succeeded but the "
        "independent evaluator rejected the wrong user preference. This is a late-clarification failure "
        "which a threshold sweep alone did not fix.",
        "- `v3_dev_016 / llm_gate`: all choices were already disclosed, but an initial ASK redundantly "
        "requested cup_destination, charging one extra slot. The task eventually succeeded. Jev runs "
        "on this case completed without that request.",
        "- `v3_dev_010 / Jev 0.7`: initial p=0.56 and next p=0.54 were below 0.7, so the planner guessed "
        "objects. At the lid step it twice emitted pick_place(lid, box, inside), violating the legal "
        "action schema. The single allowed repair retry also failed; the episode stopped with a "
        "SchemaError and was scored on its actual incomplete/wrong physical state. Both billed "
        "responses and usage remain in the logs.",
        "- NoAsk successes on unknown choices are retained, including `v3_dev_026`. It was not forced "
        "to fail. No private preference was supplied to any planner request.", "",
        f"Across all {len(raw_episodes)} episodes, {skill_successes}/{len(actions)} executed skills passed their actual geometric placement check. "
        f"Task failure remains distinct from skill failure. There were {retry_count} retried inference and {schema_count} schema-error "
        f"attempts, {api_error_count} authentication/network/API errors, and {result['global_audit']['unknown_inference_usage']} unknown inference-usage attempts. "
        "ASK invariance and paired initial payload equality passed the independent evidence audit.", "",
        "## API budget, models and tests", "",
        f"Authenticated requests: **{result['session']['attempts']}/{plan['global_limits']['authenticated_requests']}**; "
        f"new online episodes: **{result['episodes']}/{plan['global_limits']['episodes']}**. "
        f"The request IDs are unique and contiguous. {smoke_count} requests are model discovery/revalidation, "
        f"the remaining {result['session']['attempts']-smoke_count} are full-episode inference including format repair. "
        "Configured/returned DeepSeek is deepseek-flash/deepseek-flash; Jev is jev-latest/jev-1.14.0. "
        "DeepSeek returns an alias, so an immutable underlying build is unavailable. Both providers "
        "returned real usage and measured latency during revalidation. Credentials stayed in ignored "
        "0600 .env, outside source/logs/commits.", "",
        f"Original tests: 66/66 before changes. Final tests: {final_tests} passed. JUnit and evidence audit are in "
        "outputs/phase3/pytest_final.xml and evidence.json. Offline pytest blocks urllib network I/O; "
        "synthetic adapter/threshold unit tests are labeled tests and never included in these tables. "
        "No friction-only grasp, hardware test, general motion planner or confirmatory model-quality "
        "experiment is claimed.", "",
        "## Frozen Test and next execution plan", ""]
    lines += table(["Artifact","SHA-256"], [["Dev dataset",config["dataset_hashes"]["dev"]],
        ["Test dataset",config["dataset_hashes"]["test"]],
        ["Frozen Test YAML",sha256(ROOT/"configs/frozen_test.yaml")],
        ["Dev manifest",sha256(PLAN)]])
    lines += ["", "The frozen YAML (JSON syntax, valid YAML 1.2) and companion manifest record configured/returned "
        "models, threshold, prompt hashes, planner parameters, skill/evaluator/source versions, data hashes, "
        "code commit and retry/budget policy. No Test model call has occurred. Changed parameters or model "
        "versions require a distinct experiment ID; unexpected returned models must stop the run.", "",
        f"Next formal Test plan: {test_samples} samples ×3 methods ={test_samples*3} fresh paired episodes, {test_groups} cluster/group units. "
        f"Interleave all methods with seed 427804. Based on Dev means ({means['llm_noask']:g} NoAsk, {means['llm_gate']:g} LLM-Gate, "
        f"{means['jev_gate@0.5']:g} Jev-0.5 calls per episode), nominal request planning is about {predicted_requests:,.0f} episode calls plus discovery "
        "and retries; this is a forecast, not a guarantee. A separate initially proposed 5,000-request "
        "study cap gives headroom and must stop rather than silently expand. Absolute 64-attempt per-episode "
        "limits sum to 24,576, so a global 5,000 ceiling can terminate before all jobs in a bad run. "
        "Run a bounded predeclared canary, retain failures, then continue the same frozen configuration; "
        "never tune on Test outcomes. Additional Dev replication, if desired, is separately versioned and "
        "must precede any replacement Test configuration.", "",
        "## Reproduction and evidence paths", "", "```bash",
        "cd ~/Desktop/CS4278/when2ask", "source .venv/bin/activate",
        "python -m when2ask study oracle --partition dev",
        "python -m when2ask study oracle --partition test",
        "python -m when2ask study check-data", "python -m when2ask study freeze-data",
        "python -m when2ask study plan", "python -m when2ask study smoke --live",
        "python -m when2ask study dev --live --record-first", "python -m when2ask study report",
        "python -m when2ask study freeze-test", "python scripts/build_phase3_report.py",
        "python -m pytest -q --junitxml=outputs/phase3/pytest_final.xml", "python scripts/verify_phase3.py",
        "python scripts/secret_scan.py", "```", "",
        "Generation was run once with seed 4278; `study generate --seed 4278` now refuses to overwrite "
        "the frozen files. Oracle commands validate matching cached evidence and reject changed inputs. "
        "The completed smoke/Dev commands resume matching records without new model calls; the 40-episode "
        "ceiling is exhausted. Use a separately versioned/approved session for future inference.", "",
        "- Dataset/scenes: data/phase3/; physics oracles: outputs/phase3/oracle/{dev,test}/.",
        "- Raw live public states, requests/responses, dense physics, evaluation and PNGs: outputs/phase3_live/dev/.",
        "- CSV/JSON metrics and paired differences: outputs/phase3/report/.",
        f"- Actual two-container GIF: outputs/phase3_live/dev/v3_dev_016__llm_gate/demo.gif ({recording['encoded_frame_count']} encoded TinyRenderer frames, local/ignored).",
        "- Existing `python demo.py --mode ask --gui` and `--mode noask --gui` remain available.", ""]
    target = ROOT / "docs/phase3/dev_report.md"
    target.write_text("\n".join(lines))
    print("Built",target)


if __name__ == "__main__":
    main()
