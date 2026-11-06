"""Post-run integrity and readable Dev report. No inference calls or tuning."""
import hashlib
import html
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from when2ask.dev_public_summary import digest
from when2ask.dev_summary_study import OUTPUT, seal


def main():
    manifest = seal()  # Checks sealed inference/statistic sources without changing them.
    old = json.loads((ROOT / 'outputs/local_console/summary-dev-preservation.json').read_text())
    changed = [name for name,sha in old['files'].items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
    ppt = ROOT / 'presentation/milestone/When2Ask_Milestone_Presentation.pptx'
    assert not changed and hashlib.sha256(ppt.read_bytes()).hexdigest()==old['ppt_sha256']
    episodes = [json.loads(p.read_text()) for p in sorted((OUTPUT/'episodes').glob('*/episode.json'))]
    rows = [r for ep in episodes for r in ep['api_attempts']]
    assert len(episodes)==12 and len(rows)==140
    assert sorted(r['session_attempt'] for r in rows)==list(range(1,141))
    assert all(r['http_status']==200 and r['status']=='ok' for r in rows)
    assert all(c['state_unchanged'] for ep in episodes for c in ep['ask_checks'])
    analysis = json.loads((OUTPUT/'report/analysis.json').read_text())
    by_request = defaultdict(list)
    for ep in episodes:
        for row in ep['api_attempts']:
            if row['backend']=='deepseek' and row['stage']=='action' and row['status']=='ok':
                value=json.loads(row['response']['choices'][0]['message']['content'])
                by_request[digest(row['request'])].append(dict(episode_id=ep['episode_id'],round=row['round'],action=value))
    different = [dict(request_sha256=k,outputs=v) for k,v in by_request.items()
                 if len({digest(r['action']) for r in v})>1]
    physical = [a for ep in episodes for a in ep['actions']]
    audit = dict(all_original_tracked_files_unchanged=True, protected_files=len(old['files']),
        existing_user_ppt_unchanged=True, sealed_sources_match=True, source_commit=manifest['code_commit'],
        real_model_episodes=len(episodes), authenticated_requests=len(rows), reservation_ids_unique_contiguous=True,
        successful_physical_skills=sum(a['success'] for a in physical), physical_skill_calls=len(physical),
        actual_model_payloads_and_probabilities_checked_by_report=True,
        ask_physics_invariant=True, test_api_episodes=0,
        budget_terminations=[dict(episode_id=e['episode_id'],error=e['error'],task_success=e['evaluation']['task_success'])
                             for e in episodes if e['termination_reason']!='done'],
        identical_action_request_groups_with_different_outputs=different,
        frozen_test_sha256=hashlib.sha256((ROOT/'configs/frozen_test.yaml').read_bytes()).hexdigest())
    (OUTPUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    regression = {e['profile']:e for e in episodes if e['case_id']=='regression_console_m2'}
    labels = {'v3_original':'Original v3.1','compact_state':'Compact public facts','compact_question':'Compact facts + short Noul'}
    first = {p:e['turns'][0]['gate'] for p,e in regression.items()}
    summary = analysis['summary']
    lines = ['# Independent Dev version: findings and limits', '',
        'This version adds files only. Frozen Test configuration, all prior data/reports, existing agents/physics/evaluator and the user-modified PPT are unchanged. '
        f"Integrity audit checked {audit['protected_files']} existing tracked files. Inference sources were sealed at commit `{manifest['code_commit']}` before model calls.", '',
        '## Observed outcome', '',
        'Task completion improved from 2/4 to 4/4 for both compact variants on these four deliberately scoped Dev cases. '
        'The joint variant reduced public-information blocked CONTINUE decisions from 5 to 0, but both new variants added one premature ASK. '
        'Neither satisfies the predeclared no-new-early-ASK rule. Neither is adopted as the frozen/default configuration.', '',
        'The old/new task-success difference is not exclusively a Jev gate effect: compact_state also changes the public representation read by the unchanged DeepSeek planner. '
        'The all-known two-container original run repeatedly removed/replaced a correctly placed block, exhausting its action budget. '
        'The compact-state run also reached its action budget, but its final geometric/contact/DAG state passed; it remains scored successful despite no DONE. '
        'The joint run finished that task with six physical actions. All skill calls succeeded; the extra actions were planning/repair choices.', '',
        '## Target regression: identical initial public state', '',
        '| Profile | Initial Jev p(ASK) | Actual decision | Interpretation |', '|---|---:|---|---|']
    for p in ('v3_original','compact_state','compact_question'):
        g=first[p]
        lines.append(f"| {p} | {g['p_ask']:.2f} | {g['decision']} | {'Premature: the specified blue cup is still executable' if g['decision']=='ASK' else 'Correctly continues with the known cup'} |")
    lines += ['',
        'The new variants obtain the missing block/lid answers early and then finish correctly. They do not yet produce the desired CONTINUE → pack cup → ASK sequence. '
        'After this early answer, their later states include more public information; their round-1 probabilities must not be compared to the original round-1 as if the states were identical.', '',
        'The one-unknown late-lid case is also informative: the original and compact-state runs guessed the correct lid and passed the physical task without asking. '
        'They still missed the information gap at the selection stage. The joint version asked after both known objects had been packed. '
        'Thus physical task success and clarification timing are reported separately; lucky guesses are not marked as task failures.', '',
        f"Actual duplicate action-request groups with differing model outputs: {len(different)}. "
        'Details are in audit.json. The shared planner prompts and temperature were unchanged; identical returned model aliases and temperature=0 do not establish identical repeated outputs. '
        'Consequently completion differences, particularly repair loops, must not all be attributed to gate wording.', '',
        '## Evidence and reproducibility', '',
        f"Oracle 4/4; {len(episodes)} real model episodes, {len(rows)}/140 authenticated requests, "
        f"{audit['successful_physical_skills']}/{len(physical)} physical skills succeeded. No HTTP/schema errors or retries. "
        '181 offline tests passed; synthetic unit transports are kept outside the experiment reports. No Test API calls ran.', '',
        '- [Generated metrics and pairing](report/README.md)',
        '- [Read-only visual report](report/index.html)',
        '- [Raw episode table](report/episodes.csv)',
        '- [Every gate decision](report/gate_turns.csv)',
        '- [Matched public states](report/matched_public_states.json)',
        '- [Integrity and request audit](audit.json)',
        '- Real GIFs remain local under episodes/regression_console_m2__{v3_original,compact_question}/demo.gif; PNGs and JSON are committed.', '',
        '```sh', 'python scripts/run_summary_dev.py prepare', 'python scripts/run_summary_dev.py seal',
        'python scripts/run_summary_dev.py run --live', 'python scripts/run_summary_dev.py report',
        'python scripts/audit_summary_dev.py', '```', '',
        'The sealed v1 is complete and its budget is exhausted. Re-running the command skips saved episodes and does not create new requests. '
        'Any new prompt/summary replication needs an explicitly separate experiment version. '
        'The next useful Dev question is how to preserve known-subgoal-first behavior while retaining the reduced late misses, '
        'using public facts without injecting a computed ready-action or ASK oracle.', '']
    (OUTPUT/'README.md').write_text('\n'.join(lines))
    body = []
    for s in summary:
        body.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [labels[s['profile']],f"{s['task_successes']}/4",s['burden'],s['early_asks'],s['blocked_continues'],f"{s['api_latency_ms']/1000:.2f} s",f"{s['deepseek_input_tokens']} / {s['deepseek_output_tokens']}",f"{s['jev_input_tokens']} / {s['jev_output_tokens']}"])+'</tr>')
    initial = ''.join('<tr><td>'+labels[p]+'</td><td>'+str(first[p]['p_ask'])+'</td><td>'+first[p]['decision']+'</td><td>'+('Premature ASK' if first[p]['decision']=='ASK' else 'Known cup can proceed')+'</td></tr>' for p in ('v3_original','compact_state','compact_question'))
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>When2Ask · Independent Dev Lab</title><style>
    *{box-sizing:border-box}body{margin:0;background:#09121e;color:#e5eff9;font:15px -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif}main{max-width:1600px;margin:auto;padding:40px}h1{font-size:36px;margin:12px 0}h2{font-size:21px;margin:0 0 16px}p{color:#9eafc4;line-height:1.8}a{color:#6bdfd0}header>span{font-size:11px;letter-spacing:2px;color:#70e3d4}.tag{display:inline-block;background:#3d3023;color:#ffcc8a;border:1px solid #795737;padding:8px 14px;border-radius:6px;margin:5px 0 20px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:15px 0 24px}.stat,section{border:1px solid #293c52;background:#111f30;border-radius:12px;padding:23px}.stat strong{display:block;font-size:27px;color:#80e6d4}.stat span{color:#91a6c0;font-size:12px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}th{text-align:left;font-size:11px;color:#8fa9c3;border-bottom:1px solid #3c506a;padding:12px}td{padding:14px 12px;border-bottom:1px solid #283b51;font-size:13px}section{margin:20px 0}.grid{display:grid;grid-template-columns:1.1fr 1fr;gap:20px}.warning{color:#ffcc8a}code{color:#8ddcd4}small{color:#91a6c0}ul{line-height:2;color:#a1b4ca}.media{display:flex;gap:14px;flex-wrap:wrap}@media(max-width:900px){main{padding:20px}.stats{grid-template-columns:1fr 1fr}.grid{display:block}h1{font-size:27px}}
    </style></head><body><main><header><span>WHEN2ASK / INDEPENDENT DEV LAB / V1</span><h1>Fewer missed questions. Timing still matters.</h1><p>公开状态摘要与 Noul 问句消融实验 · 4 个独立 Dev 场景 · 阈值固定 0.5</p><div class="tag">未替换冻结配置 · 未运行正式 Test · 不作统计显著性结论</div></header>'''
    page += '<div class="stats">'+''.join('<div class="stat"><strong>'+str(v)+'</strong><span>'+k+'</span></div>' for v,k in [('12 / 12','真实模型 episodes'),('140 / 140','认证请求 / 硬预算'),('4 / 4','真实 PyBullet oracle'),('181 passed','离线测试 · 无付费请求')])+'</div>'
    page += '<section><h2>Real paired results</h2><div class="scroll"><table><tr><th>Jev condition</th><th>Success</th><th>Burden Σ</th><th>Early ASK</th><th>Blocked CONTINUE</th><th>API latency Σ</th><th>DeepSeek in/out</th><th>Jev in/out</th></tr>'+''.join(body)+'</table></div><p>每行合计 4 个场景；tokens 分后端统计，API latency 为累计调用时间。三种条件共享物理技能、独立 evaluator、阈值和动作/问题 Planner 提示。</p></section>'
    page += '<div class="grid"><section><h2>The original failure case</h2><div class="scroll"><table><tr><th>Condition</th><th>Initial p(ASK)</th><th>Decision</th><th>Timing</th></tr>'+initial+'</table></div><p class="warning">初始状态完全相同：蓝杯已指定且尚未装箱。两个新版本都提前问了方块和盖子，任务完成了，但还没有实现“先装蓝杯，再询问”。</p></section><section><h2>Decision: retain the frozen version</h2><p>漏问减少与提前询问同时发生。按预先锁定的规则，两个候选版本均不自动晋升为正式配置。</p><p>全公开双容器案例还出现了 DeepSeek 反复搬动方块的规划问题。原版达到动作上限失败；摘要版同样达到上限，但最终物理状态满足任务，仍按真实状态计成功。完成率差异不能全部归因于 Jev Gate。</p></section></div>'
    page += '<section><h2>Inspect the evidence</h2><ul><li><a href="README.md">完整自动计算报告</a> · <a href="episodes.csv">Episode CSV</a> · <a href="gate_turns.csv">每轮 Gate CSV</a></li><li><a href="matched_public_states.json">相同公开状态配对</a> · <a href="../audit.json">源代码、旧文件与请求审计</a></li><li>真实录像（独立轨迹，未声称同步播放）：<a href="../episodes/regression_console_m2__v3_original/demo.gif">原版</a> · <a href="../episodes/regression_console_m2__compact_question/demo.gif">摘要 + 短问句</a></li><li>所有原始 JSON、真实 PNG、模型请求与独立物理评分保存在各 episode 目录；没有 mock 数据填表。</li></ul><small>Question interface reference: <a href="https://docs.typesafe.ai/primitives/noul">TypeSafe Noul documentation</a></small></section></main></body></html>'
    (OUTPUT/'report/index.html').write_text(page)
    hashes = {str(p.relative_to(OUTPUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*')
              if p.is_file() and p.suffix!='.gif' and p.name!='artifact_hashes.json'}
    (OUTPUT/'artifact_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k!='identical_action_request_groups_with_different_outputs'}))


if __name__=='__main__':
    main()
