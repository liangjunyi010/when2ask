import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {BASE,BUILD,requireRuntime} from './runtime.mjs';
const {chromium}=requireRuntime('playwright');
const manifest=JSON.parse(await fs.readFile(path.join(BASE,'web/timeline.json'),'utf8'));
const episode=manifest.episodes.find(e=>e.episode_key==='jev_pack');
const browser=await chromium.launch({executablePath:process.env.WHEN2ASK_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const errors=[];const exports=[];
const highlightOnly=process.argv.includes('--highlight-only');
if(highlightOnly){
 const previous=JSON.parse(await fs.readFile(path.join(BASE,'export_schedule.json'),'utf8'));
 assert.equal(previous.source_episode,episode.source_episode);
 exports.push(previous.exports.find(e=>e.view==='full'));
 assert(exports[0],'Full replay schedule must already exist');
}
for(const view of (highlightOnly?['highlight']:['full','highlight'])){
 const dimensions=view==='full'?{width:1920,height:1080}:{width:1280,height:720};
 const page=await browser.newPage({viewport:dimensions,deviceScaleFactor:1});
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
 await page.goto(`http://127.0.0.1:8765/?export=1&view=${view}`,{waitUntil:'networkidle'});
 await page.evaluate(()=>window.replayReady);await page.evaluate(()=>document.fonts.ready);
 const directory=path.join(BUILD,view+'_frames');await fs.mkdir(directory,{recursive:true});
 const rows=[];let start=0;
 for(const f of episode.frames){
  const state=await page.evaluate(i=>window.replay.renderFrame(i),f.frame_index);
  assert.equal(state.dom_frame,f.frame_index);assert.equal(state.dom_node,f.active_flow_node);assert.equal(state.source_frame,f.source_gif_frame_index);
  const stem=String(f.frame_index).padStart(4,'0')+'.jpg';
  const bytes=await page.screenshot({type:'jpeg',quality:94,animations:'disabled'});
  await fs.writeFile(path.join(directory,stem),bytes);
  const duration=view==='full'?f.duration_ms:(manifest.highlight.holds_ms[f.stage]??f.duration_ms/manifest.highlight.action_speed);
  rows.push({frame_index:f.frame_index,source_gif_frame_index:f.source_gif_frame_index,simulation_step:f.simulation_step,
   source_start_ms:f.start_ms,source_duration_ms:f.duration_ms,start_ms:start,end_ms:start+duration,duration_ms:duration,
   stage:f.stage,active_flow_node:f.active_flow_node,screenshot_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),
   intermediate_screenshot:`.build/${view}_frames/${stem}`});
  start+=duration;
  if(f.frame_index%100===0)console.log(`${view}: ${f.frame_index+1}/${episode.frames.length} actual HTML screenshots`);
 }
 let concat=rows.map((f,i)=>`file '${path.join(directory,String(i).padStart(4,'0')+'.jpg')}'\noption framerate 1000\nduration ${(f.duration_ms/1000).toFixed(9)}\n`).join('');
 concat+=`file '${path.join(directory,String(rows.length-1).padStart(4,'0')+'.jpg')}'\noption framerate 1000\n`;
 await fs.writeFile(path.join(BUILD,`${view}.concat.txt`),concat);
 exports.push({view,viewport:dimensions,duration_ms:start,source_duration_ms:episode.duration_ms,
  action_speed:view==='highlight'?manifest.highlight.action_speed:1,
  timing_note:view==='highlight'?`All physical frames compressed uniformly ${manifest.highlight.action_speed}x; readable recorded decision/answer holds. Same source frame controls both sides.`:'Original recorder display intervals, no wall-time inference reconstruction.',
  frames:rows});
 await page.close();
}
assert.deepEqual(errors,[]);
await fs.writeFile(path.join(BASE,'export_schedule.json'),JSON.stringify({source_episode:episode.source_episode,exports,console_errors:errors},null,2)+'\n');
await browser.close();console.log(JSON.stringify(exports.map(e=>({view:e.view,duration_ms:e.duration_ms,frames:e.frames.length}))));
