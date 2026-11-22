"""Optional Dev v7 selected by the preregistered eight-state diagnostic rule.

Only the Gate view changes; all methods use the unchanged v6 shared planner.
"""
from .gate_contract_dev import Gate,GateProfile
from .memory_dev_agents import Planner,prompt_hashes as planner_hashes

PROFILE='gate_dev_v7'
SUPPORTED=('buffer_exchange','retrieve_restore','occlusion_inspection')
SELECTED=GateProfile(compact_state=True,explicit_contract=False)


def prompt_hashes():return {**planner_hashes(),**SELECTED.hashes()}


def configuration():return dict(profile=PROFILE,gate_view='compact_public',gate_contract='unchanged_v6',threshold_policy='unchanged_configured_threshold',
    selected_factor_profile=SELECTED.name,shared_planner='unchanged_memory_dev_v6',selection_evidence='result/gate_diagnostics_dev_v7/selection.json')


def components(method,deepseek,jev,threshold):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',threshold,SELECTED)),Planner(deepseek)
