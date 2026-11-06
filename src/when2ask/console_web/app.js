// One source of truth: decoded worker frames + their versioned task packets.
// Timers update elapsed labels and health only; never robot stages or decisions.
const $=s=>document.querySelector(s);
const tasks=new Map(),views=new Map(),groups=new Map(),incoming=new Map(),queueViews=new Map();
const archived=new Set(JSON.parse(sessionStorage.getItem('when2ask-hidden-tasks')||'[]'));
const terminal=new Set(['done','error','cancelled']);
const methods={llm_noask:'LLM-NoAsk',llm_gate:'LLM-Gate',jev_gate:'Jev-Gate',scripted_ask:'Scripted ASK',scripted_noask:'Scripted NoAsk'};
const statusNames={queued:'排队中',initializing:'初始化物理世界',gate:'Gate 决策中',planning_question:'生成澄清问题',waiting_answer:'ASK · 等待回答',answer_received:'已收到回答',planning_action:'规划下一步',dispatching:'动作已发送',executing:'机器人执行中',finalizing:'独立物理评分中',cancelling:'正在结束',cancelled:'已结束',done:'执行完成',error:'执行 / API 错误'};
const roleNames={target_location:'Knife location / 刀具位置',cup:'Cup / 杯子',block:'Block / 方块',lid:'Lid / 盖子',cup_destination:'Cup destination / 目标容器'};
let meta,mode='wall',selectedId=null,selectedGroup=null,selectedQuestion=null,inspectorSignature='',comparisonBusy=false,snapshotEpoch=0;
const requestKeys=new Map();
const routeGroup=new URLSearchParams(location.search).get('comparison');
const drafts=new Map(JSON.parse(sessionStorage.getItem('when2ask-answer-drafts')||'[]'));
function saveDrafts(){sessionStorage.setItem('when2ask-answer-drafts',JSON.stringify([...drafts]));}
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
function notice(text=''){$('#notice').hidden=!text;$('#notice').textContent=text;}
async function api(url,body){const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const value=await r.json();if(!r.ok)throw Error(value.error||'HTTP '+r.status);return value;}
function seconds(n){return n==null?'—':(n/1000).toFixed(2)+' s';}
function tokenPair(cost,backend){const b=cost?.[backend];return !b||!b.attempts?'—':(b.input_tokens??'?')+' / '+(b.output_tokens??'?');}
function sceneOptions(){const o={template:$('#template').value,unknown_preferences:Number($('#unknown').value)};if(o.template==='find_and_approach')o.navigation_case=$('#navigation-case').value;return o;}
function sceneChanged(){const nav=$('#template').value==='find_and_approach';$('#navigation-case-field').hidden=!nav;$('#launch').classList.toggle('navigation-launch',nav);$('#unknown-label').textContent=nav?'UNKNOWN LOCATION FACTS':'UNKNOWN PREFERENCES';for(const o of $('#unknown').options)o.disabled=nav&&Number(o.value)>1;if(nav&&Number($('#unknown').value)>1)$('#unknown').value='1';methodNote();}
$('#template').onchange=sceneChanged;
function methodNote(){const m=$('#method').value;$('#answer-mode').disabled=m.endsWith('noask');$('#method-note').textContent=m.startsWith('scripted')?'Scripted 是规则策略 · 真实物理 · 不调用模型 API。':m==='llm_noask'?'NoAsk 跳过 Gate · DeepSeek 根据公开信息生成动作。':'真实 API 决策 · 手动 ASK 只暂停当前任务。';}
$('#method').onchange=methodNote;
async function launch(url,options){const signature=url+JSON.stringify(options),key=requestKeys.get(signature)||crypto.randomUUID();requestKeys.set(signature,key);try{const result=await api(url,{options,request_id:key});requestKeys.delete(signature);return result;}finally{refreshMeta();}}
$('#launch').onsubmit=async e=>{e.preventDefault();notice();$('#start').disabled=true;try{const t=await launch('/api/tasks',{...sceneOptions(),method:$('#method').value,answer_mode:$('#answer-mode').disabled?'auto':$('#answer-mode').value});await receive(t);selectedId=t.id;setMode('wall');}catch(e){notice(e.message);}finally{$('#start').disabled=false;}};
$('#compare-start').onclick=async()=>{if(comparisonBusy)return;comparisonBusy=true;$('#compare-start').disabled=true;notice();try{const g=await launch('/api/comparisons',sceneOptions());receiveGroup(g);selectComparison(g.id);}catch(e){notice(e.message);}finally{comparisonBusy=false;refreshMeta();}};
function setMode(value){mode=value;history.replaceState(null,'',location.pathname+(mode==='compare'&&selectedGroup?'?comparison='+selectedGroup:''));$('#wall-tab').classList.toggle('active',mode==='wall');$('#compare-tab').classList.toggle('active',mode==='compare');$('#nav-wall').classList.toggle('active',mode==='wall');$('#nav-compare').classList.toggle('active',mode==='compare');$('#comparison-toolbar').hidden=mode!=='compare'||!selectedGroup;$('#comparison-panel').hidden=mode!=='compare'||!selectedGroup;$('#tasks').classList.toggle('comparing',mode==='compare');renderVisibility();renderComparison();renderInspector();}
$('#wall-tab').onclick=$('#nav-wall').onclick=$('#show-all').onclick=()=>setMode('wall');
$('#compare-tab').onclick=$('#nav-compare').onclick=()=>{if(!selectedGroup&&groups.size)selectComparison([...groups.keys()].at(-1));else if(!groups.size)notice('先点击“一键三方法对比”，创建同一场景的三个真实 API 任务。');else setMode('compare');};
$('#nav-queue').onclick=()=>{document.querySelector('.clarification-panel').scrollIntoView({behavior:'smooth',block:'start'});$('#answer-desk select')?.focus({preventScroll:true});};
$('#restore').onclick=()=>{archived.clear();sessionStorage.setItem('when2ask-hidden-tasks','[]');renderVisibility();};
$('#comparison-select').onchange=e=>selectComparison(e.target.value);
function selectComparison(id){if(!groups.has(id))return;selectedGroup=id;$('#comparison-select').value=id;const group=groups.get(id);if(!group.task_ids.includes(selectedId))selectedId=group.task_ids[0];setMode('compare');}
function selectTask(id){selectedId=id;const g=groups.get(selectedGroup);if(mode==='compare'&&!g?.task_ids.includes(id))setMode('wall');for(const [key,c]of views)c.classList.toggle('selected',key===id);renderInspector();}
function makeCard(t){const c=node('article','card');c.dataset.taskId=t.id;c.dataset.method=t.method;c.tabIndex=0;c.setAttribute('aria-label',methods[t.method]+' task '+t.id.slice(0,8));
 c.innerHTML='<div class="card-head"><div class="card-title"><span class="badge"></span><h3></h3><span class="task-id"></span></div><button class="stop" type="button">结束任务</button></div><div class="viewport"><span class="placeholder">等待执行器实时画面…</span><img alt="实时 PyBullet 机器人全景"><span class="camera-live">PYBULLET / PANORAMIC</span><span class="frame-label"></span></div><div class="card-body"><div class="status-line"><span class="status"></span><span class="decision"></span></div><div class="physical"></div><div class="card-metrics"><div><strong class="actions">0</strong><small>ROBOT ACTIONS</small></div><div><strong class="burden">0</strong><small>SLOT BURDEN</small></div><div><strong class="latency">—</strong><small>API SECONDS</small></div></div><button class="question-link" hidden>前往澄清队列 →</button><div class="evaluation-slot"></div><div class="error-slot"></div><a class="log-link" target="_blank" rel="noopener">Episode JSON ↗</a></div>';
 c.querySelector('.stop').onclick=()=>{const current=tasks.get(t.id);if(terminal.has(current.status)){archived.add(t.id);sessionStorage.setItem('when2ask-hidden-tasks',JSON.stringify([...archived]));renderVisibility();}else api('/api/tasks/'+t.id+'/cancel',{}).catch(e=>notice(e.message));};
 c.querySelector('.log-link').href='/api/tasks/'+t.id+'/episode';
 c.querySelector('.question-link').onclick=()=>chooseQuestion(tasks.get(t.id)?.question?.id,true);
 c.querySelector('.viewport').onclick=()=>{selectTask(t.id);const current=tasks.get(t.id);$('#focus').dataset.taskId=t.id;$('#focus-title').textContent=methods[current.method]+' · Task '+t.id.slice(0,8);$('#focus-image').src=c.querySelector('img').src;$('#focus-meta').textContent=c.querySelector('.frame-label').textContent;$('#focus').showModal();};
 c.onclick=e=>{if(!e.target.closest('button,a,.viewport'))selectTask(t.id);};c.onkeydown=e=>{if(e.key==='Enter'&&e.target===c)selectTask(t.id);};
 $('#tasks').prepend(c);views.set(t.id,c);return c;
}
function paint(t,image){const c=views.get(t.id)||makeCard(t),f=t.frame,failed=terminal.has(t.status)&&t.evaluation&&!t.evaluation.task_success;
 c.classList.toggle('navigation-task',t.template==='find_and_approach');c.dataset.version=t.version;c.dataset.status=t.status;c.classList.toggle('waiting',t.status==='waiting_answer');c.classList.toggle('done',terminal.has(t.status)&&t.evaluation?.task_success===true);c.classList.toggle('error',t.status==='error'||failed);c.classList.toggle('selected',t.id===selectedId);
 c.querySelector('h3').textContent=t.template_name;c.querySelector('.task-id').textContent=methods[t.method]+' · '+t.id.slice(0,8)+' · '+t.unknown_preferences+' unknown';
 const badge=c.querySelector('.badge');badge.textContent=t.method.startsWith('scripted')?'SCRIPTED / REAL PHYSICS':t.method==='jev_gate'?'LIVE JEV + DEEPSEEK':'LIVE DEEPSEEK';badge.classList.toggle('scripted',t.method.startsWith('scripted'));
 c.querySelector('.status').textContent=failed?'执行结束 · 任务未成功':statusNames[t.status]||t.status;
 const g=t.gate,currentGate=g&&g.round===t.round;c.querySelector('.decision').textContent=!g?'—':!g.called?'NO GATE':!currentGate?'GATE RUNNING':(typeof g.p_ask==='number'?'p='+g.p_ask.toFixed(2)+' · ':'')+g.decision;
 if(f){const img=c.querySelector('img');if(image)img.src=image.src;img.dataset.frameSeq=f.seq;img.dataset.simulationStep=f.simulation_step;img.dataset.sha256=f.sha256;c.dataset.frameStep=f.simulation_step;c.dataset.physicalPhase=f.phase||'';c.querySelector('.placeholder').hidden=true;c.querySelector('.frame-label').textContent='Step '+f.simulation_step.toLocaleString()+' / Frame '+f.seq;
 const a=f.action,n=f.object_names;c.querySelector('.physical').textContent=a?.kind==='search'?'Search → '+(n[a.location_id]||a.location_id)+' · '+(f.phase||'idle'):a?a.kind+'('+ (n[a.object_id]||a.object_id)+', '+(n[a.target_id]||a.target_id)+')'+(f.phase?' · '+f.phase:''):'物理场景已就绪';if(f.navigation){const v=f.navigation;c.querySelector('.physical').textContent+=' | '+v.distance_m.toFixed(2)+'m · inspected '+v.checked+'/6 · '+v.current_room+(v.locally_detected?' · TARGET SEEN':' · LOCAL SENSING');}}
 c.querySelector('.actions').textContent=t.actions.length;c.querySelector('.burden').textContent=t.burden;c.querySelector('.latency').textContent=t.cost.api_latency_ms==null?'—':(t.cost.api_latency_ms/1000).toFixed(2);
 c.querySelector('.stop').textContent=terminal.has(t.status)?'收起':'结束';c.querySelector('.log-link').hidden=!terminal.has(t.status);c.querySelector('.question-link').hidden=!t.question||t.status!=='waiting_answer';
 const slot=c.querySelector('.evaluation-slot');slot.replaceChildren();if(t.evaluation){const count=Object.values(t.evaluation.conditions||{}).filter(Boolean).length;slot.append(node('div','evaluation'+(t.evaluation.task_success?'':' fail'),(t.evaluation.task_success?'✓ SUCCESS':'× TASK UNSUCCESSFUL')+' · '+count+'/'+Object.keys(t.evaluation.conditions||{}).length+' physical conditions'));}
 const error=c.querySelector('.error-slot');error.replaceChildren();if(t.error)error.append(node('div','error-text',t.error));
 if($('#focus').open&&$('#focus').dataset.taskId===t.id){$('#focus-image').src=c.querySelector('img').src;$('#focus-meta').textContent=c.querySelector('.frame-label').textContent;}
}
async function receive(t){const epoch=snapshotEpoch;if((incoming.get(t.id)??-1)>=t.version)return;incoming.set(t.id,t.version);let image;const c=views.get(t.id);
 if(t.frame&&c?.querySelector('img').dataset.sha256!==t.frame.sha256){image=new Image();image.src='data:image/jpeg;base64,'+t.frame.jpeg;try{await image.decode();}catch(e){notice('执行器画面解码失败');return;}}
 if(epoch!==snapshotEpoch||incoming.get(t.id)!==t.version)return;const previous=tasks.get(t.id);tasks.set(t.id,t);if(!selectedId)selectedId=t.id;paint(t,image);renderVisibility();renderStats();renderQueue();renderInspector();renderComparison();if(terminal.has(t.status)&&!terminal.has(previous?.status))refreshMeta();
}
function renderVisibility(){let visible=0;for(const [id,c]of views){const inGroup=mode!=='compare'||!selectedGroup||groups.get(selectedGroup)?.task_ids.includes(id);c.hidden=archived.has(id)||!inGroup;if(!c.hidden)visible++;c.classList.toggle('selected',id===selectedId);}$('#task-count').textContent=tasks.size;$('#restore').hidden=!archived.size;if(tasks.size)$('#empty')?.remove();if(visible&&selectedId&&views.get(selectedId)?.hidden){selectedId=[...views.keys()].find(id=>!views.get(id).hidden);inspectorSignature='';renderInspector();}}
function renderStats(){const all=[...tasks.values()],scored=all.filter(t=>terminal.has(t.status)&&t.evaluation);$('#active-count').textContent=all.filter(t=>t.worker_id&&!terminal.has(t.status)).length;$('#waiting-count').textContent=all.filter(t=>t.status==='waiting_answer'&&t.question).length;$('#score-count').textContent=scored.length?scored.filter(t=>t.evaluation.task_success).length+' / '+scored.length:'—';$('#capacity-label').textContent='并发上限 '+(meta?.concurrency??3)+' · '+all.filter(t=>t.status==='queued').length+' 排队中';}
function receiveGroup(g){groups.set(g.id,g);$('#comparison-count').textContent=groups.size;const select=$('#comparison-select');if(![...select.options].some(o=>o.value===g.id))select.add(new Option(g.id.slice(0,8)+' · '+g.options.unknown_preferences+' unknown',g.id));if(!selectedGroup&&routeGroup===g.id)selectComparison(g.id);if(selectedGroup===g.id)renderComparison();if(g.status==='complete')refreshMeta();}
function renderComparison(){const g=groups.get(selectedGroup);if(!g)return;$('#comparison-select').value=g.id;$('#comparison-description').textContent=g.source_sample_id+' · '+g.options.unknown_preferences+' unknown · independent resets · AUTO responses';
 const tbody=$('#comparison-rows');tbody.replaceChildren();let complete=true;
 for(const id of g.task_ids){const t=tasks.get(id),fallback=g.rows.find(r=>r.task_id===id);const tr=node('tr');tr.dataset.taskId=id;tr.dataset.method=t?.method||fallback.method;const score=t?.evaluation?.task_success??null;const done=t?terminal.has(t.status):false;complete&&=done;
 const cost=t?.cost||fallback.cost;const values=[methods[t?.method||fallback.method],score===true?'Success':score===false?'Failed':done?'Not scored':'Running',t?.burden??fallback.burden,t?.ask_turns??fallback.ask_turns,t?.actions.length??fallback.robot_actions,t?.frame?.navigation?.distance_m!=null?t.frame.navigation.distance_m.toFixed(2)+' m':fallback.distance_m!=null?fallback.distance_m.toFixed(2)+' m':'—',t?.frame?.navigation?.checked??fallback.checked_locations??'—',seconds(cost.api_latency_ms),t?.timing?seconds(t.timing.wall_time_s*1000):'—',tokenPair(cost,'deepseek'),tokenPair(cost,'jev')];
 values.forEach((v,i)=>tr.append(node('td',i===1?(score===true?'success-text':score===false?'failure-text':'pending-text'):'',v)));tbody.append(tr);}
 $('#comparison-json').href='/api/comparisons/'+g.id;$('#comparison-csv').href='/api/comparisons/'+g.id+'/csv';$('#comparison-csv').setAttribute('aria-disabled',String(!complete));
}
function pendingTasks(){return [...tasks.values()].filter(t=>t.status==='waiting_answer'&&t.question).sort((a,b)=>a.question.created-b.question.created);}
function chooseQuestion(qid,scroll=false){if(!qid)return;selectedQuestion=qid;renderQueue();const t=pendingTasks().find(t=>t.question.id===qid);if(t)selectTask(t.id);if(scroll)document.querySelector('.clarification-panel').scrollIntoView({behavior:'smooth',block:'start'});}
function renderQueue(){const pending=pendingTasks(),qids=new Set(pending.map(t=>t.question.id));if(!qids.has(selectedQuestion))selectedQuestion=pending[0]?.question.id??null;
 $('#queue-count').textContent=pending.length;$('#queue-empty').hidden=pending.length>0;
 for(const [id,e]of queueViews)if(!qids.has(id)){e.remove();queueViews.delete(id);}
 for(const t of pending){const q=t.question;let button=queueViews.get(q.id);if(!button){button=node('button','queue-item');button.type='button';button.dataset.questionId=q.id;button.dataset.taskId=t.id;button.append(node('strong','',methods[t.method]+' · '+t.id.slice(0,8)),node('span','',q.requests.length+' information slots · Step '+q.simulation_step));button.onclick=()=>chooseQuestion(q.id);queueViews.set(q.id,button);$('#queue-list').append(button);}button.classList.toggle('active',q.id===selectedQuestion);}
 const t=pending.find(t=>t.question.id===selectedQuestion);const desk=$('#answer-desk');if(!t){desk.replaceChildren();delete desk.dataset.questionId;delete desk.dataset.taskId;return;}
 if(desk.dataset.questionId===selectedQuestion)return;desk.replaceChildren();desk.dataset.questionId=selectedQuestion;desk.dataset.taskId=t.id;
 const q=t.question,box=node('div','question');box.dataset.questionId=q.id;box.dataset.taskId=t.id;box.append(node('h3','',methods[t.method]+' / TASK '+t.id.slice(0,8)),node('p','',q.text));
 const fields=node('div','answer-fields');
 for(const r of q.requests){const label=node('label','',roleNames[r.role]||r.role),select=node('select');select.dataset.role=r.role;
 if(q.type==='confirm'){select.dataset.candidateId=r.candidate_id;select.add(new Option('Yes · '+q.candidates[r.candidate_id],'true'));select.add(new Option('No · use the other candidate','false'));}
 else for(const id of r.candidate_ids)select.add(new Option(q.candidates[id]||id,id));
 if(drafts.get(q.id)?.[r.role]&&[...select.options].some(o=>o.value===drafts.get(q.id)[r.role]))select.value=drafts.get(q.id)[r.role];
 select.onchange=()=>{drafts.set(q.id,{...(drafts.get(q.id)||{}),[r.role]:select.value});saveDrafts();};
 if(q.known_choices?.[r.role]){select.value=q.type==='confirm'?String(q.known_choices[r.role]===r.candidate_id):q.known_choices[r.role];select.disabled=true;}
 label.append(select);fields.append(label);}
 box.append(fields);const buttons=node('div','answer-buttons'),send=node('button','','提交我的回答'),auto=node('button','secondary','自动回答本次');send.type=auto.type='button';buttons.append(send,auto);box.append(buttons,node('div','frozen-note','Ⅱ Physics frozen at step '+q.simulation_step),node('div','question-id','Question '+q.id+' · '+(q.requested_slot_count??q.requests.length)+' distinct slots'));
 if(t.answer_mode!=='manual'){send.disabled=auto.disabled=true;box.append(node('p','muted','自动模拟器处理中…'));}
 const submit=async source=>{send.disabled=auto.disabled=true;let response;if(source==='human'){const values=[...fields.querySelectorAll('select')];response=q.type==='confirm'?{confirmations:values.map(s=>({role:s.dataset.role,candidate_id:s.dataset.candidateId,confirmed:s.value==='true'}))}:{choices:Object.fromEntries(values.map(s=>[s.dataset.role,s.value]))};}try{await api('/api/tasks/'+t.id+'/answer',{question_id:q.id,source,response});drafts.delete(q.id);saveDrafts();}catch(e){notice(e.message);if(desk.dataset.questionId===q.id)send.disabled=auto.disabled=false;}};
 send.onclick=()=>submit('human');auto.onclick=()=>submit('auto');desk.append(box);
}
function traceText(t,e){const n=t.frame?.object_names||{};switch(e.kind){case 'gate_decision':return e.gate.called?(typeof e.gate.p_ask==='number'?'Jev p='+e.gate.p_ask.toFixed(2)+' → ':'Gate → ')+e.gate.decision:'NoAsk → shared planner';case 'question':return 'ASK · '+e.text;case 'answer_received':return (e.source==='human'?'Human':'Simulator')+' answer received';case 'planned_action':return e.action.kind==='DONE'?'Planner → DONE':e.action.kind+'('+ (n[e.action.location_id||e.action.object_id]||e.action.location_id||e.action.object_id)+')';case 'physical_phase':return 'PyBullet · '+(e.phase||'execution');case 'action_result':return e.result.skill+' → '+(e.result.success?'succeeded':'failed');case 'status':return statusNames[e.status]||e.status;case 'initializing':return 'Worker claimed independent world';default:return e.kind;}}
function renderInspector(){const t=tasks.get(selectedId);if(!t)return;$('#inspector').hidden=false;
 $('#inspector-round').textContent='ROUND '+(t.round+1)+' / STEP '+(t.frame?.simulation_step??'—');
 const sig=t.id+'|'+t.status+'|'+t.round+'|'+(t.trace.at(-1)?.seq??0);if(sig===inspectorSignature)return;inspectorSignature=sig;
 $('#inspector-title').textContent=methods[t.method]+' · '+t.id.slice(0,8);
 let stage=['queued','initializing'].includes(t.status)?'observe':t.status==='gate'?'gate':['planning_question','waiting_answer','answer_received'].includes(t.status)?'ask':t.status==='planning_action'?'plan':['dispatching','executing'].includes(t.status)?'execute':'evaluate';
 const f=$('#flow');f.replaceChildren();for(const [key,label]of [['observe','Observe ↻'],['gate','Gate'],['ask','ASK → User'],['plan','Action plan'],['execute','Execute ↻'],['evaluate','Evaluate']]){const e=node('div','flow-node'+(key==='ask'?' ask':'')+(key==='evaluate'&&t.evaluation?.task_success===true?' complete':'')+(key==='evaluate'&&t.evaluation?.task_success===false?' failed':'')+(stage===key?' active':'')+((t.method.endsWith('noask')&&(key==='gate'||key==='ask'))?' skipped':''),label);e.dataset.node=key;e.setAttribute('aria-current',stage===key?'step':'false');f.append(e);}
 const g=t.gate,valid=g?.round===t.round;$('#gate-decision').textContent=t.status==='gate'&&!valid?'RUNNING':g?.called?g.decision:g?'SKIPPED':'PENDING';
 const hasP=valid&&g?.backend==='jev'&&typeof g.p_ask==='number';$('#probability').hidden=!hasP;if(hasP){$('#p-value').textContent=g.p_ask.toFixed(2);$('#p-meter').value=g.p_ask;$('#threshold-label').textContent='ASK when p ≥ '+(meta?.models.jev_threshold??0.5);}
 $('#gate-description').textContent=t.method.startsWith('scripted')?'Scripted 规则策略；动作由真实 PyBullet 执行。':t.method==='llm_noask'?'NoAsk 跳过 Gate，直接调用共享 DeepSeek Planner。':t.status==='waiting_answer'?(t.template==='find_and_approach'?'等待位置提示；真实目标不移动，物理世界保持静止。':'正在等待偏好回答；当前世界保持静止。'):'Gate 基于公开指令、物理观察和历史决定是否需要澄清。';
 const last=[...t.history].reverse().find(h=>h.kind==='user_answer');$('#inspector-answer').textContent=last?(last.source==='human'?'HUMAN':'AUTO')+' · '+(last.response.choices?Object.entries(last.response.choices).map(([r,id])=>r+': '+(t.frame?.object_names[id]||id)).join(' · '):'Confirmation recorded'):'';
 const list=$('#trace-list');list.replaceChildren();for(const e of t.trace.slice(-8).reverse()){const li=node('li',e.kind==='question'?'ask-event':'');li.append(node('time','',(e.elapsed_ms/1000).toFixed(1)+'s'),node('span','',traceText(t,e)));list.append(li);}
}
$('#focus-close').onclick=()=>$('#focus').close();
async function refreshMeta(){try{meta=await api('/api/meta');$('#worker-info').textContent='WORKER '+meta.workers.length+' · CAPACITY '+meta.concurrency;const b=meta.budget;$('#api-count').textContent=b.attempts+' / '+b.max_attempts;$('#budget').textContent=b.episodes+' / '+b.max_episodes+' live episodes';$('#budget-meter').value=b.attempts;$('#budget-meter').max=b.max_attempts;for(const o of $('#method').options)if(!o.value.startsWith('scripted'))o.disabled=!meta.live_enabled;
 const can=meta.live_enabled&&b.max_episodes-b.episodes>=3&&b.attempts<b.max_attempts;$('#compare-start').disabled=comparisonBusy||!can;$('#compare-start').title=can?'创建三个独立真实 API 任务，固定自动回答':'需要开启 --live 且剩余至少三个 live episode 名额';renderStats();}catch(e){notice(e.message);}}
const stream=new EventSource('/api/events');
stream.onopen=()=>{$('#connection').textContent='● 实时已连接';$('#connection').classList.remove('off');};
stream.onerror=()=>{$('#connection').textContent='正在重连';$('#connection').classList.add('off');};
stream.onmessage=e=>{
 const event=JSON.parse(e.data);
 if(event.type==='snapshot'){
  snapshotEpoch++;const ids=new Set(event.tasks.map(t=>t.id)),cids=new Set((event.comparisons||[]).map(g=>g.id));
  for(const id of tasks.keys())if(!ids.has(id)){tasks.delete(id);views.get(id)?.remove();views.delete(id);archived.delete(id);}
  for(const id of groups.keys())if(!cids.has(id))groups.delete(id);
  for(const o of [...$('#comparison-select').options])if(!cids.has(o.value))o.remove();
  incoming.clear();for(const t of tasks.values())incoming.set(t.id,t.version);
  if(!ids.has(selectedId)){selectedId=null;inspectorSignature='';$('#inspector').hidden=true;}
  if(selectedGroup&&!cids.has(selectedGroup)){selectedGroup=null;setMode('wall');}
  (event.comparisons||[]).forEach(receiveGroup);event.tasks.forEach(receive);
  renderStats();renderQueue();renderVisibility();$('#comparison-count').textContent=groups.size;
 }else if(event.type==='task'){
  receive(event.task);
  if(event.task.comparison_id&&!groups.has(event.task.comparison_id))api('/api/comparisons/'+event.task.comparison_id).then(receiveGroup).catch(e=>notice(e.message));
 }else if(event.type==='comparison')receiveGroup(event.comparison);
};
const requestedTemplate=new URLSearchParams(location.search).get('template');if([...$('#template').options].some(o=>o.value===requestedTemplate))$('#template').value=requestedTemplate;
sceneChanged();refreshMeta();setInterval(refreshMeta,5000);
window.consoleView={tasks,groups,getCard:id=>views.get(id),refreshMeta,selectTask,selectComparison,chooseQuestion};
