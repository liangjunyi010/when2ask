// Read-only final console and recorded-case QA: no model requests or task launches.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=path.join(ROOT,'outputs/six_tasks_dev_v1'),evidence=JSON.parse(await fs.readFile(path.join(out,'live_validation.json'),'utf8'));
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
try{
 const retrieval=evidence.rows.find(r=>r.template==='retrieve_restore');
 await page.goto('http://127.0.0.1:8877/?review='+retrieval.id,{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>document.querySelector('#task-review').open);
 assert.equal(await page.locator('#template option').count(),9);
 const text=await page.locator('#review-body').innerText();assert.match(text,/0\.26/);assert.match(text,/0\.79/);assert.match(text,/Which item/);
 assert(!text.includes('undefined'));await page.screenshot({path:path.join(out,'browser/05_real_jev_review.png')});await page.click('#review-close');
 const tasks=await page.evaluate(()=>fetch('/api/tasks').then(r=>r.json()));
 for(const row of evidence.rows){const t=tasks.tasks.find(t=>t.id===row.id);assert(t?.archived_readonly);assert.equal(t.evaluation.task_success,row.task_success);}
 await page.selectOption('#template','patrol_return');await page.screenshot({path:path.join(out,'browser/06_interactive_nine_templates.png'),fullPage:true});
 await page.goto('http://127.0.0.1:8892/',{waitUntil:'domcontentloaded'});assert.equal(await page.locator('article').count(),6);
 for(const template of evidence.rows.map(r=>r.template)){
  const video=page.locator('#'+template+' video');await video.evaluate(v=>v.load());await video.evaluate(v=>new Promise((resolve,reject)=>{if(v.readyState>=1)return resolve();v.addEventListener('loadedmetadata',resolve,{once:true});v.addEventListener('error',reject,{once:true});}));
  assert(await video.evaluate(v=>v.videoWidth>0&&v.duration>1));assert.equal(await video.evaluate(v=>v.playbackRate),3);
  await video.evaluate(async v=>{await v.play();v.pause();await new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=Math.min(3,v.duration/2);});});
 }
 await page.screenshot({path:path.join(out,'browser/07_recorded_case_gallery.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'browser/08_gallery_mobile.png'),fullPage:true});
 assert.deepEqual(errors,[]);const result={nine_templates:true,six_real_archived_cases:true,retrieval_probabilities_match_raw:[.26,.79],
    six_mp4s_actually_decoded:true,uniform_playback_rate:3,play_pause_seek:true,mobile_no_overflow:true,console_errors:errors,authenticated_requests:0};
 await fs.writeFile(path.join(out,'browser/readonly_validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser.close();}
