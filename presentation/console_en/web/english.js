// Display-only adapters. Raw episodes, model payloads and human utterances stay unchanged.
(()=>{
const titles={pack_and_cover:'Pack & Cover',place_into_selected_containers:'Two Selected Containers',find_and_approach:'Find & Approach',category_sorting:'Category Sorting',inventory_restock:'Inventory Restock',retrieve_restore:'Retrieve & Restore',buffer_exchange:'Buffered Exchange',patrol_return:'Patrol & Return',occlusion_inspection:'Reveal & Inspect'};
window.englishMetadata=m=>{for(const[k,v]of Object.entries(m.new_task_catalogue||{}))v.title=titles[k]||k;return m;};
window.englishError=message=>{
 if(!message)return '';
 // The legacy parser also accepts non-English replies; present its errors in English.
 if(/[^\u0000-\u024f\u2000-\u206f]/.test(message)&&/\p{Script=Han}/u.test(message)){
  if(message.includes('1–1000'))return 'Enter 1–1000 characters, or select the candidates below.';
  if(message.includes('yes'))return 'Answer yes or no, or use candidate selection.';
  return 'The answer could not be matched unambiguously. Use the exact candidate name or select one candidate per slot.';
 }return message;
};
function interaction(t){
 let text;
 if(t.method.endsWith('noask'))text='NoAsk never requests clarification; no answer form will appear.';
 else if(t.status==='waiting_answer')text=t.answer_mode==='manual'?'ASK received. Type an answer or select candidates in the Clarification Queue.':'ASK received. The User Simulator is answering.';
 else if(['done','error','cancelled'].includes(t.status))text=t.ask_turns?'Mission ended. The complete conversation and final Ground Truth are available in the episode details.':'No ASK occurred in this episode, so no answer form was needed.';
 else text=t.answer_mode==='manual'?'Human response mode is enabled. An answer form appears only after the Gate actually chooses ASK.':'Auto response mode: the simulator answers only when ASK occurs.';
 const g=t.gate;if(g?.backend==='jev'&&typeof g.p_ask==='number')text+=` Latest recorded Jev p(ASK)=${g.p_ask.toFixed(2)}, threshold=${t.review?.interaction.threshold??0.5}: ${g.decision}.`;
 if(['done','error','cancelled'].includes(t.status)&&t.review?.interaction.missing_roles?.length&&t.template!=='find_and_approach')text+=' Some information remained undisclosed; the final physical state determines success.';
 return text;
}
window.englishTask=t=>{
 const r=t.review;if(!r)return {...t,template_name:titles[t.template]||t.template_name};
 let truth=r.ground_truth;
 if(truth){const meaning=truth.protocol==='fixed_world_fact'?'Fixed world fact: a human reply cannot change the label or replace physical inspection.':truth.protocol==='fixed_world_location'?'Fixed target location: a human hint does not move the target or change the goal.':truth.protocol==='interactive_declared_preferences'?'Initial hidden reference and evaluated goal are shown separately. A human answer to an undisclosed preference defines the interactive goal.':'The User Simulator answers from the fixed hidden preferences; the evaluation goal stays fixed.';truth={...truth,meaning};}
 return {...t,template_name:titles[t.template]||t.template_name,review:{...r,interaction:{...r.interaction,message:interaction(t)},ground_truth:truth,engine:{...r.engine,notice:'Interactive Dev execution. Original research defaults and frozen benchmark records are preserved.'}}};
};
window.renderMissionBrief=t=>{
 const host=document.getElementById('mission-brief');if(!host)return;host.hidden=false;document.body.classList.add('has-missions');
 if(host.dataset.taskId===t.id)return;host.dataset.taskId=t.id;host.replaceChildren();
 const head=document.createElement('div');head.className='brief-head';const title=document.createElement('h2');title.textContent='Initial Instruction';const button=document.createElement('button');button.className='text-button';button.textContent='Full Instruction & Conversation';button.onclick=()=>window.consoleView?.getCard(t.id)?.querySelector('.review-link').click();head.append(title,button);
 const p=document.createElement('p');p.textContent=t.review?.original_instruction||t.instruction||'Waiting for the public instruction.';host.append(head,p);
 const controls=document.getElementById('mission-controls');if(controls)controls.hidden=(window.presentationHub?.view||'live')!=='live';
};
})();
