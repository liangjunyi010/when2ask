// Explicit opt-in. Real model outputs drive each action through the existing HTML.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Requires --live and a prepared bounded plan');
const out=path.join(ROOT,'outputs/navigation_dev_v1/live_v1'),session=path.join(ROOT,'outputs/local_console/navigation-pilot-v1');
execFileSync(path.join(ROOT,'.venv/bin/python'),['scripts/navigation_pilot.py','check'],{cwd:ROOT});
const plan=JSON.parse(await fs.readFile(path.join(out,'plan.json'),'utf8'));
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto('http://127.0.0.1:8878/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
 const meta=await page.evaluate(()=>fetch('/api/meta').then(r=>r.json()));
 assert.equal(meta.budget.max_attempts,plan.max_authenticated_requests);assert.equal(meta.budget.max_episodes,plan.max_new_episodes);
 assert.equal(meta.budget.attempts,0,'Refuse to resume/re-run paid study implicitly');
 for(const caseId of plan.scenario_order){
  await page.selectOption('#template','find_and_approach');await page.selectOption('#navigation-case',caseId);await page.selectOption('#unknown','1');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.click('#compare-start');const res=await response;assert.equal(res.status(),201,await res.text());const group=await res.json();
  console.log(JSON.stringify({case:caseId,comparison:group.id,event:'started'}));
  await fs.mkdir(path.join(out,'comparisons'),{recursive:true});
  await page.waitForFunction(ids=>ids.every(id=>['done','error','cancelled'].includes(window.consoleView.tasks.get(id)?.status)),group.task_ids,{timeout:480000});
  await page.waitForTimeout(500);
  const result=await page.evaluate(id=>fetch('/api/comparisons/'+id).then(r=>r.json()),group.id);
  await fs.writeFile(path.join(out,'comparisons',caseId+'.json'),JSON.stringify(result,null,2)+'\n');
  for(const id of group.task_ids){
   const dest=path.join(out,'episodes',id);await fs.mkdir(dest,{recursive:true});
   for(const file of ['episode.json','api_attempts.jsonl','evaluation.json']){
    try{await fs.copyFile(path.join(session,'tasks',id,file),path.join(dest,file));}catch(e){if(file==='evaluation.json')continue;throw e;}
   }
   const t=await page.evaluate(id=>fetch('/api/tasks/'+id).then(r=>r.json()),id);
   if(t.frame)await fs.writeFile(path.join(dest,'final.jpg'),Buffer.from(t.frame.jpeg,'base64'));
  }
  await page.screenshot({path:path.join(out,caseId+'_comparison.png'),fullPage:true});
  const budget=(await page.evaluate(()=>fetch('/api/meta').then(r=>r.json()))).budget;
  await fs.writeFile(path.join(out,'budget.json'),JSON.stringify(budget,null,2)+'\n');
  console.log(JSON.stringify({case:caseId,rows:result.rows.map(r=>({method:r.method,success:r.task_success,burden:r.burden,distance:r.distance_m,error:r.error})),attempts:budget.attempts,event:'complete'}));
  if(Object.values(budget.backends).some(b=>b.blocked)||budget.attempts>=plan.max_authenticated_requests)break;
 }
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(out,'browser_validation.json'),JSON.stringify({console_errors:errors,one_click_three_method_launch:true,actual_chromium_render:true},null,2)+'\n');
 console.log(execFileSync(path.join(ROOT,'.venv/bin/python'),['scripts/navigation_pilot.py','report'],{cwd:ROOT,encoding:'utf8'}));
}finally{await browser.close();}
