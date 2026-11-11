// Explicit live six-episode follow-up; actual browser/task controller/physics.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Explicit --live required');
const out=path.join(ROOT,'outputs/gate_diagnostics_dev_v7'),session=path.join(ROOT,'outputs/local_console/gate-diagnostics-v7-live');
const plan=JSON.parse(await fs.readFile(path.join(out,'live_plan.json'),'utf8'));await fs.mkdir(path.join(out,'live'),{recursive:false});
for(const [name,hash]of Object.entries(plan.source_hashes))assert.equal(crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,name))).digest('hex'),hash,name);
const b=await requireRuntime('playwright').chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const p=await b.newPage({viewport:{width:1920,height:1080}}),errors=[],created=[];p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url){return p.evaluate(async url=>{const r=await fetch(url);if(!r.ok)throw Error(await r.text());return r.json();},url);}
try{
 await p.goto('http://127.0.0.1:8898/');await p.waitForSelector('#new-task-options option',{state:'attached'});const meta=await rpc('/api/meta');assert.equal(meta.budget.episodes,0);assert.equal(meta.budget.attempts,plan.prior_gate_attempts);assert.equal(meta.budget.max_episodes,6);assert.equal(meta.budget.max_attempts,150);assert.equal(await p.locator('#planner-profile').inputValue(),'default_v1');
 for(const job of plan.jobs){
  await p.selectOption('#template',job.template);await p.selectOption('#unknown','1');await p.selectOption('#planner-profile',job.planner_profile);await p.selectOption('#method',job.method);await p.selectOption('#answer-mode','auto');
  const response=p.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await p.click('#start');const r=await response;assert.equal(r.status(),201);const task=await r.json();created.push({id:task.id,...job});console.log(JSON.stringify({launched:task.id,...job}));
 }
 const deadline=Date.now()+600000;while(Date.now()<deadline){const ts=(await rpc('/api/tasks')).tasks;if(ts.length===6&&ts.every(t=>['done','error','cancelled'].includes(t.status)))break;await p.waitForTimeout(1000);}
 const tasks=(await rpc('/api/tasks')).tasks;assert.equal(tasks.length,6);assert(tasks.every(t=>['done','error','cancelled'].includes(t.status)));
 for(const t of tasks){const dest=path.join(out,'live',[t.template,t.method,t.planner_profile].join('__'));await fs.mkdir(dest,{recursive:false});for(const name of ['episode.json','evaluation.json','api_attempts.jsonl','review.json','final_view.json'])await fs.copyFile(path.join(session,'tasks',t.id,name),path.join(dest,name));
  await p.locator('.card[data-task-id="'+t.id+'"] .review-link').click();await p.screenshot({path:path.join(dest,'review.png')});await p.click('#review-close');console.log(JSON.stringify({completed:t.id,template:t.template,method:t.method,profile:t.planner_profile,success:t.evaluation?.task_success,burden:t.burden,actions:t.actions.length,error:t.error}));}
 await p.screenshot({path:path.join(out,'live_wall.png'),fullPage:true});const budget=(await rpc('/api/meta')).budget;assert.equal(budget.episodes,6);assert(budget.attempts<=150);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'live_validation.json'),JSON.stringify({evidence_kind:'real_api_real_pybullet_browser',created,episodes:6,authenticated_episode_requests:budget.attempts-plan.prior_gate_attempts,total_authenticated_requests:budget.attempts,console_errors:errors},null,2)+'\n');
}finally{await b.close();}
