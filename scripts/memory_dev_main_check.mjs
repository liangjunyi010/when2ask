// Browser rendering/compatibility only; never starts a paid task.
import fs from 'node:fs/promises';import assert from 'node:assert/strict';
import {ROOT,requireRuntime} from '../presentation/milestone/tools/runtime.mjs';
const b=await requireRuntime('playwright').chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});const p=await b.newPage({viewport:{width:1920,height:1080}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
try{
 await p.goto('http://127.0.0.1:8877');await p.waitForSelector('#new-task-options option',{state:'attached'});
 assert.equal(await p.locator('#planner-profile').inputValue(),'default_v1');
 const before=await p.evaluate(async()=> (await(await fetch('/api/meta')).json()).budget);
 await p.selectOption('#template','retrieve_restore');assert(!(await p.locator('#planner-profile option[value=grounded_dev_v5]').evaluate(el=>el.disabled)));
 await p.selectOption('#planner-profile','memory_dev_v6');await p.selectOption('#method','llm_gate');await p.selectOption('#answer-mode','manual');
 assert((await p.locator('#method-note').innerText()).includes('Memory Dev v6'));
 await p.screenshot({path:ROOT+'outputs/memory_planner_dev_v6/main_console.png',fullPage:true});
 await p.selectOption('#template','pack_and_cover');assert.equal(await p.locator('#planner-profile').inputValue(),'default_v1');
 assert(await p.locator('#planner-profile option[value=memory_dev_v6]').evaluate(el=>el.disabled));
 const state=await p.evaluate(async()=>({meta:await(await fetch('/api/meta')).json(),tasks:(await(await fetch('/api/tasks')).json()).tasks.length}));
 assert.equal(state.tasks,10);assert.deepEqual(before,state.meta.budget);assert.deepEqual(errors,[]);
 await fs.writeFile(ROOT+'outputs/memory_planner_dev_v6/main_console_validation.json',JSON.stringify({url:'http://127.0.0.1:8877/',default_profile_unchanged:true,v5_still_available:true,v6_optional_and_supported:true,manual_selection_available:true,restored_historical_cards:state.tasks,paid_requests_added:0,errors},null,2)+'\n');
 console.log(JSON.stringify({historical_cards:state.tasks,errors,paid_requests_added:0}));
}finally{await b.close();}
