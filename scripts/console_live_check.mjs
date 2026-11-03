// Explicitly bounded three real-model interactive demos. Does not run Test data.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
if(!process.argv.includes('--live'))throw Error('Requires --live; consumes the separate console inference budget');
const si=process.argv.indexOf('--session-dir');if(si<0||!process.argv[si+1])throw Error('Supply --session-dir for the matching controller output directory');
const sessionDir=path.resolve(process.argv[si+1]);
const {chromium}=requireRuntime('playwright');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
const ids=[];
for(const method of ['llm_noask','llm_gate','jev_gate']){
 await page.selectOption('#template','pack_and_cover');await page.selectOption('#method',method);
 if(method!=='llm_noask')await page.selectOption('#answer-mode','auto');
 const response=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');
 await page.click('#start');const r=await response;assert.equal(r.status(),201);
 const t=await r.json();ids.push(t.id);console.log(JSON.stringify({started:t.id,method}));
}
const output=path.join(ROOT,'outputs/console_evidence');await fs.mkdir(output,{recursive:true});
await fs.writeFile(path.join(ROOT,'outputs/local_console/live_ids.json'),JSON.stringify(ids));
await page.waitForFunction(ids=>ids.every(id=>window.consoleView.tasks.get(id)?.frame),ids,{timeout:90000});
await page.screenshot({path:path.join(output,'live_three_methods.png')});
await page.waitForFunction(ids=>ids.every(id=>['done','error','cancelled'].includes(window.consoleView.tasks.get(id)?.status)),ids,{timeout:240000});
const results=[];
for(const id of ids){
 const t=await page.evaluate(async id=>(await fetch('/api/tasks/'+id)).json(),id);
 const episode=await page.evaluate(async id=>(await fetch('/api/tasks/'+id+'/episode')).json(),id);
 const attempts=(await fs.readFile(path.join(sessionDir,'tasks',id,'api_attempts.jsonl'),'utf8')).trim().split('\n').filter(Boolean).map(JSON.parse);
 episode.api_attempts=attempts;
 await fs.writeFile(path.join(output,'live_'+t.method+'_episode.json'),JSON.stringify(episode,null,2)+'\n');
 results.push({id,method:t.method,status:t.status,task_success:t.evaluation?.task_success??null,burden:t.burden,
  action_count:t.actions.length,api_attempts:t.cost.api_attempts,cost:t.cost,error:t.error,
  returned_models:[...new Set(attempts.map(a=>a.returned_model).filter(Boolean))]});
}
await page.screenshot({path:path.join(output,'live_results.png')});
const budget=await page.evaluate(async()=>(await(await fetch('/api/meta')).json()).budget);
const report={evidence_kind:'real_model_api_with_real_pybullet',formal_test_episodes:0,results,budget,console_errors:errors};
await fs.writeFile(path.join(output,'live_validation.json'),JSON.stringify(report,null,2)+'\n');
await browser.close();console.log(JSON.stringify(report));
