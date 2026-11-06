"""Human-facing episode review. Hidden truth is released only after termination."""
import copy

from .navigation_map import LOCATIONS

TERMINAL=('done','error','cancelled')


def interaction_status(task):
    nav=task.template=='find_and_approach'
    missing=[]
    if task.observation:
        if nav:
            from .navigation_protocol import location_claim
            if not location_claim(task.sample.u0,task.history) and not task.observation.get('target_observation'):
                missing=['target_location']
        else:
            from .task import PublicState
            from .study_protocol import disclosed_choices,public_roles
            state=PublicState.build(task.observation,task.history,task.sample.u0)
            missing=sorted(set(public_roles(state))-set(disclosed_choices(state)))
    if task.method.endswith('noask'):
        reason='NoAsk 按定义不提问；不会出现回答表单。'
    elif task.status=='waiting_answer' and task.pending:
        reason='模型已发出 ASK；请在右侧队列输入回答，或选择候选对象。' if task.answer_mode=='manual' else '模型已发出 ASK；自动用户模拟器正在回答。'
    elif task.status in TERMINAL:
        reason=('任务已结束，完整问答和最终真值可在详情查看。' if any('question' in t for t in task.turns)
                else '本次模型没有发出 ASK，因此没有出现回答表单。')
    elif task.answer_mode=='manual':
        reason='Human 模式已启用；等待模型真正发出 ASK 后才显示回答表单。'
    else:reason='Auto 模式：仅在模型发出 ASK 时自动回答。'
    gate=task.gate or {}
    if gate.get('backend')=='jev' and isinstance(gate.get('p_ask'),(int,float)):
        reason+=f" 最近 Jev p(ASK)={gate['p_ask']:.2f}，阈值={task.audit.config.threshold:g}，决策={gate['decision']}。"
    if missing and task.status in TERMINAL and not nav:
        reason+=' 结束时仍有未公开偏好，执行可能使用了猜测；成功与否由真实物理结果评分。'
    return dict(message=reason,missing_roles=missing,manual_form_available=task.status=='waiting_answer' and task.answer_mode=='manual',
        ask_turns=sum('question' in t for t in task.turns),threshold=task.audit.config.threshold)


def conversation(task):
    events=[]
    for turn in task.turns:
        step=turn.get('public_payload',{}).get('observation',{}).get('simulation_step')
        def add(kind,**value):events.append(dict(kind=kind,round=turn['round'],simulation_step=step,**value))
        if turn.get('gate'):add('gate',value=copy.deepcopy(turn['gate']))
        if turn.get('question'):add('question',value=copy.deepcopy(turn['question']),question_id=turn.get('question_id'))
        if turn.get('user_answer'):
            submitted=task.answers.get(turn.get('question_id'),{})
            add('user_answer',value=copy.deepcopy(turn['user_answer']),source=turn.get('answer_source'),input_text=submitted.get('input_text'))
        if turn.get('action'):add('action',value=copy.deepcopy(turn['action']))
        if turn.get('physical_result'):
            result=copy.deepcopy(turn['physical_result']);add('physical_result',value=result)
            events[-1]['simulation_step']=result.get('end_step',step)
    return events


def ground_truth(task):
    if task.status not in TERMINAL:return None
    names=(task.frame or {}).get('object_names',{})
    if task.template=='find_and_approach':
        location=task.sample.target_location
        return dict(protocol='fixed_world_location',meaning='固定世界事实；人工位置提示不会移动目标或改变评分目标。',
            initial=[dict(role='target_location',object_id=location,label=LOCATIONS[location]['name'])],
            evaluated=[dict(role='target_location',object_id=location,label=LOCATIONS[location]['name'])],manual_changes=[])
    initial=task.sample.theta_star;effective={**initial,**task.goal_overrides}
    def rows(values):
        return [dict(role=task.sample.slots[k]['public_role'],object_id=v,label=names.get(v,v)) for k,v in values.items()]
    return dict(protocol='interactive_declared_preferences' if task.answer_mode=='manual' else 'fixed_demo_preferences',
        meaning='预置隐藏偏好与本次实际评分目标分别显示。人工对未公开偏好的回答定义本次交互目标。' if task.answer_mode=='manual' else '自动用户按预置隐藏偏好回答；评分目标固定。',
        initial=rows(initial),evaluated=rows(effective),
        manual_changes=[dict(role=task.sample.slots[k]['public_role'],before=names.get(initial[k],initial[k]),after=names.get(v,v))
                        for k,v in task.goal_overrides.items() if initial[k]!=v])


def review(task):
    return dict(original_instruction=task.sample.u0,instruction_origin='generated_task_instruction',
        interaction=interaction_status(task),conversation=conversation(task),ground_truth=ground_truth(task),
        truth_revealed=task.status in TERMINAL,
        engine=dict(tabletop='shared_task_contract_v3.1',navigation='navigation_search_dev_v1',
            notice='当前交互控制台保留基础策略；Navigation Dev v2 是独立研究实验，未自动替换。'))
