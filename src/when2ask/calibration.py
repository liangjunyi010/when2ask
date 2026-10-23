"""Pre-registered Dev study, immutable inputs, hard session caps, no Test calls."""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from .accounting import Audit, Limits, SessionLedger
from .api import DeepSeekClient, JevClient
from .config import Config, ROOT
from .diverse_world import DiverseEnvironment, PHYSICS_VERSION
from .protocol import public_payload
from .research_runner import run_sample
from .study_agents import PROMPT_VERSION, StudyJevGate, StudyLLMGate, prompt_hashes
from .study_data import SOURCE_PAIRS, check_study, load_study, sha256, write_json
from .study_evaluator import EVALUATOR_VERSION
from .study_oracle import code_hash
from .study_protocol import observe

LIVE = ROOT / "outputs/phase3_live"
PLAN = ROOT / "configs/dev_calibration_manifest.json"
FROZEN_DATA = ROOT / "data/phase3/freeze.json"
SELECTED = ("v3_dev_000", "v3_dev_005", "v3_dev_010", "v3_dev_015",
            "v3_dev_016", "v3_dev_021", "v3_dev_026", "v3_dev_031")
CONDITIONS = (("llm_noask", .5), ("llm_gate", .5),
              ("jev_gate", .3), ("jev_gate", .5), ("jev_gate", .7))
SOURCE_FILES = ("accounting.py", "api.py", "config.py", "environment.py", "skills.py", "evaluator.py",
                "diverse_world.py", "study_agents.py", "study_protocol.py", "study_evaluator.py",
                "study_data.py", "research_runner.py", "user_simulator.py", "protocol.py", "task.py", "calibration.py",
                "agents.py", "recording.py", "study_reporting.py", "study_validation.py")
SELECTION_RULE = {
    "default_threshold": .5,
    "unit": "independent physical layout group; 8 paired groups, one sample each",
    "priority": ["task_success", "clarification_burden", "api_latency_ms", "separate_backend_tokens"],
    "bootstrap_seed": 4278, "bootstrap_draws": 20000, "paired_interval": [.0125, .9875],
    "rule": "Compare 0.3 and 0.7 against 0.5 with paired group bootstrap intervals (97.5%, "
            "Bonferroni for two alternatives). Change default only if lower SR-difference bound > 0; "
            "or all 8 paired success outcomes are identical and lower burden-saving bound > 0; "
            "or success AND burden vectors are identical and latency savings >=10% with lower bound >0. "
            "Among eligible alternatives rank SR, mean burden, latency, then distance to default. "
            "Never pool backend tokens as dollars. Incomplete pairing or no clear eligible alternative keeps 0.5.",
    "limitation": "Exploratory engineering Dev calibration; intervals at 8 groups are unstable, not a confirmatory claim."
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def study_ledger():
    return SessionLedger(LIVE, 600, 40, policy="phase3_dev")


def source_hashes():
    return {"src/when2ask/" + name: sha256(ROOT / "src/when2ask" / name) for name in SOURCE_FILES}


def bias_audit(samples):
    result = {}
    for s in samples:
        scene = s.scene()
        inverse = {v: k for k, v in scene["object_id_map"].items()}
        for slot, registry in s.slots.items():
            key = f"{s.partition}/{s.template_id}/{registry['public_role']}"
            row = result.setdefault(key, dict(candidate_list_rank={}, lexical_id_rank={}, observation_rank={},
                                              spatial_rank={}, canonical_choices={}))
            truth, ids = s.theta_star[slot], registry["candidate_ids"]
            positions = {scene["object_id_map"][k]: xy for k, xy in scene["sources"].items()}
            positions.update({scene["object_id_map"][c["id"]]: c["xy"] for c in scene["containers"]})
            orders = {"candidate_list_rank": ids, "lexical_id_rank": sorted(ids),
                      "observation_rank": [k for k in scene["object_order"] if k in ids],
                      "spatial_rank": sorted(ids, key=lambda k: positions[k])}
            for name, order in orders.items():
                rank = str(order.index(truth))
                row[name][rank] = row[name].get(rank, 0) + 1
            canonical = inverse[truth]
            row["canonical_choices"][canonical] = row["canonical_choices"].get(canonical, 0) + 1
    if any(set(r[name]) != {"0", "1"} for r in result.values() for name in
           ("candidate_list_rank", "lexical_id_rank", "observation_rank", "spatial_rank")):
        raise ValueError("A fixed rank exposes all correct choices in a task/partition/role stratum")
    return result


def freeze_data():
    if FROZEN_DATA.exists():
        verify_data_freeze()
        return json.loads(FROZEN_DATA.read_text())
    samples = load_study("dev") + load_study("test")
    summary = check_study(samples)
    oracle = {}
    for partition in ("dev", "test"):
        path = ROOT / f"outputs/phase3/oracle/{partition}/summary.json"
        result = json.loads(path.read_text())
        if result["physics_code_sha256"] != code_hash():
            raise ValueError("Oracle uses a different controller/evaluator")
        subset = [s for s in samples if s.partition == partition]
        if result["total"] != len(subset) or result["successes"] != len(subset):
            raise ValueError("All frozen samples must pass real oracle; fix/version candidate data first")
        if any(r["initial_penetrations"] for r in result["runs"]):
            raise ValueError("Initial scene penetration")
        oracle[partition] = dict(successes=result["successes"], total=result["total"],
                                 templates=result["templates"], summary_sha256=sha256(path))
        # Validate each public projection against real oracle sensor snapshots.
        for s in subset:
            scene = s.scene()
            ids = scene["object_id_map"]
            for slot, registry in s.slots.items():
                role = registry["public_role"]
                canonical = SOURCE_PAIRS.get(role, ("container_a", "container_b"))
                if set(registry["candidate_ids"]) != {ids[k] for k in canonical}:
                    raise ValueError("Slot candidates differ from the actual visible category")
            raw = json.loads((path.parent / f"{s.sample_id}.json").read_text())["initial_observation"]
            from .task import PublicState
            payload = public_payload(PublicState.build(raw, [], s.u0))
            for forbidden in ("theta_star", "slots", "dag", "group_id", "sample_id", "partition", "task_success"):
                if '"' + forbidden + '"' in json.dumps(payload):
                    raise ValueError("Private metadata entered the public projection")
    manifest = json.loads((ROOT / "data/phase3/manifest.json").read_text())
    result = dict(dataset_version=manifest["dataset_version"], frozen_at=utc_now(),
                  distribution=summary["distribution"], independent_groups=summary["independent_groups"],
                  dataset_hashes=manifest["dataset_hashes"], scene_hashes=manifest["scene_hashes"],
                  geometry_version=PHYSICS_VERSION, evaluator_version=EVALUATOR_VERSION,
                  physics_code_sha256=code_hash(), oracle=oracle, bias_audit=bias_audit(samples),
                  minimum_cross_split_container_distance_m=summary["minimum_cross_split_container_distance_m"],
                  test_api_episodes=0, note="Test used only for schema, leakage and physical feasibility checks; no inference/tuning")
    write_json(FROZEN_DATA, result)
    return result


def verify_data_freeze():
    frozen = json.loads(FROZEN_DATA.read_text())
    for split, expected in frozen["dataset_hashes"].items():
        if sha256(ROOT / f"data/phase3/{split}.jsonl") != expected:
            raise ValueError("Frozen dataset was modified")
    for ref, expected in frozen["scene_hashes"].items():
        if sha256(ROOT / ref) != expected:
            raise ValueError("Frozen scene was modified")
    if code_hash() != frozen["physics_code_sha256"]:
        raise ValueError("Frozen oracle/controller changed")
    return frozen


def create_plan():
    verify_data_freeze()
    if PLAN.exists():
        return verify_plan()
    config = Config.load()
    validation_path = ROOT / "outputs/phase3/data_validation.json"
    validation = json.loads(validation_path.read_text())
    if not validation["all_passed"] or validation["total"] != 160:
        raise ValueError("Full data validation must precede API registration")
    samples = {s.sample_id: s for s in load_study("dev")}
    selected = [samples[s] for s in SELECTED]
    assert len({s.group_id for s in selected}) == 8
    jobs = []
    for sample in selected:
        for method, threshold in CONDITIONS:
            condition = method if method != "jev_gate" else f"jev_gate@{threshold:.1f}"
            run_id = sample.sample_id + "__" + condition.replace("@", "_t").replace(".", "p")
            jobs.append(dict(run_id=run_id, sample_id=sample.sample_id, group_id=sample.group_id,
                             template_id=sample.template_id, missing_preferences=3-len(sample.initial_disclosed_slots),
                             scene_seed=sample.scene_seed, method=method, threshold=threshold, condition=condition))
    random.Random(20261023).shuffle(jobs)
    result = dict(study_id="phase3_dev_calibration_v1", registered_at=utc_now(), partition="dev",
        code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_sha256=source_hashes(), dataset_freeze_sha256=sha256(FROZEN_DATA),
        data_validation_sha256=sha256(validation_path),
        dataset_hashes=verify_data_freeze()["dataset_hashes"],
        public_prompt_version=PROMPT_VERSION, prompt_hashes=prompt_hashes(),
        model_configuration=config.public_config(), random_interleave_seed=20261023,
        limits=asdict(Limits()), global_limits=dict(episodes=40, authenticated_requests=600),
        retry_policy=dict(max_retries=config.max_retries, timeout_s=config.timeout_s,
            backoff_s=[.5], permanent_http=[400, 401, 402, 403, 404, 422],
            circuit_breaker="block backend after 3 consecutive unsuccessful responses",
            all_discovery_smoke_diagnostics_repairs_and_retries_count=True),
        selection_rule=SELECTION_RULE, jobs=jobs,
        sample_selection="One per each of all eight Dev scene groups; variants 0/1/2/3 repeated across two templates. "
                         "Chosen before API results, not selected for Jev performance.",
        no_test_inference=True, smoke_policy="2 model discoveries + one real gate inference per backend; no additional full episodes")
    write_json(PLAN, result)
    return result


def verify_plan():
    plan = json.loads(PLAN.read_text())
    verify_data_freeze()
    if (plan["source_sha256"] != source_hashes() or plan["prompt_hashes"] != prompt_hashes()
            or plan["dataset_freeze_sha256"] != sha256(FROZEN_DATA)
            or plan["model_configuration"] != Config.load().public_config()):
        raise ValueError("Pre-registered code/config/data changed; cannot continue the same experiment")
    return plan


def revalidate_live():
    plan = verify_plan()
    output = LIVE / "revalidation.json"
    if output.exists():
        return json.loads(output.read_text())
    config, session = Config.load(), study_ledger()
    audit = Audit("phase3_revalidation", config, session, LIVE / "revalidation_attempts.jsonl", limit=16)
    ds, jev = DeepSeekClient(config, audit), JevClient(config, audit)
    sample = next(s for s in load_study("dev") if s.sample_id == SELECTED[-1])
    result = dict(plan_sha256=sha256(PLAN), started_at=utc_now(), full_episodes=0, results={})
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        state = observe(env, sample.u0, [])
        before = env.snapshot()
        for backend, client, gate in (("deepseek", ds, StudyLLMGate(ds)), ("jev", jev, StudyJevGate(jev, .5))):
            try:
                catalog = client.models()
                decision = gate.decide(state).to_dict()
                record = audit.records[-1]
                result["results"][backend] = dict(success=True, catalog=catalog, gate=decision,
                    returned_model=record["returned_model"], input_tokens=record["input_tokens"],
                    output_tokens=record["output_tokens"], latency_ms=record["latency_ms"], schema_valid=True)
            except Exception as exc:
                result["results"][backend] = dict(success=False, error=config.sanitize(str(exc)))
        result["physical_world_unchanged"] = env.snapshot() == before
    result.update(cost=audit.summary(), session=session.snapshot())
    write_json(output, config.sanitize(result))
    return result


def run_dev(*, record_first=False):
    plan = verify_plan()
    smoke = json.loads((LIVE / "revalidation.json").read_text())
    if not all(r["success"] for r in smoke["results"].values()):
        raise ValueError("Backend smoke failed; keep diagnostics and fix/version before full study")
    config, session = Config.load(), study_ledger()
    samples = {s.sample_id: s for s in load_study("dev")}
    completed, skipped = [], []
    for index, job in enumerate(plan["jobs"]):
        out = LIVE / "dev" / job["run_id"]
        if (out / "episode.json").exists():
            episode = json.loads((out / "episode.json").read_text())
            if episode["prompt_hashes"] != plan["prompt_hashes"]:
                raise ValueError("Existing episode has different prompts")
            completed.append(job["run_id"])
            continue
        budget = session.snapshot()
        if budget["episodes"] >= 40 or budget["attempts"] >= 600:
            skipped.extend(j["run_id"] for j in plan["jobs"][index:])
            break
        needs = ("deepseek", "jev") if job["method"] == "jev_gate" else ("deepseek",)
        if any(budget["backends"].get(b, {}).get("blocked") for b in needs):
            skipped.append(job["run_id"])
            continue
        print(f"DEV {index + 1}/40 {job['run_id']} session={budget['attempts']}/600", flush=True)
        episode = run_sample(samples[job["sample_id"]], job["method"], out, live=True,
            config=replace(config, threshold=job["threshold"]), limits=Limits(**plan["limits"]), session=session,
            record=record_first and index == 0)
        write_json(out / "study_metadata.json", dict(job=job, plan_sha256=sha256(PLAN),
                                                   completed_at=utc_now()))
        completed.append(job["run_id"])
    result = dict(completed=completed, skipped=skipped, session=session.snapshot(), plan_sha256=sha256(PLAN))
    write_json(LIVE / "run_status.json", result)
    return result
