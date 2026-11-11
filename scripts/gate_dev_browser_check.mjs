// Offline scripted policies with real physics; six manual-mode UI regressions.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=path.join(ROOT,'outputs/gate_diagnostics_dev_v7/browser');await fs.mkdir(out,{recursive:true});
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],answered=[],ids=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json();},{url,body});}
try{
 await page.goto('http://127.0.0.1:8899/',{waitUntil:'domcontentloaded'});await page.waitForSelector('#new-task-options option',{state:'attached'});
 assert.equal(await page.locator('#template option').count(),9);
 const meta=await rpc('/api/meta');assert.equal(meta.live_enabled,false);assert.equal(meta.new_tasks.length,6);assert(meta.planner_profiles.some(p=>p.id==='grounded_dev_v5'));assert(meta.planner_profiles.some(p=>p.id==='gate_dev_v7'));assert.equal(await page.locator('#planner-profile').inputValue(),'default_v1');
 for(const template of ['buffer_exchange','retrieve_restore','occlusion_inspection']){
  await page.selectOption('#template',template);assert(await page.locator('#scenario-field').isHidden());
  assert.equal(await page.locator('#unknown').inputValue(),'1');assert(await page.locator('#scenario-preview').isVisible());
  await page.selectOption('#planner-profile','gate_dev_v7');await page.selectOption('#method','scripted_ask');await page.selectOption('#answer-mode','manual');
  if(template==='buffer_exchange')await page.screenshot({path:path.join(out,'01_new_task_launcher.png')});
  const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const r=await response;assert.equal(r.status(),201);const t=await r.json();ids.push(t.id);assert.equal(t.review.ground_truth,null);
 }
 const deadline=Date.now()+300000;let freezeChecks=0,queueCaptured=false;
 while(Date.now()<deadline){
  const tasks=(await rpc('/api/tasks')).tasks.filter(t=>ids.includes(t.id));
  for(const t of tasks.filter(t=>t.status==='waiting_answer'&&t.question)){
   assert.equal(t.planner_profile,'gate_dev_v7');const q=t.question;if(answered.some(a=>a.question_id===q.id))continue;
   await page.waitForFunction(qid=>[...window.consoleView.tasks.values()].some(t=>t.question?.id===qid),q.id);
   await page.evaluate(id=>window.consoleView.chooseQuestion(id),q.id);
   const before=await rpc('/api/tasks/'+t.id+'/inspect',{});await page.waitForTimeout(150);const after=await rpc('/api/tasks/'+t.id+'/inspect',{});
   assert.deepEqual(before.observation,after.observation);assert.equal(before.frame.sha256,after.frame.sha256);freezeChecks++;
   const choices={};for(const req of q.requests){const selected=req.candidate_ids[0];choices[req.role]=selected;await page.selectOption('#answer-desk select[data-role="'+req.role+'"]',selected);}
   if(!queueCaptured){await page.screenshot({path:path.join(out,'02_manual_clarification_queue.png'),fullPage:true});queueCaptured=true;}
   await page.locator('#answer-desk .answer-buttons button').filter({hasText:'提交我的回答'}).click();
   answered.push({task_id:t.id,template:t.template,question_id:q.id,choices,physics_frozen:true,source:'browser_automation_acting_as_manual_operator'});
  }
  if(tasks.length===3&&tasks.every(t=>['done','error','cancelled'].includes(t.status)))break;
  await page.waitForTimeout(250);
 }
 const final=(await rpc('/api/tasks')).tasks.filter(t=>ids.includes(t.id));assert.equal(final.length,3);
 assert(final.every(t=>t.status==='done'),JSON.stringify(final.map(t=>({task:t.template,status:t.status,error:t.error}))));
 assert(final.every(t=>t.evaluation.task_success),JSON.stringify(final.map(t=>({task:t.template,conditions:t.evaluation.conditions}))));
 assert.equal(freezeChecks,2);assert.equal(final.find(t=>t.template==='occlusion_inspection').ask_turns,0);
 assert(final.every(t=>t.review.ground_truth));await page.screenshot({path:path.join(out,'03_six_completed_worlds.png'),fullPage:true});
 for(const t of final){await page.locator('.card[data-task-id="'+t.id+'"] .review-link').click();assert.equal(await page.locator('.truth-table').count(),1);assert(!(await page.locator('#review-body').innerText()).includes('undefined'));await page.screenshot({path:path.join(out,'review_'+t.template+'.png')});await page.click('#review-close');}
 await page.selectOption('#template','pack_and_cover');assert.equal(await page.locator('#planner-profile').inputValue(),'default_v1');assert(await page.locator('#planner-profile option[value=gate_dev_v7]').evaluate(el=>el.disabled));await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'04_mobile.png'),fullPage:true});
 assert.equal((await rpc('/api/meta')).budget.attempts,0);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'validation.json'),JSON.stringify({evidence_kind:'scripted_policy_real_physics_browser_regression',task_count:3,
  successes:final.filter(t=>t.evaluation.task_success).length,manual_answers:answered,freeze_checks:freezeChecks,occlusion_no_ask:true,ground_truth_after_completion:true,
  no_undefined_action_labels:true,console_errors:errors,mobile_no_overflow:true,authenticated_requests:0,rows:final.map(t=>({id:t.id,template:t.template,success:t.evaluation.task_success,burden:t.burden}))},null,2)+'\n');
 console.log(JSON.stringify({successes:3,freeze_checks:freezeChecks,errors,authenticated_requests:0}));
}finally{
 for(const id of ids){const t=await rpc('/api/tasks/'+id).catch(()=>null);if(t&&!['done','error','cancelled'].includes(t.status))await rpc('/api/tasks/'+id+'/cancel',{}).catch(()=>{});}
 await browser.close();
}
