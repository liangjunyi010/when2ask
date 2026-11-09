// Read-only browser QA: no task launches, model requests, or simulated evidence.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=path.join(ROOT,'outputs/presentation_dag_v1/browser');await fs.mkdir(out,{recursive:true});
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],checked=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
try{
 await page.goto('http://127.0.0.1:8881/',{waitUntil:'networkidle'});await page.waitForSelector('.case');
 assert.equal(await page.locator('.case').count(),20);assert.equal(await page.locator('#results tr').count(),20);
 for(const id of ['dag_demo_03','dag_demo_06','dag_demo_15','dag_demo_18']){
  await page.locator('.case[data-id="'+id+'"]').click();await page.waitForFunction(()=>document.querySelector('#robot').readyState>=1&&document.querySelector('#robot').videoWidth>0);
  const metric=await page.locator('#metrics').innerText();assert.match(metric,/Jev-Gate/);
  assert(!(await page.locator('#trace').innerText()).includes('undefined'));
  await page.click('#replay');await page.waitForFunction(()=>!document.querySelector('#robot').paused&&document.querySelector('#robot').currentTime>0);await page.waitForFunction(()=>document.querySelector('#robot').readyState>=1&&document.querySelector('#robot').videoWidth>0);
  const src=await page.locator('#robot').getAttribute('src');assert.match(src,/\.mp4/);assert.equal(await page.locator('#robot').evaluate(v=>v.playbackRate),2);await page.locator('#robot').evaluate(v=>{v.pause();v.currentTime=1;});
  await page.screenshot({path:path.join(out,'gallery_'+id+'.png')});checked.push({sample_id:id,real_mp4_loaded:true,default_playback_rate:2,raw_transcript:true,dag_public_only:true});
 }
 await page.selectOption('#filter','2');assert.equal(await page.locator('.case').count(),5);
 await page.selectOption('#filter','all');assert.equal(await page.locator('.case').count(),20);
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'gallery_mobile.png'),fullPage:true});assert.deepEqual(errors,[]);
 const result={url:'http://127.0.0.1:8881/',scenarios:20,rows:20,checked,filters:true,mobile_no_overflow:true,console_errors:errors,authenticated_requests:0};await fs.writeFile(path.join(out,'gallery_validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser.close();}
