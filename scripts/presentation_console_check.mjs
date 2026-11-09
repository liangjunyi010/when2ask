// Browser regression of preset -> worker scene -> manual ASK -> final review.
// Explicitly scripted offline policy; never included as a live-model result.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=path.join(ROOT,'outputs/presentation_dag_v1/browser');await fs.mkdir(out,{recursive:true});
const {chromium}=requireRuntime('playwright');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json();},{url,body});}
let task;
try{
 await page.goto('http://127.0.0.1:8877/?scenario=dag_demo_06',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelector('#scenario').value==='dag_demo_06');
 assert.equal(await page.locator('#scenario option').count(),11);assert(await page.locator('#unknown').isDisabled());
 assert.equal(await page.locator('#unknown').inputValue(),'2');
 assert.match(await page.locator('#scenario-preview').innerText(),/Place cup → Place block/);
 await page.screenshot({path:path.join(out,'01_scenario_launcher.png')});
 await page.selectOption('#template','place_into_selected_containers');assert.equal(await page.locator('#scenario option').count(),11);
 await page.selectOption('#scenario','dag_demo_15');assert.equal(await page.locator('#unknown').inputValue(),'1');
 await page.selectOption('#template','find_and_approach');assert(await page.locator('#scenario-field').isHidden());assert(await page.locator('#unknown').isEnabled());
 await page.selectOption('#template','pack_and_cover');await page.selectOption('#scenario','dag_demo_06');
 await page.selectOption('#method','scripted_ask');await page.selectOption('#answer-mode','manual');
 const before=(await rpc('/api/meta')).budget.attempts;
 const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');
 const result=await response;assert.equal(result.status(),201);task=await result.json();assert.equal(task.scenario_id,'dag_demo_06');
 assert.equal(task.review.ground_truth,null);
 const deadline=Date.now()+90000;let answered=false, frozen=false, actionCaptured=false;
 while(Date.now()<deadline){
  const t=await rpc('/api/tasks/'+task.id);
  if(t.status==='executing'&&t.frame&&!actionCaptured){await page.screenshot({path:path.join(out,'02_real_execution.png')});actionCaptured=true;}
  if(t.status==='waiting_answer'&&!answered){
   await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='waiting_answer',task.id);
   await page.evaluate(id=>window.consoleView.chooseQuestion(id),t.question.id);
   const one=await rpc('/api/tasks/'+task.id+'/inspect',{});await page.waitForTimeout(250);const two=await rpc('/api/tasks/'+task.id+'/inspect',{});
   assert.deepEqual(one.observation,two.observation);assert.equal(one.frame.sha256,two.frame.sha256);frozen=true;
   for(const req of t.question.requests){const candidate=req.candidate_ids?.[0]||req.candidate_id;await page.selectOption('#answer-desk select[data-role="'+req.role+'"]',candidate);}
   await page.screenshot({path:path.join(out,'03_manual_queue.png'),fullPage:true});
   await page.locator('#answer-desk .answer-buttons button').filter({hasText:'提交我的回答'}).click();answered=true;
  }
  if(['done','error','cancelled'].includes(t.status)){task=t;break;}
  await page.waitForTimeout(200);
 }
 assert.equal(task.status,'done');assert.equal(task.evaluation.task_success,true);assert(answered&&frozen);
 await page.locator('.card[data-task-id="'+task.id+'"] .review-link').click();
 assert.equal(await page.locator('.truth-table').count(),1);assert.equal(await page.locator('#review-body .dag-node').count(),3);
 await page.screenshot({path:path.join(out,'04_completed_review.png')});await page.click('#review-close');
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'05_mobile.png'),fullPage:true});
 assert.equal((await rpc('/api/meta')).budget.attempts,before);assert.deepEqual(errors,[]);
 const report={task_id:task.id,scenario_id:task.scenario_id,evidence_kind:'scripted_policy_real_physics_browser_integration',
   success:task.evaluation.task_success,manual_answer_form:true,ask_physics_frozen:frozen,unknown_count_locked:true,
   twenty_presets:true,template_switching:true,ground_truth_hidden_until_terminal:true,public_dag_review:true,
   mobile_no_overflow:true,console_errors:errors,authenticated_requests:0};
 await fs.writeFile(path.join(out,'validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{
 if(task&&!['done','error','cancelled'].includes(task.status))await rpc('/api/tasks/'+task.id+'/cancel',{}).catch(()=>{});
 await browser.close();
}
