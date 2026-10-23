import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {ROOT,BASE,requireRuntime} from './runtime.mjs';
const {chromium}=requireRuntime('playwright');
const manifest=JSON.parse(await fs.readFile(path.join(BASE,'web/timeline.json'),'utf8'));
const main=manifest.episodes.find(e=>e.episode_key==='jev_pack');
const browser=await chromium.launch({executablePath:process.env.WHEN2ASK_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
const errors=[],failed=[],external=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
page.on('requestfailed',r=>failed.push({url:r.url(),error:r.failure()?.errorText}));
await page.route('**/*',route=>{const url=new URL(route.request().url());if(!['127.0.0.1','localhost'].includes(url.hostname)){external.push(url.href);return route.abort();}return route.continue();});
await page.goto('http://127.0.0.1:8765/?presentation=1',{waitUntil:'networkidle'});
await page.evaluate(()=>window.replayReady);await page.evaluate(()=>document.fonts.ready);
await fs.mkdir(path.join(BASE,'screenshots'),{recursive:true});
const first=predicate=>{const f=main.frames.find(predicate);assert(f,'Checkpoint absent');return f;};
const cupId=main.frames.find(f=>f.action?.kind==='pick_place').action.object_id;
const blockId=main.frames.find(f=>f.action?.kind==='pick_place'&&f.action.object_id!==cupId).action.object_id;
const points=[
 ['01_initial',main.frames[0]],
 ['02_pick_cup',first(f=>f.action?.object_id===cupId&&f.physical_phase==='grasp')],
 ['02b_cup_transport',first(f=>f.action?.object_id===cupId&&f.physical_phase==='transport')],
 ['03_ask',first(f=>f.stage==='question')],
 ['04_user_answer',first(f=>f.stage==='user_answer')],
 ['05_robot_continue',first(f=>f.action?.object_id===blockId&&f.physical_phase==='transport')],
 ['05b_cover',first(f=>f.action?.kind==='cover'&&f.physical_phase==='transport')],
 ['06_evaluation',first(f=>f.stage==='evaluation')],
];
const checks=[];
for(const [label,f]of points){
 const state=await page.evaluate(i=>window.replay.renderFrame(i),f.frame_index);
 const hash=await page.evaluate(()=>window.replay.pixelHash());
 assert.equal(state.frame_index,f.frame_index);assert.equal(state.dom_frame,f.frame_index);
 assert.equal(state.source_frame,f.source_gif_frame_index);assert.equal(state.simulation_step,f.simulation_step);
 assert.equal(state.dom_step,f.simulation_step);assert.equal(state.dom_node,f.active_flow_node);
 assert.deepEqual(state.gate,f.gate);assert.deepEqual(state.action,f.action);assert.deepEqual(state.question,f.question);
 assert.deepEqual(state.user_answer,f.user_answer);assert.equal(hash,f.source_pixel_sha256);
 const screenshot=`screenshots/${label}.png`;
 await page.screenshot({path:path.join(BASE,screenshot),animations:'disabled'});
 checks.push({label,frame_index:f.frame_index,source_gif_frame_index:f.source_gif_frame_index,
  simulation_step:f.simulation_step,start_ms:f.start_ms,end_ms:f.end_ms,round:f.round,
  active_flow_node:f.active_flow_node,physical_phase:f.physical_phase,gate:f.gate,action:f.action,
  question:f.question,user_answer:f.user_answer,pixel_sha256:hash,screenshot,passed:true});
}
// Validate every frame, not just six selected screenshots.
let allPixels=0;
for(const ep of manifest.episodes){
 await page.evaluate(k=>window.replay.selectEpisode(k),ep.episode_key);
 for(const f of ep.frames){
  const state=await page.evaluate(i=>window.replay.renderFrame(i),f.frame_index);
  const hash=await page.evaluate(()=>window.replay.pixelHash());
  assert.equal(hash,f.source_pixel_sha256);assert.equal(state.dom_node,f.active_flow_node);
  assert.equal(state.dom_frame,f.frame_index);assert.equal(state.dom_step,f.simulation_step);allPixels++;
 }
 if(ep.method==='llm_gate'){
  await page.evaluate(()=>window.replay.seek(0));
  assert.equal(await page.locator('#gate-probability').textContent(),'ASK · LLM decision');
  assert.equal((await page.evaluate(()=>window.replay.snapshot())).gate.p_ask,null);
 }
}
await page.evaluate(()=>window.replay.selectEpisode('jev_pack'));
await page.evaluate(()=>window.replay.seek(15000));const frozen=await page.evaluate(()=>window.replay.snapshot());
await page.waitForTimeout(200);assert.deepEqual(await page.evaluate(()=>window.replay.snapshot()),frozen);
const controls=[];
for(const speed of [1,2,3]){
 for(const start of [0,points[2][1].start_ms,points[3][1].end_ms-150]){
  await page.evaluate(async ({s,t})=>{await window.replay.seek(t);await window.replay.setSpeed(s);window.replay.play();},{s:speed,t:start});
  await page.waitForTimeout(240);
  const state=await page.evaluate(async()=>{await window.replay.pause();return window.replay.snapshot();});
  assert(state.time_ms-start>=160*speed&&state.time_ms-start<650*speed);
  const expected=main.frames.find(f=>f.start_ms<=state.time_ms&&state.time_ms<f.end_ms);
  assert.equal(state.dom_frame,expected.frame_index);assert.equal(state.dom_node,expected.active_flow_node);
  assert.equal(await page.evaluate(()=>window.replay.pixelHash()),expected.source_pixel_sha256);
  assert.deepEqual(state.question,expected.question);assert.deepEqual(state.user_answer,expected.user_answer);
  controls.push({speed,start_ms:start,time_ms:state.time_ms,frame_index:state.frame_index,stage:state.stage,synchronized:true});
 }
}
for(const f of [points[3][1],points[4][1],points[5][1],points[0][1],points.at(-1)[1]]){
 const state=await page.evaluate(ms=>window.replay.seek(ms),f.start_ms);assert.equal(state.frame_index,f.frame_index);
}
// Exercise the actual visible controls in normal mode as well.
await page.evaluate(()=>document.getElementById('stage').classList.remove('presentation'));
await page.locator('#restart').click();await page.waitForTimeout(130);await page.locator('#play').click();
assert.equal((await page.evaluate(()=>window.replay.snapshot())).playing,false);
await page.selectOption('#speed','2');assert.equal((await page.evaluate(()=>window.replay.snapshot())).speed,2);
await page.selectOption('#episode-select','llm_containers');await page.waitForTimeout(100);
assert.equal((await page.evaluate(()=>window.replay.snapshot())).episode,'llm_containers');
await page.selectOption('#episode-select','jev_pack');await page.waitForTimeout(100);
const overflow=await page.evaluate(()=>Array.from(document.querySelectorAll('h1,#instruction,#known-preferences,#planner-line,#answer-line,#outcome-line')).filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.id||e.tagName));
assert.deepEqual(overflow,[]);assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);assert.deepEqual(external,[]);
const report={schema_version:1,browser:await browser.version(),viewport:{width:1920,height:1080},
 source_episode:main.source_episode,source_gif_sha256:main.source_files['demo.gif'].sha256,
 checkpoint_count:checks.length,checkpoints:checks,all_source_frames_pixel_verified:allPixels,
 equal_step_ask_user_preserved:checks.find(c=>c.label==='03_ask').simulation_step===checks.find(c=>c.label==='04_user_answer').simulation_step&&checks.find(c=>c.label==='03_ask').frame_index!==checks.find(c=>c.label==='04_user_answer').frame_index,
 controls:{paused_state_unchanged:true,seek_restart_episode_switch_passed:true,speeds:controls},
 console_errors:errors,failed_requests:failed,external_requests:external,text_horizontal_overflow:overflow,
 inference_wall_time_reconstruction:false,passed:true};
await fs.writeFile(path.join(BASE,'mapping_validation.json'),JSON.stringify(report,null,2)+'\n');
await browser.close();console.log(JSON.stringify({passed:true,checkpoints:checks.length,pixel_verified_frames:allPixels}));
