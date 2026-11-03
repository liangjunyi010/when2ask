// Browser + actual HTTP worker integration. These runs use explicitly Scripted
// policies and REAL PyBullet, never invented or paid model decisions.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const {chromium}=requireRuntime('playwright');
const output=path.join(ROOT,'outputs/console_evidence');await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],external=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
await page.route('**/*',r=>{if(new URL(r.request().url()).hostname!=='127.0.0.1'){external.push(r.request().url());return r.abort();}return r.continue();});
await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
async function get(id){return page.evaluate(async id=>(await fetch('/api/tasks/'+id)).json(),id);}
async function post(url,body){return page.evaluate(async ({url,body})=>{const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const value=await r.json();if(!r.ok)throw Error(value.error);return value;},{url,body});}
async function launch(template,method,mode){await page.selectOption('#template',template);await page.selectOption('#method',method);if(!method.endsWith('noask'))await page.selectOption('#answer-mode',mode);const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const r=await response;assert.equal(r.status(),201);return (await r.json()).id;}
const manual=await launch('pack_and_cover','scripted_ask','manual');
const dual=await launch('place_into_selected_containers','scripted_ask','auto');
const noask=await launch('pack_and_cover','scripted_noask','auto');
const queued=await launch('pack_and_cover','scripted_ask','manual');
await page.waitForTimeout(500);assert.equal((await get(queued)).status,'queued');
await post(`/api/tasks/${queued}/cancel`,{});
await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='cancelled',queued);
await page.locator(`[data-task-id="${queued}"] button.stop`).click();
await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='waiting_answer',manual,{timeout:120000});
const one=await post(`/api/tasks/${manual}/inspect`,{});
const othersBefore=[await get(dual),await get(noask)];
await page.waitForTimeout(1500);
const two=await post(`/api/tasks/${manual}/inspect`,{});
assert.deepEqual(one.observation,two.observation);
const othersAfter=[await get(dual),await get(noask)];
assert(othersAfter.some((t,i)=>t.status==='done'||t.frame.simulation_step>othersBefore[i].frame.simulation_step));
const ids=[manual,dual,noask],states=await Promise.all(ids.map(get));
assert.equal(new Set(states.map(t=>t.worker_pid)).size,3);
await page.screenshot({path:path.join(output,'console_waiting.png')});
const pending=await get(manual),qid=pending.question.id;
await page.reload({waitUntil:'domcontentloaded'});
await page.waitForFunction(({id,qid})=>window.consoleView.tasks.get(id)?.question?.id===qid,{id:manual,qid});
assert.equal((await get(manual)).frame.simulation_step,two.observation.simulation_step);
const card=page.locator(`[data-task-id="${manual}"]`);
await card.locator('select[data-role="block"]').selectOption({label:'yellow block'});
await card.locator('select[data-role="lid"]').selectOption({label:'white lid'});
const choices=await card.locator('.answer-fields select').evaluateAll(elements=>Object.fromEntries(elements.map(e=>[e.dataset.role,e.value])));
await card.getByRole('button',{name:'提交我的回答'}).click();
const duplicate=await post(`/api/tasks/${manual}/answer`,{question_id:qid,source:'human',response:{choices}});assert(duplicate.duplicate);
await page.waitForFunction(ids=>ids.every(id=>['done','error','cancelled'].includes(window.consoleView.tasks.get(id)?.status)),ids,{timeout:120000});
const finished=await Promise.all(ids.map(get));
assert(finished.every(t=>t.status==='done'),JSON.stringify(finished.map(t=>({status:t.status,error:t.error}))));
assert.equal(finished[0].evaluation.task_success,true);assert.equal(finished[1].evaluation.task_success,true);
assert.equal(finished[0].burden,2);assert.equal(finished[0].history.filter(e=>e.kind==='user_answer').length,1);
assert.equal(finished[2].history.filter(e=>e.kind==='ask').length,0);
assert(finished.every(t=>t.cost.api_attempts===0));
const frameChecks=[];
for(const t of finished){const loc=page.locator(`[data-task-id="${t.id}"]`);await page.waitForFunction(id=>{const c=window.consoleView.getCard(id);return c?.dataset.status==='done';},t.id);const image=await loc.locator('img').getAttribute('src');const sha=crypto.createHash('sha256').update(Buffer.from(image.split(',')[1],'base64')).digest('hex');assert.equal(sha,await loc.locator('img').getAttribute('data-sha256'));assert.equal(Number(await loc.getAttribute('data-frame-step')),Number(await loc.locator('img').getAttribute('data-simulation-step')));frameChecks.push({task_id:t.id,sha256:sha,simulation_step:t.frame.simulation_step,frame_matches_metadata:true});}
await page.screenshot({path:path.join(output,'console_completed.png')});
assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
const report={passed:true,evidence_kind:'scripted_policy_with_real_pybullet',task_ids:ids,independent_worker_pids:finished.map(t=>t.worker_pid),queue_limit_verified:true,queued_cancel_verified:true,
 ask_fresh_worker_observations_equal:true,ask_simulation_step:one.observation.simulation_step,browser_reconnect_preserved_question:true,other_tasks_progress_during_ask:true,duplicate_answer_ignored:true,
 manual_choices:choices,manual_success:finished[0].evaluation.task_success,dual_container_success:finished[1].evaluation.task_success,noask_actual_success:finished[2].evaluation.task_success,
 new_model_api_attempts:0,frame_checks:frameChecks,console_errors:errors,external_requests:external};
await fs.writeFile(path.join(output,'browser_validation.json'),JSON.stringify(report,null,2)+'\n');
for(const t of finished){const episode=await page.evaluate(async id=>(await fetch(`/api/tasks/${id}/episode`)).json(),t.id);await fs.writeFile(path.join(output,`${t.method}_${t.template}_episode.json`),JSON.stringify(episode,null,2)+'\n');}
await browser.close();console.log(JSON.stringify(report));
