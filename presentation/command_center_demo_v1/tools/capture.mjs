// Operate the actual console in Chromium. No mocked responses or synthetic tasks.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../../milestone/tools/runtime.mjs';
const {chromium}=requireRuntime('playwright');
const BASE=path.join(ROOT,'presentation/command_center_demo_v1');
const OUT=path.join(ROOT,'outputs/command_center_demo_v1');
const live=process.argv.includes('--live');
const URL='http://127.0.0.1:8908/';
const jobs=[
 {template:'retrieve_restore',method:'llm_gate',profile:'gate_dev_v7',unknown:'1',answer:'manual'},
 {template:'buffer_exchange',method:'jev_gate',profile:'gate_dev_v7',unknown:'1',answer:'manual'},
 {template:'category_sorting',method:'jev_gate',profile:'default_v1',unknown:'1',answer:'manual'},
 {template:'find_and_approach',method:'llm_noask',profile:'default_v1',unknown:'0',answer:'auto'},
];
const css=await fs.readFile(path.join(BASE,'tools/film.css'),'utf8');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,...(live?{recordVideo:{dir:path.join(BASE,'.build'),size:{width:1920,height:1080}}}:{})});
const started=Date.now(),page=await context.newPage(),events=[],errors=[],ids=[],samples=[];
const stamp=()=>Math.round(Date.now()-started);
function event(kind,data={}){const row={capture_ms:stamp(),kind,...data};events.push(row);console.log(JSON.stringify(row));return row;}
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url){return page.evaluate(async url=>{const r=await fetch(url);if(!r.ok)throw Error('HTTP '+r.status);return r.json();},url);}
async function save(){await fs.writeFile(path.join(OUT,'capture_events.json'),JSON.stringify({started_at:new Date(started).toISOString(),events,errors,jobs},null,2));}
async function pause(ms){await page.waitForTimeout(ms);}
async function move(selector){const loc=page.locator(selector);await loc.scrollIntoViewIfNeeded();const b=await loc.boundingBox();await page.mouse.move(b.x+b.width*.5,b.y+b.height*.5,{steps:14});return loc;}
async function choose(selector,value){const loc=await move(selector);await loc.evaluate(el=>el.classList.add('film-picked'));await pause(300);await loc.selectOption(value);await pause(500);await loc.evaluate(el=>el.classList.remove('film-picked'));}
async function click(selector){const loc=await move(selector);await pause(250);await loc.click();await pause(300);}
let sampler,summary;
try{
 await page.goto(URL,{waitUntil:'networkidle'});
 await page.waitForSelector('#new-task-options option',{state:'attached'});
 await page.addStyleTag({content:css});
 await page.evaluate(()=>{
  const tag=document.createElement('span');tag.className='film-tag';tag.textContent='Robot Command Center  /  Human in the loop';document.querySelector('.hub-nav').append(tag);
  const foot=document.createElement('div');foot.className='film-footer';foot.innerHTML='<b>Dispatch → Observe → Answer → Complete</b><span>Real model decisions · Real PyBullet execution</span>';document.body.append(foot);
  const cursor=document.createElement('div');cursor.id='film-pointer';document.body.append(cursor);
  document.addEventListener('mousemove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px';});
  document.addEventListener('mousedown',()=>cursor.classList.add('down'));document.addEventListener('mouseup',()=>cursor.classList.remove('down'));
 });
 assert.equal((await rpc('/api/tasks')).tasks.length,0,'Must begin with an empty session');
 assert.equal((await rpc('/api/meta')).budget.episodes,0,'Refuse paid recapture');
 await page.screenshot({path:path.join(BASE,'screenshots/01_empty.png')});
 if(!live){console.log(JSON.stringify({preflight:true,errors,layout:await page.evaluate(()=>({width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth}))}));}
 else{
  await fs.writeFile(path.join(OUT,'capture_plan.json'),JSON.stringify({jobs,max_episodes:4,max_authenticated_requests:160,threshold:.5,answer_protocol:'operator typed public candidate names; interactive intent, not a benchmark',recording:'actual Chromium whole-page video; no mocked API/physics',version:'command_center_demo_v1'},null,2),{flag:'wx'});
  event('empty_ready');await pause(2300);
  sampler=setInterval(async()=>{try{samples.push({capture_ms:stamp(),tasks:await page.evaluate(()=>[...window.consoleView.tasks.values()].map(t=>({id:t.id,version:t.version,status:t.status,round:t.round,gate:t.gate,question_id:t.question?.id,frame_step:t.frame?.simulation_step,frame_sha:t.frame?.sha256,phase:t.frame?.phase,evaluation:t.evaluation}))) });}catch{}},600);
  for(const [index,job] of jobs.entries()){
   event('configure_start',{index,...job});
   await choose('#template',job.template);
   await page.selectOption('#unknown',job.unknown,{force:true});await page.selectOption('#planner-profile',job.profile,{force:true});
   await choose('#method',job.method);
   if(job.method!=='llm_noask')await choose('#answer-mode',job.answer);
   await pause(600);
   const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');
   await click('#start');const res=await response;assert.equal(res.status(),201);const task=await res.json();ids.push(task.id);event('mission_launched',{index,task_id:task.id,...job,instruction:task.instruction});
   await pause(1400);await save();
  }
  event('all_dispatched');await page.screenshot({path:path.join(BASE,'screenshots/02_four_missions.png')});
  const handled=new Set(),deadline=Date.now()+420000;let answerIndex=0;
  while(Date.now()<deadline){
   const tasks=(await rpc('/api/tasks')).tasks;
   const pending=tasks.filter(t=>t.status==='waiting_answer'&&t.question&&!handled.has(t.question.id)).sort((a,b)=>a.question.created-b.question.created);
   if(pending.length){
    const task=pending[0],q=task.question;handled.add(q.id);answerIndex++;
    const selector='.queue-item[data-question-id="'+q.id+'"]';await page.waitForSelector(selector);await click(selector);
    const before=await rpc('/api/tasks/'+task.id);
    event('answer_focus',{task_id:task.id,question_id:q.id,question:q.text,step:before.frame?.simulation_step,frame_sha:before.frame?.sha256});
    await pause(1700);await page.screenshot({path:path.join(BASE,'screenshots/03_question_'+answerIndex+'.png')});
    // Human preferences: choose visible candidates. No private ground truth is read.
    const choices=q.requests.map(r=>({role:r.role,candidate_id:q.known_choices?.[r.role]||r.candidate_ids?.[0]||r.candidate_id}));
    const text=q.type==='confirm'?'yes':choices.map(c=>q.candidates[c.candidate_id]||c.candidate_id).join(', ');
    await move('#answer-desk textarea');await page.click('#answer-desk textarea');await page.locator('#answer-desk textarea').pressSequentially(text,{delay:85});await pause(900);
    const beforeSubmit=await rpc('/api/tasks/'+task.id);assert.equal(before.frame.simulation_step,beforeSubmit.frame.simulation_step);assert.equal(before.frame.sha256,beforeSubmit.frame.sha256);
    await page.screenshot({path:path.join(BASE,'screenshots/04_typed_answer_'+answerIndex+'.png')});
    event('answer_typed',{task_id:task.id,question_id:q.id,text,choices,physics_frozen:true});
    const answerResponse=page.waitForResponse(r=>r.url().includes('/answer')&&r.request().method()==='POST');
    await click('#answer-desk .answer-buttons button:first-child');const ar=await answerResponse;assert.equal(ar.status(),200,'Actual text reply must be accepted');
    event('answer_submitted',{task_id:task.id,question_id:q.id,text});await pause(1500);await save();
   }else if(tasks.length===4&&tasks.every(t=>['done','error','cancelled'].includes(t.status))){summary=tasks;break;}
   else await pause(500);
  }
  assert(summary,'Bounded live capture timed out; keep evidence, do not rerun');
  event('all_terminal',{tasks:summary.map(t=>({id:t.id,template:t.template,method:t.method,success:t.evaluation?.task_success,error:t.error,ask_turns:t.ask_turns,robot_actions:t.actions.length}))});
  await pause(1700);await page.screenshot({path:path.join(BASE,'screenshots/05_completed.png')});
  await pause(5000);event('end');
  const meta=await rpc('/api/meta');assert.equal(meta.budget.episodes,4);assert(meta.budget.attempts<=160);
  await fs.writeFile(path.join(OUT,'validation.json'),JSON.stringify({kind:'real_browser_real_models_real_physics_operator_replies',tasks:summary.map(t=>({id:t.id,template:t.template,method:t.method,status:t.status,evaluation:t.evaluation,ask_turns:t.ask_turns,robot_actions:t.actions.length,cost:t.cost,returned_models:t.returned_models,error:t.error})),budget:meta.budget,errors,viewport:{width:1920,height:1080},overflow:await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)},null,2));
 }
}finally{
 if(sampler)clearInterval(sampler);
 if(live){await save();await fs.writeFile(path.join(OUT,'visible_state_samples.json'),JSON.stringify(samples));}
 const video=page.video();await context.close();if(video)await video.saveAs(path.join(BASE,'.build/full_live_capture.webm'));await browser.close();
}
