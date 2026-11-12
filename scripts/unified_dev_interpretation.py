"""Offline post-run explanation of timing and cache effects; no model tuning."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.unified_dev_study import OUT, METHODS, checked
from when2ask.nine_task_data import write


def main():
    checked()
    root=OUT/'report';summary=json.loads((root/'summary.json').read_text())
    attempts=list(csv.DictReader((root/'attempt_costs.csv').open()))
    episodes=list(csv.DictReader((root/'episodes.csv').open()))
    prices=json.loads((OUT/'pricing.json').read_text())
    # These explicit public-order references predate this study in
    # tabletop_contract_dev_v1. They are a diagnostic, not a universal oracle
    # for optimal timing, and never enter a policy request.
    references={'td1_pack_block_first':0,'td1_pack_continue_known_cup':1,
                'td1_containers_block_first':0,'td1_containers_all_known':None}
    methods=[]
    for method in METHODS:
        calls=[r for r in attempts if r['method']==method]
        ds=[r for r in calls if r['backend']=='deepseek']
        hit=sum(int(r['cache_hit_tokens']) for r in ds);miss=sum(int(r['cache_miss_tokens']) for r in ds)
        cache_miss_scenario=0.
        for r in calls:
            if r['backend']=='deepseek':
                rate=prices['deepseek'][r['tariff']]
                cache_miss_scenario+=(int(r['input_tokens'])*rate['cache_miss_per_million']+int(r['output_tokens'])*rate['output_per_million'])/1e6
            else:cache_miss_scenario+=float(r['estimated_usd'])
        rr=[r for r in episodes if r['method']==method]
        matches=None if method=='llm_noask' else sum(
            (int(r['first_ask_after_actions']) if r['first_ask_after_actions'] else None)==references[r['sample_id']] for r in rr)
        methods.append(dict(method=method,deepseek_cache_hit_tokens=hit,deepseek_cache_miss_tokens=miss,
            deepseek_input_cache_hit_fraction=hit/(hit+miss),public_order_first_ask_reference_matches=matches,
            cases=len(rr),hypothetical_all_input_cache_miss_usd=cache_miss_scenario))
    by={r['method']:r for r in summary['methods']}
    result=dict(kind='read_only_post_run_diagnostics',methods=methods,
        cache_scenario_warning='Hypothetical repricing of observed token counts with all DeepSeek input uncached. NOT an additional run, invoice, latency measurement or main observed-cost result.',
        timing_reference_scope='Four explicit Dev cases only; references existed before this run. Same burden and task success can coexist with different first-ASK timing.',
        unified_vs_llm_gate=dict(api_time_change_percent=100*(by['llm_unified']['api_latency_s_total']/by['llm_gate']['api_latency_s_total']-1),
            estimated_usd_change_percent=100*(by['llm_unified']['estimated_usd_total']/by['llm_gate']['estimated_usd_total']-1)),
        findings=[
            'Unified and LLM-Gate ask before the known cup in the independent-order case; Jev performs the supported cup first. All three still complete the task with burden two.',
            'NoAsk fails the unknown-destination two-container case. All robot skills succeed, but its guessed final destinations disagree with fixed GT.',
            'Actual cache mix differs. Longer combined prompt and more cache-miss input make Unified more expensive in this run despite fewer requests and fewer total DeepSeek tokens than separate LLM-Gate.',
            'The observed Jev Gate-stage cost exceeds the heavily cached DeepSeek Gate-stage estimate in this run. Neither Jev nor Unified is guaranteed cheaper.',
            'No repetition, reprompting, threshold changes or selective episode exclusion follows these results.'])
    write(root/'interpretation.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
