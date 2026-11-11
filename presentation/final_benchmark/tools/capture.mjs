import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const runtime=process.env.RUNTIME_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req=createRequire(path.join(runtime,'runtime.cjs'));
const {chromium}=req('playwright');
const BASE=fileURLToPath(new URL('../',import.meta.url));
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
await page.goto('http://127.0.0.1:8901/presentation/final_benchmark/web/?export');await page.waitForFunction(()=>window.replayReady);
await fs.mkdir(path.join(BASE,'.build/capture'),{recursive:true});await fs.mkdir(path.join(BASE,'assets'),{recursive:true});
const t=await page.evaluate(()=>window.replay.timeline);const checkpoints=[];
for(let i=0;i<t.frames.length;i++){
 const state=await page.evaluate(i=>window.replay.showFrame(i),i);
 if(state.frame_index!==i||state.simulation_step!==t.frames[i].simulation_step)throw Error('Frame synchronization mismatch');
 if(!process.argv.includes('--validate-only'))await page.locator('#canvas').screenshot({path:path.join(BASE,'.build/capture',`${String(i).padStart(4,'0')}.png`)});
 if([0,20,49,50,75,106,130,163].includes(i))checkpoints.push(state);
}
await fs.copyFile(path.join(BASE,'.build/capture/0000.png'),path.join(BASE,'assets/replay_poster.png'));
// Pause, seek, replay and speed tests all interrogate the same master clock.
await page.evaluate(()=>document.body.classList.remove('export'));
await page.evaluate(()=>window.replay.seek(1500));await page.evaluate(()=>window.replay.pause());const paused=await page.evaluate(()=>window.replay.getState());await page.waitForTimeout(170);const stable=await page.evaluate(()=>window.replay.getState());if(paused.frame!==stable.frame)throw Error('Pause failed');
for(const speed of ['1','2','3']){await page.selectOption('#speed',speed);await page.evaluate(()=>window.replay.seek(0));await page.evaluate(()=>window.replay.play());await page.waitForTimeout(280);await page.evaluate(()=>window.replay.pause());const s=await page.evaluate(()=>window.replay.getState());const expected=t.frames.findIndex(f=>s.clock>=f.start_ms&&s.clock<f.end_ms);if(s.frame!==expected)throw Error('Speed sync failed');}
await page.click('#restart');const restart=await page.evaluate(()=>window.replay.getState());if(restart.frame!==0)throw Error('Restart failed');
await fs.writeFile(path.join(BASE,'browser_validation.json'),JSON.stringify({browser:await browser.version(),viewport:[1280,720],rendered_frames:t.frames.length,checkpoints,pause:true,seek:true,restart:true,speeds:[1,2,3],errors},null,2)+'\n');
await browser.close();if(errors.length)throw Error(JSON.stringify(errors));console.log(JSON.stringify({frames:t.frames.length,errors:errors.length}));
