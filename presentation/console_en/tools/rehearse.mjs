// Real browser / real physics rehearsal. Paid calls require --live explicitly.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const ROOT=fileURLToPath(new URL('../../../',import.meta.url));
const req=createRequire(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/runtime.cjs'));
const {chromium}=req('playwright');
const live=process.argv.includes('--live');
const attempt=process.argv.find(x=>x.startsWith('--attempt='))?.split('=')[1]||'qa1';
const OUT=path.join(ROOT,'outputs/presentation_console_en/20261112',live?'live_'+attempt:'offline_'+attempt);
await fs.mkdir(OUT,{recursive:false});
const manifest={mode:live?'live_models_and_real_physics':'scripted_public_policy_and_real_physics',url:'http://127.0.0.1:8902/',
 profile:'gate_dev_v7',templates:live?['retrieve_restore']:['buffer_exchange','occlusion_inspection'],
 max_new_online_episodes:live?3:0,max_new_authenticated_requests:live?96:0,whole_episode_retries:0};
await fs.writeFile(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],ids=[],answerEvidence=[];let expectingAnswerValidation=false;const expectedValidationErrors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'){if(expectingAnswerValidation&&m.text().includes('400'))expectedValidationErrors.push(m.text());else errors.push(m.text());}});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const v=await r.json();if(!r.ok)throw Error(v.error||String(r.status));return v;},{url,body});}
const sleep=ms=>page.waitForTimeout(ms);
async function ready(){await page.goto(manifest.url,{waitUntil:'domcontentloaded'});await page.waitForSelector('#new-task-options',{state:'attached'});await sleep(200);}
async function select(template,method,answerMode){await page.selectOption('#template',template);await page.selectOption('#unknown','1');await page.selectOption('#planner-profile','gate_dev_v7');await page.selectOption('#method',method);if(answerMode)await page.selectOption('#answer-mode',answerMode);}
async function launch(){const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const r=await response;assert.equal(r.status(),201);const task=await r.json();ids.push(task.id);return task;}
async function english(){assert.equal(await page.evaluate(()=>/\p{Script=Han}/u.test(document.body.innerText)),false,'Non-English display copy');}
async function screenshot(name){await english();await page.screenshot({path:path.join(OUT,name+'.png')});}
async function finish(taskIds,ms=180000){const deadline=Date.now()+ms;while(Date.now()<deadline){const rows=(await rpc('/api/tasks')).tasks.filter(t=>taskIds.includes(t.id));if(rows.length===taskIds.length&&rows.every(t=>['done','error','cancelled'].includes(t.status)))return rows;await sleep(250);}throw Error('Bounded rehearsal timeout');}
let result={manifest,started_at:new Date().toISOString()};
try{
 await ready();const before=(await rpc('/api/meta')).budget;result.budget_before=before;
 assert.equal(await page.locator('#template option').count(),9);await english();
 if(!live){
  await select('buffer_exchange','scripted_ask','manual');const human=await launch();assert.equal(human.review.ground_truth,null);
  await select('occlusion_inspection','scripted_ask','auto');const sensor=await launch();
  const deadline=Date.now()+90000;let waiting;
  while(Date.now()<deadline){const t=await rpc('/api/tasks/'+human.id);if(t.status==='waiting_answer'){waiting=t;break;}if(['error','done'].includes(t.status))throw Error('Manual task terminated before ASK');await sleep(200);}
  assert(waiting);await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='waiting_answer',human.id);
  await page.evaluate(id=>window.consoleView.chooseQuestion(id),waiting.question.id);
  assert.equal(await page.locator('#answer-desk textarea').count(),1);assert(await page.locator('#answer-desk textarea').isVisible());
  await page.locator(`.card[data-task-id="${human.id}"] .review-link`).click();assert.equal(await page.locator('.truth-table').count(),0);await english();await page.click('#review-close');
  const f1=await rpc('/api/tasks/'+human.id+'/inspect',{});
  await page.getByRole('button',{name:'Presentation View',exact:true}).click();
  // Leave the manual robot paused while the independent sensor task completes.
  const sensorDone=(await finish([sensor.id]))[0];assert.equal(sensorDone.evaluation.task_success,true);assert.equal(sensorDone.ask_turns,0);
  const f2=await rpc('/api/tasks/'+human.id+'/inspect',{});assert.deepEqual(f1.observation,f2.observation);assert.equal(f1.frame.sha256,f2.frame.sha256);
  await screenshot('01_manual_question_and_independent_robot');
  expectingAnswerValidation=true;await page.locator('#answer-desk textarea').fill('unclear choice');await page.getByRole('button',{name:'Submit Answer',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.answer-error').textContent.length>0);await english();
  expectingAnswerValidation=false;const req=waiting.question.requests[0],candidate=req.candidate_ids[0],text=waiting.question.candidates[candidate];
  await page.locator('#answer-desk textarea').fill(text);await screenshot('02_typed_answer');await page.getByRole('button',{name:'Submit Answer',exact:true}).click();
  answerEvidence.push({task_id:human.id,question_id:waiting.question.id,text,role:req.role,candidate,physics_frozen:true,other_world_finished_during_wait:true});
  const rows=await finish([human.id,sensor.id]);assert(rows.every(t=>t.evaluation?.task_success===true));
  for(const t of rows){await page.evaluate(id=>window.consoleView.selectTask(id),t.id);await page.locator(`.card[data-task-id="${t.id}"] .review-link`).click();assert.equal(await page.locator('.truth-table').count(),1);assert((await page.locator('#review-body').innerText()).includes(t.instruction));await screenshot('review_'+t.template);await page.click('#review-close');}
  // Explicit NoAsk control: Human is disabled and never creates a queue entry.
  await page.getByRole('button',{name:'Mission Controls',exact:true}).click();await select('occlusion_inspection','scripted_noask',null);assert(await page.locator('#answer-mode').isDisabled());assert.equal(await page.locator('#answer-mode').inputValue(),'auto');const noask=await launch();const noaskDone=(await finish([noask.id]))[0];assert.equal(noaskDone.ask_turns,0);assert.equal(noaskDone.evaluation.task_success,true);
  result.tasks=[...rows,noaskDone].map(t=>({id:t.id,template:t.template,method:t.method,success:t.evaluation.task_success,burden:t.burden,ask_turns:t.ask_turns,worker_pid:t.worker_pid}));result.manual_answers=answerEvidence;result.scripted_physics_successes=3;
  assert.equal((await rpc('/api/meta')).budget.attempts,before.attempts);
 }else{
  assert.equal(before.episodes,0,'Refuse to repeat online rehearsal in a consumed session');
  await select('retrieve_restore','jev_gate','auto');const response=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');await page.click('#compare-start');const r=await response;assert.equal(r.status(),201);const group=await r.json();ids.push(...group.task_ids);await fs.writeFile(path.join(OUT,'comparison_id.json'),JSON.stringify({id:group.id,task_ids:group.task_ids},null,2)+'\n');
  assert.equal(group.partition,'interactive_demo_on_dev_layout');assert.equal(group.answer_mode,'auto');assert.equal(group.planner_profile,'gate_dev_v7');
  await page.waitForFunction(()=>[...document.querySelectorAll('.card:not([hidden]) img')].filter(i=>i.src.startsWith('data:')).length===3);await page.getByRole('button',{name:'Presentation View',exact:true}).click();await screenshot('01_three_real_methods');
  const rows=await finish(group.task_ids,240000);assert(rows.every(t=>t.evaluation),'All methods must return actual physical scoring');assert(rows.every(t=>t.evidence_kind==='live_models_real_pybullet'));
  const noask=rows.find(t=>t.method==='llm_noask');assert.equal(noask.ask_turns,0);assert.equal(noask.burden,0);
  await screenshot('02_paired_final_scores');
  for(const t of rows){await page.locator(`.card[data-task-id="${t.id}"] .review-link`).click();await english();assert.equal(await page.locator('.truth-table').count(),1);await screenshot('review_'+t.method);await page.click('#review-close');}
  const tasks=await Promise.all(group.task_ids.map(id=>rpc('/api/tasks/'+id+'/episode')));
  result.comparison_id=group.id;result.tasks=rows.map(t=>({id:t.id,template:t.template,method:t.method,success:t.evaluation.task_success,burden:t.burden,ask_turns:t.ask_turns,actions:t.actions.length,worker_pid:t.worker_pid,cost:t.cost,error:t.error,returned_models:t.returned_models}));
  assert.equal(new Set(rows.map(t=>t.worker_pid)).size,3);assert.equal((await rpc('/api/meta')).budget.episodes-before.episodes,3);
  await fs.writeFile(path.join(OUT,'raw_episodes.json'),JSON.stringify(tasks,null,2)+'\n');
 }
 result.budget_after=(await rpc('/api/meta')).budget;assert(result.budget_after.attempts<=96);
 // Navigate all three entry points and decode every recorded case.
 await page.getByRole('button',{name:'Benchmark Results',exact:true}).click();await page.waitForSelector('.evidence-panel tbody');await screenshot('benchmark_results');assert((await page.locator('#benchmark-page').innerText()).includes('105.41'));
 await page.getByRole('button',{name:'Recorded Replay',exact:true}).click();await page.waitForFunction(()=>window.presentationHub.recordedCase);const cases=await page.locator('#recorded-case option').evaluateAll(os=>os.map(o=>o.value));
 for(const id of cases){await page.selectOption('#recorded-case',id);await page.waitForFunction(id=>window.presentationHub.recordedCase===id,id);await page.waitForFunction(()=>[...document.querySelectorAll('.recorded-card video')].every(v=>v.videoWidth>0&&v.readyState>=2));}
 const replay=page.frames().find(f=>f.url().endsWith('/replay/'));assert(replay);await replay.waitForFunction(()=>window.replayReady);const checkpoints=[];for(const i of [0,20,49,50,75,106,130,163])checkpoints.push(await replay.evaluate(i=>window.replay.showFrame(i),i));assert.equal(checkpoints[2].simulation_step,checkpoints[3].simulation_step);assert.equal(checkpoints[2].stage,'question');assert.equal(checkpoints[3].stage,'answer');await replay.evaluate(()=>window.replay.seek(0));await screenshot('recorded_replay');result.replay_checkpoints=checkpoints;result.decoded_recorded_videos=9;
 await page.setViewportSize({width:390,height:844});for(const view of ['live','benchmark','replay']){await page.evaluate(v=>window.presentationHub.setView(v),view);await sleep(200);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),view+' mobile overflow');}await screenshot('mobile');result.mobile_no_overflow=true;assert.deepEqual(errors,[]);result.console_errors=errors;result.expected_invalid_answer_responses=expectedValidationErrors;result.passed=true;
}catch(e){result.passed=false;result.error=String(e);await page.screenshot({path:path.join(OUT,'failure.png')}).catch(()=>{});throw e;
}finally{result.finished_at=new Date().toISOString();await fs.writeFile(path.join(OUT,'validation.json'),JSON.stringify(result,null,2)+'\n');await browser.close();console.log(JSON.stringify({out:OUT,passed:result.passed,tasks:result.tasks,error:result.error}));}
