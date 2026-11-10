// Six real-model cases through the actual HTML/controller/worker system.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Explicit --live required');
const out=path.join(ROOT,'outputs/six_tasks_dev_v1'),session=path.join(ROOT,'outputs/local_console/task6-live-v1');
const plan=JSON.parse(await fs.readFile(path.join(out,'live_plan.json'),'utf8'));
await fs.mkdir(path.join(out,'live'),{recursive:false}); // Refuse accidental whole-study reruns.
for(const [name,digest]of Object.entries(plan.source_hashes))assert.equal(crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,'src/when2ask',name))).digest('hex'),digest,'Changed source after lock: '+name);
assert.equal(crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,'data/six_tasks_dev_v1/samples.json'))).digest('hex'),plan.dataset_sha256);
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],created=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json();},{url,body});}
try{
 await page.goto('http://127.0.0.1:8891/',{waitUntil:'domcontentloaded'});await page.waitForSelector('#new-task-options option',{state:'attached'});
 const before=await rpc('/api/meta');assert.equal(before.budget.attempts,0);assert.equal(before.budget.max_episodes,6);assert.equal(before.budget.max_attempts,120);assert.deepEqual(before.models,plan.configuration);
 for(const job of plan.jobs){
  await page.selectOption('#template',job.template);await page.selectOption('#unknown','1');await page.selectOption('#method',job.method);if(job.method!=='llm_noask')await page.selectOption('#answer-mode','auto');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');const res=await response;assert.equal(res.status(),201);const t=await res.json();created.push({id:t.id,...job});console.log(JSON.stringify({launched:t.id,...job}));
 }
 const deadline=Date.now()+600000;
 while(Date.now()<deadline){
  const tasks=(await rpc('/api/tasks')).tasks.filter(t=>created.some(c=>c.id===t.id));
  if(tasks.length===6&&tasks.every(t=>['done','error','cancelled'].includes(t.status)))break;
  await page.waitForTimeout(500);
 }
 const final=await Promise.all(created.map(c=>rpc('/api/tasks/'+c.id)));assert(final.every(t=>['done','error','cancelled'].includes(t.status)),'Timed out; preserve partial traces');
 for(const t of final){
  const dest=path.join(out,'live',t.template);await fs.mkdir(dest,{recursive:false});
  for(const name of ['episode.json','evaluation.json','api_attempts.jsonl','review.json','final_view.json']){
   try{await fs.copyFile(path.join(session,'tasks',t.id,name),path.join(dest,name));}catch(e){if(name!=='api_attempts.jsonl')throw e;}
  }
  if(t.frame)await fs.writeFile(path.join(dest,'final.jpg'),Buffer.from(t.frame.jpeg,'base64'));
  await page.locator('.card[data-task-id="'+t.id+'"] .review-link').click();await page.screenshot({path:path.join(dest,'review.png')});await page.click('#review-close');
 }
 const budget=(await rpc('/api/meta')).budget;assert.equal(budget.episodes,6);assert(budget.attempts<=120);
 assert(final.filter(t=>t.method==='llm_noask').every(t=>t.ask_turns===0));
 await page.screenshot({path:path.join(out,'live_wall.png'),fullPage:true});
 const result={evidence_kind:'live_models_real_pybullet_via_actual_browser',created,authenticated_requests:budget.attempts,
  episode_count:6,console_errors:errors,rows:final.map(t=>({id:t.id,template:t.template,method:t.method,status:t.status,task_success:t.evaluation?.task_success,
    burden:t.burden,ask_turns:t.ask_turns,actions:t.actions.length,error:t.error,cost:t.cost,returned_models:t.returned_models}))};
 await fs.writeFile(path.join(out,'live_validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser.close();}
