"""Dev v3: compress execution history without changing actions or goal facts.

The prior v2 append-only payload remains intact in its own modules/records.
All user questions/answers, the latest action and aggregate action evidence remain.
Full input is saved by the runner; no oracle or private task is consulted here.
"""
import copy
from dataclasses import dataclass

from .buffer_public_dev import augment
from .buffer_planner_dev import Profile

VERSION='buffer_compact_context_dev_v3'


def compact(public):
    augmented=augment(public);summary=augmented['public_summary'];obs=public['observation']
    last_action=max((i for i,e in enumerate(public['history']) if e.get('kind')=='action'),default=-1)
    retained=[copy.deepcopy(e) for i,e in enumerate(public['history']) if e.get('kind')!='action' or i==last_action]
    # Keep current physical geometry and ALL schema-supported affordances.
    # Velocities and orientations are not needed to choose a region; the skill
    # controller still receives/uses the full real physical world unchanged.
    observation={key:copy.deepcopy(value) for key,value in obs.items() if key!='objects'}
    observation['objects']={key:{k:copy.deepcopy(v) for k,v in obj.items()
        if k in ('category','color','position','aabb_min','aabb_max')}
        for key,obj in obs['objects'].items()}
    results=summary.pop('chronological_action_results')
    summary.update(version=VERSION,execution_history_coverage=dict(total_actions=len(results),
        successful_actions=sum(r['success'] is True for r in results),failed_actions=sum(r['success'] is False for r in results),
        latest_result=results[-1] if results else None,
        note='Earlier physical actions are aggregated, not repeated as a long action pattern. All user dialogue is retained; full original public input is saved in the trace.'),
        confirmed_dialogue_preserved=True)
    # Put the measured current state after the small chronological history.
    return dict(instruction=public['instruction'],history=retained,
                observation=observation,public_summary=summary)


@dataclass(frozen=True)
class CompactProfile(Profile):
    @property
    def name(self):return super().name+'c1'
    def serialize(self,public):return compact(public)
