"""Independent nine-task Dev cases with explicit, model-hidden FPR strata."""
import os
from pathlib import Path
import copy
import hashlib
import json
from dataclasses import asdict, replace

from .config import ROOT
from .nine_task_data import Case, TEMPLATES, STUDY, load as original_load, write
from .study_data import instruction, dag_for
from .navigation_task import NavigationSample

VERSION='nine_task_metrics_dev_v1'
DATA=ROOT/'data'/VERSION
OUT=Path(os.environ.get('WHEN2ASK_RUN_DIR', str(ROOT/'result'/VERSION))).resolve()


def create_rows():
    originals=original_load('dev');rows=[]
    six={s['template_id']:s for s in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']}
    for ti,template in enumerate(TEMPLATES):
        bases=[s for s in originals if s.template_id==template]
        for i in range(3):
            base=bases[0 if i==0 else 1]
            known=i<2;disclosed=list(base.slots) if known else []
            dag=copy.deepcopy(base.dag)
            if template in STUDY:
                order='independent' if i==0 else 'block_first'
                dag=dag_for(template,order);text=instruction(template,order,i)
                if not known:
                    disclosed=['cup_choice'] if template=='pack_and_cover' else ['cup_choice','block_choice']
                for slot in disclosed:text+=f" For the {base.slots[slot]['public_role']}, use {base.theta_star[slot]}."
            elif template=='find_and_approach':
                text=NavigationSample('metrics_dev',base.target_location,disclosed=known).u0
            else:
                text=six[template]['u0']
                for slot in disclosed:text+=f" The user specifies {base.slots[slot]['public_role']}={base.theta_star[slot]}."
            sample=replace(base,sample_id=f'md1_{ti:02d}_{i}',u0=text,dag=dag,initial_disclosed_slots=disclosed).validate()
            label=('no_ask_required' if known else 'search_hint_optional' if template=='find_and_approach'
                   else 'observable_fact_no_ask' if template=='occlusion_inspection' else 'preference_clarification_required')
            rows.append(dict(sample=asdict(sample),source_dev_sample_id=base.sample_id,
                condition=label,fpr_core_negative=known,
                annotation_basis=('All user choices / target location explicitly disclosed; physical goal still requires execution.' if known else
                    'Unseen world location can be discovered by search; no mandatory-ASK label.' if template=='find_and_approach' else
                    'Required physical inspection reveals the label; unknown fact is not a hidden preference.' if template=='occlusion_inspection' else
                    'A fixed undisclosed user preference affects the final goal and cannot be inferred from physical observation; guessing may happen to succeed.')))
    return rows


def prepare():
    DATA.mkdir(parents=True,exist_ok=False)
    rows=create_rows()
    audit_rows(rows)
    value=dict(study_version=VERSION,partition='dev_only',cases=rows,
        design='Nine templates x two fully disclosed FPR negatives plus one information-condition contrast. All are new Dev sample variants of 18 existing Dev physical groups; not new Test.',
        fpr_scope='Balanced core: exactly 18 fully disclosed cases, two per template. Unknown navigation is not a required-ASK positive; observable-fact contrast is a supplemental hard negative, excluded from core denominator.',
        group_policy='The contrast shares the second negative layout group; variants are not independent observations. No confidence interval treats 27 cases as 27 independent groups.',
        metadata_policy='Condition, fpr labels and source sample IDs are retained by the harness only, never supplied to policies.')
    write(DATA/'samples.json',value)
    return audit_rows(rows)


def entries():return json.loads((DATA/'samples.json').read_text())['cases']


def load():return [Case(**r['sample']).validate() for r in entries()]


def audit_rows(rows):
    samples=[Case(**r['sample']).validate() for r in rows]
    assert len(samples)==27 and len({s.sample_id for s in samples})==27
    original_dev={s.group_id for s in original_load('dev')}
    original_test={s.group_id for s in original_load('test')}
    assert all(s.partition=='dev' and s.group_id in original_dev and s.group_id not in original_test for s in samples)
    for template in TEMPLATES:
        rr=[r for r in rows if r['sample']['template_id']==template]
        assert len(rr)==3 and sum(r['fpr_core_negative'] for r in rr)==2
        for r in rr:
            if r['fpr_core_negative']:
                assert set(r['sample']['initial_disclosed_slots'])==set(r['sample']['slots'])
    return dict(samples=27,physical_groups=len({s.group_id for s in samples}),core_fpr_negatives=18,
                preference_positive_controls=7,optional_search_controls=1,observable_fact_controls=1,
                original_test_groups_reused=False,distribution={t:dict(samples=3,groups=2,core_fpr_negatives=2) for t in TEMPLATES})
