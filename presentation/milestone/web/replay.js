// One master display clock. Robot pixels and flow state commit in one render.
const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
const stage=$('stage'),canvas=$('robot-frame'),ctx=canvas.getContext('2d',{alpha:false});
if(params.has('presentation')||params.has('export'))stage.classList.add('presentation');
const highlight=params.get('view')==='highlight';
function resize(){const s=Math.min(innerWidth/1920,innerHeight/1080);stage.style.transform=`scale(${s})`;stage.style.left=`${(innerWidth-1920*s)/2}px`;stage.style.top=`${(innerHeight-1080*s)/2}px`;}
addEventListener('resize',resize);resize();
let manifest,episode,frame,playbackFrames=[],playbackDuration=0,time=0,speed=1,playing=false,anchorWall=0,anchorSource=0,renderSerial=0,raf;
const cache=new Map();
const phaseNames=['approach','grasp','lift','transport','lower','release','settle'];
const stageNames={gate_result:'Gate decision',question:'Clarification',user_answer:'User answer',execution:'Robot execution',evaluation:'Evaluation'};
function atlas(url){
  if(!cache.has(url))cache.set(url,new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(Error(`Atlas failed: ${url}`));im.src=url;}));
  const entry=cache.get(url);cache.delete(url);cache.set(url,entry);
  while(cache.size>3)cache.delete(cache.keys().next().value);
  return entry;
}
function frameAt(ms){
  const fs=playbackFrames;let lo=0,hi=fs.length-1;
  while(lo<hi){const mid=Math.floor((lo+hi+1)/2);if(fs[mid].start_ms<=ms)lo=mid;else hi=mid-1;}
  return fs[lo];
}
function name(id){return episode.object_names[id]||id;}
function humanText(text){for(const [id,label]of Object.entries(episode.object_names).sort((a,b)=>b[0].length-a[0].length))if(id!=='table')text=text.replaceAll(id,label);return text;}
function answerText(answer){
  if(answer?.choices)return Object.entries(answer.choices).map(([r,id])=>`${r==='cup_destination'?'Cup destination':r[0].toUpperCase()+r.slice(1)}: ${name(id)}`).join('  ·  ');
  return (answer?.confirmations||[]).map(c=>`${name(c.candidate_id)}: ${c.confirmed?'Yes':'No'}`).join('  ·  ');
}
function physicalTitle(f){
  if(f.stage==='question')return 'Clarification needed · physics paused';
  if(f.stage==='user_answer')return 'User preferences received · physics paused';
  if(f.stage==='evaluation')return f.evaluation.task_success?'Task complete · Success':'Task complete · Evaluation failed';
  if(f.stage==='gate_result')return f.gate.decision==='ASK'?'Observe scene · clarification decision':'Observe scene · useful progress is available';
  if(f.action?.kind==='cover')return 'Cover box with '+f.action_name;
  return (f.action_name?.endsWith('cup')?'Pick and place ':'Place ')+f.action_name+' in '+f.target_name;
}
function updateDOM(f){
  stage.dataset.frameIndex=f.frame_index;stage.dataset.simulationStep=f.simulation_step;stage.dataset.activeNode=f.active_flow_node;stage.dataset.round=f.round;
  stage.classList.toggle('ask',f.gate.decision==='ASK');stage.classList.toggle('success',f.stage==='evaluation'&&f.evaluation.task_success);
  const jev=f.gate.backend==='jev';
  $('gate-name').textContent=jev?'Clarification Gate · Jev Noul':'Clarification Gate · DeepSeek';
  $('gate-probability').textContent=jev&&f.gate.p_ask!==null?`p(ASK) = ${f.gate.p_ask.toFixed(2)} · ${f.gate.decision}`:`${f.gate.decision} · LLM decision`;
  $('round-stage').textContent=`Round ${f.round} · ${stageNames[f.stage]}`;
  $('action-title').textContent=physicalTitle(f);$('step-label').textContent=`Simulation step ${f.simulation_step.toLocaleString()}`;
  document.querySelectorAll('[data-node]').forEach(el=>{
    const id=el.dataset.node,active=f.active_nodes.includes(id);
    el.classList.toggle('active',active);el.classList.toggle('primary',id===f.active_flow_node);
    el.classList.toggle('completed',f.completed_nodes.includes(id));
    el.classList.toggle('orange',active&&f.gate.decision==='ASK');el.classList.toggle('green',active&&f.stage==='evaluation');
  });
  document.querySelectorAll('[data-edge]').forEach(el=>{
    const active=f.active_edges.includes(el.dataset.edge);el.classList.toggle('active',active);
    el.classList.toggle('orange',active&&f.gate.decision==='ASK');el.classList.toggle('green',active&&f.stage==='evaluation');
  });
  document.querySelector('.ask-label').classList.toggle('active',f.gate.decision==='ASK');
  document.querySelector('.continue-label').classList.toggle('active',f.gate.decision==='CONTINUE');
  $('evaluator-text').textContent=f.evaluation?`Independent Evaluator · ${f.evaluation.task_success?'SUCCESS':'FAILURE'}`:'Independent Evaluator';
  const phaseIndex=phaseNames.indexOf(f.physical_phase);
  document.querySelectorAll('[data-phase]').forEach(el=>{el.classList.toggle('active',el.dataset.phase===f.physical_phase);el.classList.toggle('past',phaseIndex>=0&&phaseNames.indexOf(el.dataset.phase)<phaseIndex);});
  $('instruction').textContent=episode.public_task_summary;$('instruction').title=episode.instruction;
  const roles=episode.method==='jev_gate'?['cup','block','lid']:['cup','block','cup_destination'];
  $('known-preferences').textContent=roles.map(r=>`${r==='cup_destination'?'Cup destination':r[0].toUpperCase()+r.slice(1)}: ${f.public_preferences[r]||'undisclosed'}`).join('  ·  ');
  $('decision-line').textContent=jev?`Jev p(ASK) = ${f.gate.p_ask.toFixed(2)}  ·  ${f.gate.decision}`:`DeepSeek Gate  ·  ${f.gate.decision}`;
  $('output-heading').textContent=f.stage==='evaluation'?'INDEPENDENT PHYSICAL EVALUATION':f.gate.decision==='ASK'?'PUBLIC QUESTION & ANSWER':'RECORDED DECISION & ACTION';
  $('planner-line').textContent=f.question?humanText(f.question.text):(f.action_text?`Planner: ${f.action_text}`:'Recorded gate decision');
  $('answer-line').textContent=f.user_answer?answerText(f.user_answer):f.stage==='question'?'Awaiting user response…':f.stage==='execution'?`Physical phase: ${f.physical_phase[0].toUpperCase()+f.physical_phase.slice(1)}`:'';
  if(f.evaluation){
    const satisfied=Object.values(f.evaluation.conditions).filter(Boolean).length;
    $('outcome-line').textContent=`${satisfied}/${Object.keys(f.evaluation.conditions).length} conditions satisfied · ${f.evaluation.action_count} actions · burden ${f.evaluation.clarification_burden}`;
  }else if(f.completed_actions.length){
    const last=f.completed_actions.at(-1);$('outcome-line').textContent=`Last result: ${last.object_name} ${last.success?'placed successfully':'failed'}${f.stage==='execution'?' · current action in progress':''}`;
  }else $('outcome-line').textContent=f.stage==='execution'?'Physical result: in progress':'Public observation + instruction + history';
  $('evidence-label').textContent=`${episode.sample_id} · ${episode.method} · source frame ${f.source_gif_frame_index+1}/${episode.encoded_gif_frame_count}`;
  $('time-compression').textContent=highlight?`Milestone highlight · actions ${manifest.highlight.action_speed}× · readable clarification holds`:'Source display timeline · inference instants not recorded';
  $('replay-kind').textContent=highlight?'COMPRESSED RECORDED EXECUTION':'RECORDED EPISODE';
  $('seek').value=Math.round(time);$('time-label').textContent=`${(time/1000).toFixed(1)} / ${(playbackDuration/1000).toFixed(1)} s`;
}
async function renderAt(ms){
  time=Math.max(0,Math.min(ms,playbackDuration));const f=frameAt(time);const serial=++renderSerial;
  if(frame?.frame_index===f.frame_index&&canvas.dataset.episode===episode.episode_key){$('seek').value=Math.round(time);$('time-label').textContent=`${(time/1000).toFixed(1)} / ${(playbackDuration/1000).toFixed(1)} s`;return f;}
  const im=await atlas(f.asset.url);if(serial!==renderSerial)return null;
  const [x,y,w,h]=f.asset.rect;ctx.drawImage(im,x,y,w,h,0,0,canvas.width,canvas.height);
  canvas.dataset.sourceFrame=f.source_gif_frame_index;canvas.dataset.logicalFrame=f.frame_index;canvas.dataset.episode=episode.episode_key;
  frame=f;updateDOM(f);
  const next=episode.frames.find(r=>r.frame_index>f.frame_index&&r.asset.url!==f.asset.url);if(next)atlas(next.asset.url).catch(fail);
  return f;
}
function currentTime(){return playing?Math.min(playbackDuration,anchorSource+(performance.now()-anchorWall)*speed):time;}
function fail(error){pause();$('load-error').style.display='block';$('load-error').textContent=error.message;console.error(error);}
function pause(){if(playing)time=currentTime();playing=false;cancelAnimationFrame(raf);$('play').textContent='Play';return renderAt(time);}
function tick(){if(!playing)return;const ms=currentTime();renderAt(ms).catch(fail);if(ms>=playbackDuration){playing=false;$('play').textContent='Play';return;}raf=requestAnimationFrame(tick);}
function play(){if(time>=playbackDuration)time=0;playing=true;anchorSource=time;anchorWall=performance.now();$('play').textContent='Pause';cancelAnimationFrame(raf);raf=requestAnimationFrame(tick);}
async function seek(ms,{keepPlaying=false}={}){const wasPlaying=playing;await pause();await renderAt(ms);if(keepPlaying&&wasPlaying)play();return snapshot();}
function setSpeed(value){if(![1,2,3].includes(Number(value)))throw Error('Invalid speed');time=currentTime();speed=Number(value);anchorSource=time;anchorWall=performance.now();$('speed').value=speed;return renderAt(time);}
async function selectEpisode(key){
 if(episode)await pause();episode=manifest.episodes.find(e=>e.episode_key===key);if(!episode)throw Error('Unknown episode');
 let start=0;
 playbackFrames=episode.frames.map(f=>{const duration=highlight?(manifest.highlight.holds_ms[f.stage]??f.duration_ms/manifest.highlight.action_speed):f.duration_ms;const row={...f,source_start_ms:f.start_ms,source_duration_ms:f.duration_ms,start_ms:start,end_ms:start+duration,duration_ms:duration};start+=duration;return row;});
 playbackDuration=start;frame=null;time=0;cache.clear();$('episode-select').value=key;$('seek').max=playbackDuration;await renderAt(0);return snapshot();
}
function snapshot(){return {episode:episode?.episode_key,time_ms:time,playing,speed,frame_index:frame?.frame_index,source_frame:Number(canvas.dataset.sourceFrame),simulation_step:frame?.simulation_step,round:frame?.round,stage:frame?.stage,active_flow_node:frame?.active_flow_node,physical_phase:frame?.physical_phase,gate:frame?.gate,action:frame?.action,question:frame?.question,user_answer:frame?.user_answer,public_preferences:frame?.public_preferences,evaluation:frame?.evaluation,dom_frame:Number(stage.dataset.frameIndex),dom_step:Number(stage.dataset.simulationStep),dom_node:stage.dataset.activeNode};}
$('play').onclick=()=>playing?pause():play();$('restart').onclick=async()=>{await seek(0);play();};
$('seek').oninput=()=>seek(Number($('seek').value),{keepPlaying:true}).catch(fail);
$('speed').onchange=()=>setSpeed($('speed').value);$('episode-select').onchange=()=>selectEpisode($('episode-select').value).catch(fail);
window.replay={seek,play,pause,setSpeed,selectEpisode,snapshot,frameAt:ms=>frameAt(ms),
  async renderFrame(index){await pause();return seek(playbackFrames[index].start_ms);},
  async pixelHash(){const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;const hash=await crypto.subtle.digest('SHA-256',data);return Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');},
  get manifest(){return manifest;},get episode(){return episode;},get playbackFrames(){return playbackFrames;},get playbackDuration(){return playbackDuration;}};
window.replayReady=(async()=>{const response=await fetch('timeline.json');if(!response.ok)throw Error('Timeline failed to load');manifest=await response.json();await selectEpisode(params.get('episode')||manifest.default_episode);if(params.get('autoplay')==='1')play();return snapshot();})();
window.replayReady.catch(fail);
