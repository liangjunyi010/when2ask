import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../../milestone/tools/runtime.mjs';
const {chromium}=requireRuntime('playwright');
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],failed=[];
page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>failed.push(r.url()));
try{
 await page.goto('http://127.0.0.1:8909/',{waitUntil:'networkidle'});
 await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
 const meta=await page.evaluate(()=>{const v=document.querySelector('video');v.pause();return {duration:v.duration,width:v.videoWidth,height:v.videoHeight,readyState:v.readyState};});
 assert.equal(meta.duration,50);assert.equal(meta.width,1920);assert.equal(meta.height,1080);
 for(const at of [0,10,16,19,36,48]){
  await page.evaluate(at=>new Promise(resolve=>{const v=document.querySelector('video');if(v.currentTime===at){resolve();return;}v.addEventListener('seeked',resolve,{once:true});v.currentTime=at;}),at);
  assert(await page.evaluate(()=>!document.querySelector('video').error));
 }
 await page.screenshot({path:path.join(ROOT,'presentation/command_center_demo_v1/screenshots/browser_player.png')});
 await page.evaluate(()=>{const v=document.querySelector('video');v.currentTime=0;v.playbackRate=1;v.play();});
 await page.waitForFunction(()=>document.querySelector('video').ended,null,{timeout:60000});
 const playback=await page.evaluate(()=>{const v=document.querySelector('video');return {ended:v.ended,currentTime:v.currentTime,error:v.error,quality:v.getVideoPlaybackQuality().toJSON?.()||{totalVideoFrames:v.getVideoPlaybackQuality().totalVideoFrames,droppedVideoFrames:v.getVideoPlaybackQuality().droppedVideoFrames}};});
 assert.equal(playback.ended,true);assert.equal(playback.error,null);assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
 await fs.writeFile(path.join(ROOT,'outputs/command_center_demo_v1/browser_video_validation.json'),JSON.stringify({metadata:meta,seek_points:[0,10,16,19,36,48],full_1x_playback:playback,javascript_errors:errors,failed_requests:failed},null,2));
 console.log(JSON.stringify({meta,playback,errors,failed}));
}finally{await browser.close();}
