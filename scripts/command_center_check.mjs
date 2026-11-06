// Explicit real-browser checks. Default: scripted policies + real PyBullet only.
// --live: exactly one three-method comparison, billed to the controller's cap.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const live=process.argv.includes('--live'),si=process.argv.indexOf('--session-dir');
if(live&&si<0)throw Error('--live requires --session-dir for raw API audit verification');
const session=si>=0?path.resolve(process.argv[si+1]):null;
const output=path.join(ROOT,'outputs/command_center_evidence');await fs.mkdir(output,{recursive:true});
const {chromium}=requireRuntime('playwright');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],external=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
await page.route('**/*',r=>{if(new URL(r.request().url()).hostname!=='127.0.0.1'){external.push(r.request().url());return r.abort();}return r.continue();});
await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
async function request(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});return {status:r.status,data:await r.json()};},{url,body});}
async function get(id){return (await request('/api/tasks/'+id)).data;}
async function launch(template,method,mode,unknown){await page.selectOption('#template',template);await page.selectOption('#unknown',String(unknown));await page.selectOption('#method',method);if(!method.endsWith('noask'))await page.selectOption('#answer-mode',mode);const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const r=await response;assert.equal(r.status(),201);return (await r.json()).id;}
async function finish(ids){await page.waitForFunction(ids=>ids.every(id=>['done','error','cancelled'].includes(window.consoleView.tasks.get(id)?.status)),ids,{timeout:240000});return Promise.all(ids.map(get));}
async function saveEpisode(t,prefix){const episode=(await request('/api/tasks/'+t.id+'/episode')).data;if(live){const lines=await fs.readFile(path.join(session,'tasks',t.id,'api_attempts.jsonl'),'utf8');episode.api_attempts=lines.trim().split('\n').filter(Boolean).map(JSON.parse);await fs.writeFile(path.join(output,prefix+'_'+t.method+'_api_attempts.jsonl'),lines);}await fs.writeFile(path.join(output,prefix+'_'+t.method+'_'+t.template+'_episode.json'),JSON.stringify(episode,null,2)+'\n');return episode;}
async function checkFrames(states){const results=[];for(const t of states){const c=page.locator('[data-task-id="'+t.id+'"].card');const src=await c.locator('img').getAttribute('src');const sha=crypto.createHash('sha256').update(Buffer.from(src.split(',')[1],'base64')).digest('hex');assert.equal(sha,await c.locator('img').getAttribute('data-sha256'));assert.equal(Number(await c.getAttribute('data-frame-step')),Number(await c.locator('img').getAttribute('data-simulation-step')));results.push({task_id:t.id,simulation_step:t.frame.simulation_step,sha256:sha,metadata_matches:true});}return results;}
const before=(await request('/api/meta')).data.budget;
let report;
if(!live){
 const manual=await launch('pack_and_cover','scripted_ask','manual',2);
 const dual=await launch('place_into_selected_containers','scripted_ask','manual',1);
 const auto=await launch('pack_and_cover','scripted_noask','auto',0);
 const queued=await launch('pack_and_cover','scripted_ask','manual',3);
 assert.equal((await get(queued)).status,'queued');await request('/api/tasks/'+queued+'/cancel',{});
 await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='cancelled',queued);await page.locator('.card[data-task-id="'+queued+'"] .stop').click();
 await page.waitForFunction(ids=>ids.every(id=>window.consoleView.tasks.get(id)?.status==='waiting_answer'),[manual,dual],{timeout:120000});
 assert.equal(await page.locator('#queue-list .queue-item').count(),2);
 const pending=[await get(manual),await get(dual)],qids=pending.map(t=>t.question.id);
 const snapshots=await Promise.all([manual,dual].map(id=>request('/api/tasks/'+id+'/inspect',{})));
 const otherBefore=(await get(auto)).frame.simulation_step;await page.waitForTimeout(1500);
 const after=await Promise.all([manual,dual].map(id=>request('/api/tasks/'+id+'/inspect',{})));
 snapshots.forEach((v,i)=>assert.deepEqual(v.data.observation,after[i].data.observation));
 const other=await get(auto);assert(other.frame.simulation_step>otherBefore||other.status==='done');
 await page.locator('#queue-list [data-task-id="'+manual+'"]').click();
 await page.selectOption('#answer-desk select[data-role="block"]',{label:'green block'});
 const draft=await page.locator('#answer-desk select[data-role="block"]').inputValue();
 await page.locator('#queue-list [data-task-id="'+dual+'"]').click();
 assert.equal(await page.locator('#answer-desk').getAttribute('data-task-id'),dual);
 await page.locator('#queue-list [data-task-id="'+manual+'"]').click();
 assert.equal(await page.locator('#answer-desk select[data-role="block"]').inputValue(),draft);
 await page.screenshot({path:path.join(output,'02_clarification_queue.png')});
 await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>document.querySelectorAll('#queue-list .queue-item').length===2);
 await page.locator('#queue-list [data-task-id="'+manual+'"]').click();
 assert.equal(await page.locator('#answer-desk select[data-role="block"]').inputValue(),draft);
 const cross=await request('/api/tasks/'+dual+'/answer',{question_id:qids[0],source:'auto'});assert.equal(cross.status,409);
 // Browser intentionally reports the rejected 409; this is expected protocol validation.
 const expectedErrors=errors.splice(0).filter(e=>!e.includes('409'));assert.deepEqual(expectedErrors,[]);
 await page.selectOption('#answer-desk select[data-role="block"]',{label:'yellow block'});await page.selectOption('#answer-desk select[data-role="lid"]',{label:'white lid'});
 const choices=await page.locator('#answer-desk select').evaluateAll(es=>Object.fromEntries(es.map(e=>[e.dataset.role,e.value])));
 await page.getByRole('button',{name:'提交我的回答',exact:true}).click();
 const duplicate=await request('/api/tasks/'+manual+'/answer',{question_id:qids[0],source:'human',response:{choices}});assert.equal(duplicate.data.duplicate,true);
 await page.waitForFunction(id=>document.querySelector('#answer-desk')?.dataset.taskId===id,dual);
 const still=await get(dual);assert.equal(still.question.id,qids[1]);assert.equal(still.frame.simulation_step,after[1].data.observation.simulation_step);
 await page.getByRole('button',{name:'自动回答本次',exact:true}).click();
 const finished=await finish([manual,dual,auto]);assert(finished.every(t=>t.status==='done'&&t.evaluation.task_success),JSON.stringify(finished.map(t=>({status:t.status,error:t.error,score:t.evaluation}))));
 assert.equal(new Set(finished.map(t=>t.worker_pid)).size,3);assert.deepEqual(finished.map(t=>t.burden),[2,1,0]);assert.equal((await request('/api/clarifications')).data.clarifications.length,0);
 const frames=await checkFrames(finished);await page.screenshot({path:path.join(output,'03_offline_results.png')});
 for(const t of finished)await saveEpisode(t,'offline');
 await page.setViewportSize({width:1440,height:900});await page.screenshot({path:path.join(output,'04_laptop.png')});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.setViewportSize({width:430,height:932});await page.screenshot({path:path.join(output,'05_mobile.png')});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 const now=(await request('/api/meta')).data.budget;assert.equal(now.attempts,before.attempts);
 report={passed:true,evidence_kind:'scripted_policies_real_pybullet_browser',new_api_attempts:now.attempts-before.attempts,tasks:finished.map(t=>({id:t.id,template:t.template,burden:t.burden,task_success:t.evaluation.task_success,worker_pid:t.worker_pid})),queue_has_two_independent_questions:true,cross_task_answer_rejected:true,duplicate_answer_ignored:true,draft_preserved_across_switch_and_reload:true,queued_cancel_verified:true,ask_snapshots_unchanged:true,other_task_progress:true,frame_checks:frames,responsive_no_overflow:[1920,1440,430]};
}else{
 await page.selectOption('#template','pack_and_cover');await page.selectOption('#unknown','2');
 const response=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
 await page.click('#compare-start');const res=await response;assert.equal(res.status(),201);const group=await res.json();
 await fs.writeFile(path.join(ROOT,'outputs/local_console/command-center-live-group.json'),JSON.stringify(group));
 console.log(JSON.stringify({live_comparison_id:group.id,task_ids:group.task_ids}));
 await page.waitForFunction(ids=>ids.every(id=>window.consoleView.tasks.get(id)?.frame),group.task_ids,{timeout:90000});
 await page.screenshot({path:path.join(output,'06_live_comparison_running.png')});
 const finished=await finish(group.task_ids),episodes=[];for(const t of finished)episodes.push(await saveEpisode(t,'live'));
 assert(finished.every(t=>t.status==='done'),JSON.stringify(finished.map(t=>({method:t.method,error:t.error,status:t.status}))));
 assert.equal(new Set(finished.map(t=>t.worker_pid)).size,3);
 assert(episodes.every(e=>JSON.stringify(e.turns[0].public_payload)===JSON.stringify(episodes[0].turns[0].public_payload)));
 assert(episodes.every(e=>JSON.stringify(e.prompt_hashes)===JSON.stringify(episodes[0].prompt_hashes)));
 const raw=(await request('/api/comparisons/'+group.id)).data;assert.equal(raw.status,'complete');
 assert(raw.rows.every((r,i)=>r.task_success===finished[i].evaluation.task_success));
 const noask=episodes[0];assert(noask.turns.every(t=>t.gate.called===false));
 const tries=episodes.flatMap(e=>e.api_attempts);assert(tries.every(r=>r.status==='ok'));assert(tries.every(r=>Number.isInteger(r.session_attempt)&&r.session_attempt>0));
 const budget=(await request('/api/meta')).data.budget;assert.equal(budget.attempts-before.attempts,tries.length);assert.equal(budget.episodes-before.episodes,3);
 await page.evaluate(()=>window.consoleView.refreshMeta());
 await page.screenshot({path:path.join(output,'07_live_comparison_results.png'),fullPage:true});
 await page.locator('#comparison-panel').screenshot({path:path.join(output,'08_comparison_table.png')});
 const frames=await checkFrames(finished);await page.locator('.tasks.comparing .card:not([hidden]) .viewport').first().click();await page.waitForSelector('#focus[open]');await page.screenshot({path:path.join(output,'09_full_view.png')});await page.click('#focus-close');
 await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.consoleView?.groups.size>0);await page.click('#compare-tab');await page.waitForFunction(()=>document.querySelectorAll('#comparison-rows tr').length===3);
 const csv=await page.evaluate(async id=>{const r=await fetch('/api/comparisons/'+id+'/csv');return {status:r.status,text:await r.text()};},group.id);assert.equal(csv.status,200);
 await fs.writeFile(path.join(output,'live_comparison.json'),JSON.stringify(raw,null,2)+'\n');await fs.writeFile(path.join(output,'live_comparison.csv'),csv.text);
 report={passed:true,evidence_kind:'three_live_model_methods_real_pybullet_browser',group_id:group.id,task_ids:group.task_ids,same_initial_public_payload:true,same_prompt_hashes:true,independent_worker_pids:finished.map(t=>t.worker_pid),results:raw.rows,new_authenticated_attempts:tries.length,budget,frame_checks:frames,csv_export_verified:true,reload_keeps_comparison:true,formal_test_episodes:0};
}
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);report.console_errors=errors;report.external_requests=external;
await fs.writeFile(path.join(output,live?'live_validation.json':'browser_validation.json'),JSON.stringify(report,null,2)+'\n');
await browser.close();console.log(JSON.stringify(report));
