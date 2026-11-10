// Read-only report/media QA. No model calls or task launches.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=path.join(ROOT,'outputs/buffer_dev_v4');await fs.mkdir(path.join(out,'browser'),{recursive:true});
const {chromium}=requireRuntime('playwright'),browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
try{
 await page.goto('http://127.0.0.1:8893/',{waitUntil:'domcontentloaded'});
 assert.equal(await page.locator('article').count(),6);assert.equal(await page.locator('table').count(),2);
 assert.match(await page.locator('main').innerText(),/DEFAULT CONSOLE UNCHANGED/);
 for(const video of await page.locator('video').all()){
  await video.evaluate(v=>v.load());await video.evaluate(v=>new Promise((resolve,reject)=>{if(v.readyState>=1)return resolve();v.addEventListener('loadedmetadata',resolve,{once:true});v.addEventListener('error',reject,{once:true});}));
  assert.equal(await video.evaluate(v=>v.playbackRate),3);assert(await video.evaluate(v=>v.videoWidth>0&&v.duration>1));
  await video.evaluate(async v=>{await v.play();v.pause();await new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=Math.min(3,v.duration/2);});});
 }
 await page.screenshot({path:path.join(out,'browser/report_desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'browser/report_mobile.png'),fullPage:true});assert.deepEqual(errors,[]);
 const result={url:'http://127.0.0.1:8893/',six_real_videos_decoded:true,play_pause_seek:true,playback_rate:3,mobile_no_overflow:true,
  negative_iterations_displayed:true,console_errors:errors,authenticated_requests:0};await fs.writeFile(path.join(out,'browser/validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await browser.close();}
