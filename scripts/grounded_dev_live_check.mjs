// Explicitly live: exactly three paired groups, using actual HTML controls.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Explicit --live required');
const out=path.join(ROOT,'outputs/grounded_planner_dev_v5'),session=path.join(ROOT,'outputs/local_console/grounded-dev-v5-live');
const plan=JSON.parse(await fs.readFile(path.join(out,'live_plan.json'),'utf8'));
await fs.mkdir(path.join(out,'live'),{recursive:false}); // Never rerun or overwrite.
for(const [name,digest]of Object.entries(plan.source_hashes))assert.equal(crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,name))).digest('hex'),digest,'Source changed after freeze: '+name);
assert.equal(crypto.createHash('sha256').update(await fs.readFile(path.join(ROOT,'data/six_tasks_dev_v1/samples.json'))).digest('hex'),plan.dataset_sha256);
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],created=[],comparisons=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
async function rpc(url){return page.evaluate(async url=>{const r=await fetch(url);if(!r.ok)throw Error(await r.text());return r.json();},url);}
try{
 await page.goto('http://127.0.0.1:8894/',{waitUntil:'domcontentloaded'});await page.waitForSelector('#new-task-options option',{state:'attached'});
 const before=await rpc('/api/meta');assert.equal(before.budget.attempts,0);assert.equal(before.budget.episodes,0);assert.equal(before.budget.max_episodes,9);assert.equal(before.budget.max_attempts,150);assert.deepEqual(before.models,plan.configuration);
 assert.equal(await page.locator('#planner-profile').inputValue(),'default_v1');
 for(const job of plan.groups){
  await page.selectOption('#template',job.template);await page.selectOption('#unknown','1');await page.selectOption('#planner-profile',plan.planner_profile);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');await page.click('#compare-start');const res=await response;assert.equal(res.status(),201);const group=await res.json();
  assert.equal(group.planner_profile,plan.planner_profile);assert.deepEqual(group.prompt_hashes,plan.prompt_hashes);
  comparisons.push(group.id);for(const id of group.task_ids)created.push({id,template:job.template,comparison_id:group.id});
  console.log(JSON.stringify({launched:job.template,comparison:group.id,ids:group.task_ids}));
  const deadline=Date.now()+600000;
  while(Date.now()<deadline){const g=await rpc('/api/comparisons/'+group.id);if(g.status==='complete')break;await page.waitForTimeout(1000);}
  const finalGroup=await rpc('/api/comparisons/'+group.id);assert.equal(finalGroup.status,'complete','Timeout; preserve partial results, do not rerun');
  await fs.writeFile(path.join(out,'live',job.template+'.comparison.json'),JSON.stringify(finalGroup,null,2)+'\n');
  await page.screenshot({path:path.join(out,'live',job.template+'.png'),fullPage:true});
  for(const id of group.task_ids){
   const t=await rpc('/api/tasks/'+id);assert.equal(t.planner_profile,plan.planner_profile);
   const dest=path.join(out,'live',t.template+'__'+t.method);await fs.mkdir(dest,{recursive:false});
   for(const name of ['episode.json','evaluation.json','api_attempts.jsonl','review.json','final_view.json'])await fs.copyFile(path.join(session,'tasks',id,name),path.join(dest,name));
   if(t.frame)await fs.writeFile(path.join(dest,'final.jpg'),Buffer.from(t.frame.jpeg,'base64'));
   await page.locator('.card[data-task-id="'+t.id+'"] .review-link').click();await page.screenshot({path:path.join(dest,'review.png')});await page.click('#review-close');
   console.log(JSON.stringify({completed:t.id,template:t.template,method:t.method,success:t.evaluation?.task_success,burden:t.burden,actions:t.actions.length,attempts:t.cost.api_attempts,error:t.error}));
  }
 }
 const budget=(await rpc('/api/meta')).budget;assert.equal(budget.episodes,9);assert(budget.attempts<=150);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'live_validation.json'),JSON.stringify({evidence_kind:'live_models_real_pybullet_actual_html',created,comparisons,episodes:9,authenticated_requests:budget.attempts,console_errors:errors},null,2)+'\n');
 console.log(JSON.stringify({episodes:9,authenticated_requests:budget.attempts,console_errors:errors}));
}finally{await browser.close();}
