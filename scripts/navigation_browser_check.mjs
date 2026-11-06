// Real Chromium + real PyBullet. No model/API calls in this UI regression.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const {chromium}=requireRuntime('playwright');
const out=path.join(ROOT,'outputs/navigation_dev_v1/browser');await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],external=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
await page.route('**/*',r=>{if(new URL(r.request().url()).hostname!=='127.0.0.1'){external.push(r.request().url());return r.abort();}return r.continue();});
async function rpc(url,body){return page.evaluate(async({url,body})=>{const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json();},{url,body});}
async function launch(template,method,mode,unknown,caseId){
 await page.selectOption('#template',template);await page.selectOption('#unknown',String(unknown));
 if(caseId)await page.selectOption('#navigation-case',caseId);
 await page.selectOption('#method',method);if(!method.endsWith('noask'))await page.selectOption('#answer-mode',mode);
 const res=page.waitForResponse(r=>r.url().endsWith('/api/tasks')&&r.request().method()==='POST');await page.click('#start');
 const response=await res;assert.equal(response.status(),201);return (await response.json()).id;
}
try{
 await page.goto('http://127.0.0.1:8877/',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.consoleView&&document.querySelector('#connection').textContent.includes('实时已连接'));
 const before=(await rpc('/api/meta')).budget;
 const manual=await launch('find_and_approach','scripted_ask','manual',1,'case_b');
 const autonomous=await launch('find_and_approach','scripted_noask','auto',1,'case_c');
 const tabletop=await launch('pack_and_cover','scripted_noask','auto',0);
 await page.waitForFunction(id=>window.consoleView.tasks.get(id)?.status==='waiting_answer',manual,{timeout:120000});
 const one=await rpc('/api/tasks/'+manual+'/inspect',{}),q=(await rpc('/api/tasks/'+manual)).question;
 const advancing=(await rpc('/api/tasks/'+autonomous)).frame.simulation_step;
 await page.screenshot({path:path.join(out,'01_live_navigation_queue.png'),fullPage:true});
 await page.waitForTimeout(1200);
 const two=await rpc('/api/tasks/'+manual+'/inspect',{});
 assert.deepEqual(one.observation,two.observation);
 assert.equal(one.frame.sha256,two.frame.sha256);
 assert((await rpc('/api/tasks/'+autonomous)).frame.simulation_step>advancing);
 await page.locator('#queue-list [data-task-id="'+manual+'"]').click();
 assert.equal(await page.locator('#answer-desk select[data-role="target_location"]').count(),1);
 await page.selectOption('#answer-desk select[data-role="target_location"]','living_cabinet');
 await page.reload({waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelector('#answer-desk select[data-role="target_location"]'));
 assert.equal(await page.locator('#answer-desk select[data-role="target_location"]').inputValue(),'living_cabinet');
 await page.locator('#answer-desk button').filter({hasText:'提交我的回答'}).click();
 await page.waitForFunction(ids=>ids.every(id=>['done','error','cancelled'].includes(window.consoleView.tasks.get(id)?.status)),[manual,autonomous,tabletop],{timeout:240000});
 const tasks=await Promise.all([manual,autonomous,tabletop].map(id=>rpc('/api/tasks/'+id)));
 const frames=[];
 for(const t of tasks){
  assert.equal(t.status,'done',t.error);assert.equal(t.evaluation.task_success,true,JSON.stringify(t.evaluation));
  const c=page.locator('.card[data-task-id="'+t.id+'"]'),img=c.locator('img');
  const src=await img.getAttribute('src'),sha=crypto.createHash('sha256').update(Buffer.from(src.split(',')[1],'base64')).digest('hex');
  assert.equal(sha,t.frame.sha256);assert.equal(Number(await img.getAttribute('data-simulation-step')),t.frame.simulation_step);
  const episode=await rpc('/api/tasks/'+t.id+'/episode');await fs.writeFile(path.join(out,t.method+'_'+t.template+'_episode.json'),JSON.stringify(episode,null,2)+'\n');
  frames.push({task_id:t.id,simulation_step:t.frame.simulation_step,jpeg_sha256:sha,metadata_matches:true});
 }
 assert.equal(tasks[0].burden,1);assert.equal(tasks[1].burden,0);assert.equal(tasks[0].evaluation_protocol,'fixed_world_location');
 assert.equal((await rpc('/api/meta')).budget.attempts,before.attempts);
 await page.selectOption('#template','find_and_approach');await page.screenshot({path:path.join(out,'02_navigation_success.png'),fullPage:true});
 assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
 await fs.writeFile(path.join(out,'validation.json'),JSON.stringify({evidence:'scripted_policy_real_pybullet',tasks:tasks.map(t=>({id:t.id,template:t.template,method:t.method,success:t.evaluation.task_success,burden:t.burden})),
  actual_manual_response:true,ask_freezes_physics:true,other_world_keeps_running:true,reload_preserves_answer_draft:true,frame_checks:frames,api_attempts:0,console_errors:errors,external_requests:external},null,2)+'\n');
 console.log(JSON.stringify({success:true,output:out}));
}finally{await browser.close();}
