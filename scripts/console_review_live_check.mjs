// Exactly one real-model run per task template. No policy overrides or extra retries.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Requires explicit --live');
const out=path.join(ROOT,'outputs/console_review_v1'),session=path.join(ROOT,'outputs/local_console/clarification-review-v1');
const plan=JSON.parse(await fs.readFile(path.join(out,'plan.json'),'utf8'));
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],answered=[],ids=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json();},{url,body});}
function answerText(q){return q.requests.map(r=>{
 const ids=r.candidate_ids||[r.candidate_id];const known=q.known_choices?.[r.role];
 const preferred={cup:'blue cup',block:'green block',lid:'black lid'}[r.role];
 const selected=known||ids.find(id=>q.candidates[id]===preferred)||ids[0];
 return q.candidates[selected]||selected;
}).join(', ');}
try{
 await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
 const before=(await rpc('/api/meta')).budget;assert.equal(before.attempts,0);assert.equal(before.max_episodes,3);
 for(const c of plan.cases){
  await page.selectOption('#template',c.template);await page.selectOption('#unknown',String(c.unknown_preferences));if(c.navigation_case)await page.selectOption('#navigation-case',c.navigation_case);
  await page.selectOption('#method',c.method);if(c.answer_mode==='manual')await page.selectOption('#answer-mode','manual');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const res=await response;assert.equal(res.status(),201);const t=await res.json();ids.push(t.id);
  assert.equal(t.review.ground_truth,null);assert.equal(t.review.original_instruction,t.instruction);
 }
 await page.locator('.card[data-task-id="'+ids[0]+'"] .review-link').click();
 assert.match(await page.locator('#review-body').innerText(),/任务结束后才揭示/);await page.screenshot({path:path.join(out,'01_original_instruction.png')});await page.click('#review-close');
 const deadline=Date.now()+240000;
 while(Date.now()<deadline){
  const tasks=(await rpc('/api/tasks')).tasks.filter(t=>ids.includes(t.id));
  for(const t of tasks.filter(t=>t.status==='waiting_answer'&&t.question)){
   const q=t.question;if(answered.some(a=>a.question_id===q.id))continue;
   assert.equal(t.answer_mode,'manual');await page.evaluate(qid=>window.consoleView.chooseQuestion(qid),q.id);
   const one=await rpc('/api/tasks/'+t.id+'/inspect',{});
   let submitted;
   if(q.type==='confirm'){
    for(const r of q.requests)await page.selectOption('#answer-desk select[data-role="'+r.role+'"]',q.known_choices?.[r.role]?String(q.known_choices[r.role]===r.candidate_id):'true');
   }else{
    submitted=answerText(q);await page.fill('#answer-desk textarea',submitted);
    await page.reload({waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.consoleView);
    await page.waitForFunction(qid=>[...window.consoleView.tasks.values()].some(t=>t.question?.id===qid),q.id);
    await page.evaluate(qid=>window.consoleView.chooseQuestion(qid),q.id);
    assert.equal(await page.locator('#answer-desk textarea').inputValue(),submitted);
   }
   const two=await rpc('/api/tasks/'+t.id+'/inspect',{});assert.deepEqual(one.observation,two.observation);assert.equal(one.frame.sha256,two.frame.sha256);
   await page.screenshot({path:path.join(out,'02_manual_queue_'+t.method+'.png'),fullPage:true});
   await page.locator('#answer-desk .answer-buttons button').filter({hasText:'提交我的回答'}).click();
   await page.waitForFunction(({id,qid})=>window.consoleView.tasks.get(id)?.question?.id!==qid,{id:t.id,qid:q.id});
   if(submitted)assert.equal((await rpc('/api/tasks/'+t.id+'/answer',{question_id:q.id,source:'human',response:{text:submitted}})).duplicate,true);
   answered.push({task_id:t.id,method:t.method,question_id:q.id,input_text:submitted,physics_frozen:true,source:'browser_automation_acting_as_manual_operator'});
  }
  if(tasks.length===3&&tasks.every(t=>['done','error','cancelled'].includes(t.status)))break;
  await page.waitForTimeout(400);
 }
 const final=await Promise.all(ids.map(id=>rpc('/api/tasks/'+id)));
 assert(final.every(t=>['done','error','cancelled'].includes(t.status)),'Episode timeout');
 for(const t of final){
  assert(t.review.ground_truth&&t.review.truth_revealed);
  const dest=path.join(out,t.template);await fs.mkdir(dest,{recursive:true});
  for(const file of ['episode.json','api_attempts.jsonl','review.json']){try{await fs.copyFile(path.join(session,'tasks',t.id,file),path.join(dest,file));}catch(e){if(file==='api_attempts.jsonl')throw e;}}
  await fs.writeFile(path.join(dest,'final.jpg'),Buffer.from(t.frame.jpeg,'base64'));
  await page.locator('.card[data-task-id="'+t.id+'"] .review-link').click();assert.equal(await page.locator('.original-instruction').textContent(),t.instruction);
  assert.equal(await page.locator('.truth-table').count(),1);assert.equal(await page.locator('.conversation-event').count(),t.review.conversation.length);
  await page.screenshot({path:path.join(dest,'review.png'),fullPage:true});await page.click('#review-close');
 }
 const noask=final.find(t=>t.method==='llm_noask');assert.equal(noask.ask_turns,0);assert.match(noask.review.interaction.message,/NoAsk/);
 const budget=(await rpc('/api/meta')).budget;assert.equal(budget.episodes,3);assert(budget.attempts<=60);
 assert.deepEqual(errors,[]);await page.screenshot({path:path.join(out,'03_final_wall.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'04_mobile.png'),fullPage:true});
 const summary={rows:final.map(t=>({task_id:t.id,template:t.template,method:t.method,status:t.status,success:t.evaluation?.task_success,burden:t.burden,ask_turns:t.ask_turns,error:t.error,cost:t.cost})),answered,authenticated_requests:budget.attempts,
  episode_count:3,truth_hidden_until_terminal:true,full_conversation_persisted:true,actual_text_form:answered.some(a=>a.input_text),console_errors:errors,scope:plan.scope};
 await fs.writeFile(path.join(out,'validation.json'),JSON.stringify(summary,null,2)+'\n');console.log(JSON.stringify(summary));
}finally{await browser.close();}
