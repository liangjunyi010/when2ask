// Actual Chrome renders all recorded cases and decodes all nine real MP4s.
import fs from 'node:fs/promises';import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const out=ROOT+'outputs/three_task_v8/browser';await fs.mkdir(out,{recursive:true});const browser=await requireRuntime('playwright').chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],decoded=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
try{
 await page.goto('http://127.0.0.1:8900/',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.galleryReady===true);assert.equal(await page.locator('#results tr').count(),3);await page.screenshot({path:out+'/01_results.png'});
 const ids=await page.locator('#case option').evaluateAll(os=>os.map(o=>o.value));assert.equal(ids.length,3);
 for(const id of ids){await page.selectOption('#case',id);await page.waitForFunction(id=>window.galleryCaseReady===id,id);await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=2&&v.videoWidth>0));
  const videos=await page.locator('video').evaluateAll(vs=>vs.map(v=>({src:v.src,width:v.videoWidth,height:v.videoHeight,duration:v.duration})));assert.equal(videos.length,3);decoded.push({id,videos});
  await page.locator('#recordings').scrollIntoViewIfNeeded();await page.screenshot({path:out+'/'+id+'.png'});
 }
 await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8900/');await page.waitForFunction(()=>window.galleryReady===true);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:out+'/02_mobile.png',fullPage:true});assert.deepEqual(errors,[]);
 await fs.writeFile(out+'/validation.json',JSON.stringify({evidence:'actual_Chrome_render_and_MP4_decode',recorded_cases:3,decoded_videos:decoded,mobile_no_overflow:true,errors,api_requests_added:0},null,2)+'\n');console.log(JSON.stringify({cases:3,videos:9,errors,model_requests:0}));
}finally{await browser.close();}
