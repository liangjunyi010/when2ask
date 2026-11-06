"""Audit/interpret existing evidence, without changing prompts or calling models."""
import hashlib
import html
import json
from collections import Counter
from pathlib import Path


def main():
    root=Path('outputs/navigation_dev_v2');run=root/'study_v2';summary=json.loads((run/'summary.json').read_text())
    preserve=json.loads(Path('outputs/local_console/navigation-v2-preservation.json').read_text())['files']
    changed=[p for p,h in preserve.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    assert not changed
    failed=[json.loads(p.read_text()) for p in (root/'study_v1/episodes').glob('*/episode.json')]
    assert len(failed)==12 and sum(len(e['actions']) for e in failed)==0
    oldplan=json.loads((root/'study_v1/plan.json').read_text());newplan=json.loads((run/'plan.json').read_text())
    assert all(oldplan['prompt_hashes'][k]==newplan['prompt_hashes'][k] for k in ('cost_exclusive','overlap_control','criteria'))
    assert oldplan['snapshots_sha256']==newplan['snapshots_sha256'] and oldplan['dataset_sha256']==newplan['dataset_sha256']
    stage_checks=[];p_ranges=[]
    for p in (run/'episodes').glob('*/episode.json'):
        e=json.loads(p.read_text());api=[json.loads(s) for s in p.with_name('api_attempts.jsonl').read_text().splitlines() if s]
        for a in api:
            assert 'nominal_reference' not in json.dumps(a.get('request',{}))
        if e['method']=='llm_noask':assert all(a['stage']=='action' for a in api)
        else:
            for turn in e['turns']:
                stages=[a['stage'] for a in api if a['round']==turn['round']]
                assert stages[0]=='gate'
                for i,s in enumerate(stages):
                    if s in ('action','question'):assert 'gate' in stages[:i]
        if e['method']=='jev_gate':
            ps=[t['gate']['p_ask'] for t in e['turns']]
            p_ranges.append(dict(sample=e['sample_id'],min=min(ps),max=max(ps),sequence=ps))
        stage_checks.append(dict(episode=e['episode_id'],gate_before_planner=True,api_calls=len(api),burden=e['clarification_burden']))
    audit=dict(protected_file_count=len(preserve),protected_files_unchanged=True,
        frozen_v1_unchanged=True,old_protocol_launches=len(failed),old_physical_actions=0,
        old_terminations=dict(Counter(e['termination_reason'] for e in failed)),
        gate_and_data_unchanged_across_json_marker_fix=True,global_requests=summary['requests'],
        registered_launches=summary['protocol_incident']['combined_registered_launches'],
        valid_physical_episodes=len(summary['episodes']),stage_checks=stage_checks,jev_probabilities=p_ranges,
        no_reference_values_sent_to_models=True,held_out_test_calls=0)
    categories={'gate_ablation':list((run/'ablation').glob('gate_*.jsonl')),
        'protocol_incident':[run/'incident_api_attempts.jsonl'],
        'valid_episodes':list((run/'episodes').glob('*/api_attempts.jsonl'))}
    accounting={}
    for category,paths in categories.items():
        records=[json.loads(s) for p in paths for s in p.read_text().splitlines() if s]
        accounting[category]={}
        for backend in ('deepseek','jev'):
            rs=[r for r in records if r['backend']==backend]
            accounting[category][backend]=dict(attempts=len(rs),
                observed_input_tokens=sum(r['input_tokens'] for r in rs if r.get('input_tokens') is not None) if rs else None,
                observed_output_tokens=sum(r['output_tokens'] for r in rs if r.get('output_tokens') is not None) if rs else None,
                unknown_usage_attempts=sum(r.get('input_tokens') is None or r.get('output_tokens') is None for r in rs),
                latency_s=sum(r.get('latency_ms') or 0 for r in rs)/1000 if rs else None)
    assert sum(v['attempts'] for c in accounting.values() for v in c.values())==summary['requests']
    audit['accounting_by_stage_and_backend']=accounting
    (root/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    refs=json.loads((root/'references/results.json').read_text())
    refrows=[{k:r[k] for k in ('sample','policy','success','burden','distance_m','motion_sim_s','modeled_operational_s')} for r in refs]
    lines=['# Navigation Dev v2 interpretation','',
        f"Verified {len(summary['episodes'])} physical model episodes and 48 gate-only calls. Total authenticated attempts including the protocol incident: {summary['requests']}/200.",'',
        'All 48 gate-only outputs were CONTINUE. Thus this small ablation did not show a decision-level effect of exclusive wording or the derived summary. Its six states share one map and cannot support generalization or significance claims. The nominal reference is conditional on approximate kinematic costs and a stipulated prior; disagreement is a diagnostic, not proof that a real human would prefer a question.','',
        'Complete episodes contain additional measured states beyond those six snapshots. Their actual ASK events must be read from raw turns. Any ASK appearing online does not retroactively change the gate-only result.','',
        'The action planner is identical across methods (temperature 0, same prompts/model), yet generated station orders can differ. For example, normal-speed/30s-delay LLM-Gate visited the kitchen while the other two chose the study earlier, even though all three continued. This is planner route variation, not a demonstrated gate-timing effect. Matched-state ablations isolate Gate outputs better; this tiny end-to-end pilot mixes timing with realized search-order variability.','',
        '## Technical incident and amendment','',
        'The original v2 run registered 12 episode launches and made no robot actions. A DeepSeek HTTP 400 required a literal JSON marker in JSON-object-mode prompts. Its 48 successful gate calls and six launch-stage requests are retained. All source/raw records of that run remain available. The marker was added to Action/Question prompts, regression-tested, and a new hashed plan was created before valid physical execution. Gate rules, threshold, scene facts and ablation snapshots were unchanged; gate-only results were reused without payment.','',
        'This explicitly amends the launch cap: 24 combined registrations, comprising 12 execution-before-motion aborts and 12 valid physical runs. The original 200-request cap was preserved using a 54-request offset and a fresh session with at most 146 remaining requests. The amended plan allows 140 for valid episodes. This is a software repair, not a prompt/threshold selection based on performance.','',
        '## Unpaid physical policy anchors','',
        'The anchors below actually execute wheel-driven physics. Their answer-wait costs are arithmetic using the declared delay; the offline script does not sleep. They are not additional LLM/Jev episodes, and modeled time must not be reported as observed wall time. The nominal-cost Gate is an independent diagnostic policy, never an override on learned gates.','',
        '| Cost case | Policy | Success | Burden | Motion simulation s | Modeled operational s |','|---|---|---:|---:|---:|---:|']
    for r in refrows:lines.append(f"| {r['sample']} | {r['policy']} | {r['success']} | {r['burden']} | {r['motion_sim_s']:.2f} | {r['modeled_operational_s']:.2f} |")
    lines+=['','## Limits and next experiment','',
        'One original map group and one seed-selected target are used for the complete cost-factorial. The uniform prior is a planning stipulation, not a frequency estimated from the four placements. Realized cost on this target can disagree with expected cost under that prior. Therefore neither realized advantage nor nominal-reference match alone proves optimal clarification timing.','',
        'A next independent version should balance multiple target placements across independent layouts, hold declared costs fixed, quantify search-order variation, and preregister any threshold sensitivity by operational cost/burden, not ask frequency. Recompute actual trajectories for every threshold. Keep existing frozen Test and these results unchanged.','',
        f"Preservation: all {len(preserve)} pre-existing protected file hashes match. No held-out Test calls; user-modified PPT preserved."]
    (root/'ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    note='<section id="evidence-audit"><h2>Interpretation and protocol audit</h2><p>All 48 gate-only outputs were CONTINUE. Six matched public states did not show a decision-level ablation effect. Actual full-episode questions are recorded separately; this is one map and one target, not independent-group evidence.</p><p>Shared Planner can produce different station orders even at temperature 0. Total execution-cost differences cannot all be attributed to Gate timing.</p>'
    note+=f'<p><strong>Technical incident retained:</strong> 12 launches aborted before motion due to a missing JSON-mode marker. Six launch-stage calls plus 48 ablation calls are included in {summary["requests"]}/200 total requests. After a format-only repair: 12 valid physical runs; 24 combined registrations. No gate/threshold tuning.</p>'
    note+='<p><a href="../ANALYSIS.md">Detailed interpretation</a> · <a href="../audit.json">Preservation/protocol audit</a> · <a href="../references/results.json">Unpaid physical policy anchors</a></p></section>'
    import re
    p=run/'index.html';text=p.read_text()
    text=re.sub(r'<section(?: id="evidence-audit")?><h2>Interpretation and protocol audit</h2>.*?</section>','',text,flags=re.S)
    if 'rel="icon"' not in text:text=text.replace('<title>','<link rel="icon" href="data:,"><title>',1)
    p.write_text(text.replace('</body>',note+'</body>'))
    print(json.dumps({k:audit[k] for k in ('protected_file_count','global_requests','registered_launches','valid_physical_episodes')},indent=2))


if __name__=='__main__':main()
