"""Conservative text-to-candidate grounding; public choices only, no model/API."""
import re

COLORS={
    'blue':['blue','蓝'],'red':['red','红'],'green':['green','绿'],'yellow':['yellow','黄'],
    'black':['black','黑'],'white':['white','白'],'cyan':['cyan','青','蓝绿'],
    'magenta':['magenta','洋红','紫红'],'orange':['orange','橙'],'purple':['purple','紫'],
    'grey':['grey','gray','灰'],'gray':['gray','grey','灰']}
LOCATION_NAMES={
    'kitchen_counter':['kitchen counter','厨房台面','厨房柜台','厨房的柜台','厨房的台面'],
    'kitchen_shelf':['kitchen shelf','厨房架子','厨房的架子','厨房置物架'],
    'living_cabinet':['living room cabinet','客厅柜子','客厅的柜子','客厅柜台'],
    'living_table':['living room table','客厅桌子','客厅的桌子','客厅茶几'],
    'study_desk':['study desk','书房桌子','书房的桌子','书房书桌','书房的书桌'],
    'study_shelf':['study shelf','书房架子','书房的架子','书房书架','书房的书架']}


def contains(text,term):
    if re.fullmatch(r'[a-z_0-9 ]+',term):return re.search(r'(?<![a-z0-9_])'+re.escape(term)+r'(?![a-z0-9_])',text) is not None
    return term in text


def text_answer(pending,text):
    if not isinstance(text,str) or not 1<=len(text.strip())<=1000:raise ValueError('请输入 1–1000 字的回答，或使用下方候选选择。')
    text=text.strip().lower();requests=pending['requests'];names=pending['candidates']
    if pending['type']=='confirm':
        if len(requests)!=1:raise ValueError('多项确认请使用候选选择逐项回答。')
        yes=text in ('yes','是','对','确认','是的','对的');no=text in ('no','否','不对','不是','不是的')
        if not yes and not no:raise ValueError('请明确回答 yes/是 或 no/否，或使用候选选择。')
        r=requests[0];return dict(confirmations=[dict(role=r['role'],candidate_id=r['candidate_id'],confirmed=yes)])
    choices={}
    for request in requests:
        candidates=request['candidate_ids']
        exact=[key for key in candidates if contains(text,key.lower()) or contains(text,names.get(key,key).lower())]
        if not exact:
            if request['role']=='target_location':
                exact=[key for key in candidates if any(contains(text,t) for t in LOCATION_NAMES.get(key,[]))]
            else:
                exact=[key for key in candidates if any(contains(text,t) for t in COLORS.get(names.get(key,'').split(' ')[0].lower(),[]))]
        if len(exact)!=1:raise ValueError(f"无法唯一确定 {request['role']}：请写清候选名称、颜色或 ID，也可使用下方选择。")
        choices[request['role']]=exact[0]
    return dict(choices=choices)
