// Apply Team 11's requested structure to the current ten-slide presentation.
// Diagrams, tables and charts remain native editable PowerPoint objects.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const BASE=fileURLToPath(new URL('../',import.meta.url));
const ROOT=fileURLToPath(new URL('../../../',import.meta.url));
const C={bg:'#F7F9FC',navy:'#163650',ink:'#243F56',muted:'#617589',blue:'#1975BC',pale:'#E9F2FA',orange:'#C66B19',warm:'#FFF0DF',green:'#218565',mint:'#EAF6EF',line:'#CCD9E5'};
function get(s,n){const q=s.shapes.items.find(x=>x.name===n);if(!q)throw Error('Missing '+n);return q;}
function text(s,n,t,x,y,w,h,size=30,color=C.ink,bold=false,align='left'){
 const q=s.shapes.add({name:n,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=t;q.text.style={fontSize:size,typeface:'Arial',color,bold,alignment:align,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};return q;
}
function edit(s,n,t){get(s,n).text=t;}
function clear(p,s){p.delete(s.shapes.items.map(x=>x.toSnapshot().aid));}
function heading(s,n,t,sub){text(s,'title',t,65,38,1465,70,46,C.navy,true);text(s,'subtitle',sub,68,115,1460,55,28,C.muted);page(s,n);}
function page(s,n){const q=s.shapes.items.find(x=>x.name==='page-number');if(q)q.text=String(n).padStart(2,'0');else text(s,'page-number',String(n).padStart(2,'0'),1484,853,55,30,19,C.muted,false,'right');}
function table(s,name,values,x,y,widths,h=76,font=28){
 const t=s.tables.add({name,rows:values.length,columns:widths.length,left:x,top:y,width:widths.reduce((a,b)=>a+b),height:values.length*h,columnWidths:widths,values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:widths.length}).assign({fill:'#FFFFFF',textStyle:{fontSize:font,typeface:'Arial',color:C.ink,alignment:'center',verticalAlignment:'middle'},margins:{left:14,right:14,top:10,bottom:10},anchor:'center'});t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++){t.rows[r].height=h;for(let c=0;c<widths.length;c++){t.getCell(r,c).text.style={fontSize:font,typeface:'Arial',color:r===0?C.navy:C.ink,bold:r===0,alignment:c===0?'left':'center',verticalAlignment:'middle'};if(r===0)t.getCell(r,c).fill=C.pale;}}
 return t;
}
function line(s,name,points,color=C.blue,arrow=true){
 for(let i=1;i<points.length;i++){
  const [x1,y1]=points[i-1],[x2,y2]=points[i];
  s.shapes.add({name:name+'-'+i,geometry:'connector',kind:'straight',position:{left:Math.min(x1,x2),top:Math.min(y1,y2),width:Math.abs(x2-x1),height:Math.abs(y2-y1),horizontalFlip:x2<x1,verticalFlip:y2<y1},line:{fill:color,width:2.7},tail:{type:arrow&&i===points.length-1?'triangle':'none',width:'med',length:'med'}});
 }
}
function node(s,n,label,sub,x,y,w,h,color=C.blue,fill=C.pale){
 s.shapes.add({name:n,geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:color,width:1.5}});
 if(sub){text(s,n+'-label',label,x+10,y+9,w-20,34,29,C.navy,true,'center');text(s,n+'-detail',sub,x+10,y+45,w-20,h-48,24,C.ink,false,'center');}
 else text(s,n+'-label',label,x+10,y+5,w-20,h-10,28,C.navy,true,'center');
 return {id:n,label,detail:sub,x,y,width:w,height:h};
}

export async function reviseTeam({presentation:p}){
 if(p.slides.items.length!==10)throw Error('Expected current ten-slide deck');
 const old=[...p.slides.items];
 const script=JSON.parse(await fs.readFile(path.join(BASE,'speaker_script.json'),'utf8'));
 const report=JSON.parse(await fs.readFile(path.join(ROOT,'presentation/final_benchmark_cost/analysis/cost_report.json'),'utf8'));
 const cover=old[0];clear(p,cover);
 text(cover,'project-name','When2Ask',72,93,680,110,78,C.navy,true);
 text(cover,'presentation-title','A Benchmark for\nClarification Timing\nin Robotic Tasks',76,241,680,190,48,C.navy,true);
 text(cover,'team-number','Team 11',80,525,600,55,36,C.blue,true);
 text(cover,'team-members','Liang Junyi\nYang Haocheng',80,604,610,104,33,C.ink);
 cover.images.items[0].frame={left:765,top:270,width:770,height:433};
 text(cover,'research-question','When should a robot ask, and when should it continue?',80,790,1450,55,33,C.navy);page(cover,1);

 const problem=old[1];clear(p,problem);
 heading(problem,2,'Problem & Motivation','Strong zero-shot capability does not remove response latency or inference cost.');
 text(problem,'llm-heading','Conversational LLMs',80,230,680,52,35,C.navy,true);
 text(problem,'llm-benefits','Strong zero-shot task understanding\nEasy to connect to agent tools',82,307,665,105,31);
 text(problem,'overhead-heading','Repeated decisions have overhead',80,465,690,52,33,C.blue,true);
 text(problem,'overhead-details','Latency slows the decision loop.\nAPI calls add inference cost.',82,538,680,105,31);
 text(problem,'example-heading','A missing user preference',850,230,675,52,35,C.navy,true);
 text(problem,'example-instruction','“Open the box, bring my chosen item,\nthen put the lid back.”',852,303,675,104,31);
 node(problem,'example-open','Open',null,852,449,155,64);
 node(problem,'example-retrieve','Chosen item',null,1065,449,240,64,C.orange,C.warm);
 node(problem,'example-close','Reclose',null,1363,449,165,64);
 line(problem,'example-edge-open',[[1007,481],[1065,481]]);
 line(problem,'example-edge-close',[[1305,481],[1363,481]]);
 text(problem,'example-disclosure','Opening is already supported.\nThe item choice still needs the user.',852,558,675,105,30,C.ink);
 text(problem,'hypothesis','Can a specialized gate preserve reliability with less decision overhead?',80,765,1440,65,33,C.navy,true);

 const flow=old[5];clear(p,flow);
 heading(flow,3,'Approach & Implementation','A repeated decision loop connects model outputs, user answers and real robot skills.');
 const nodes=[
  node(flow,'public-state','Public State','Instruction, observation, history',565,184,470,82),
  node(flow,'gate','Clarification Gate','DeepSeek / Jev; NoAsk bypasses',590,306,420,82),
  node(flow,'question-planner','Question Planner','DeepSeek',120,445,400,82,C.orange,C.warm),
  node(flow,'action-planner','Action Planner','Shared DeepSeek Planner',1080,445,400,82),
  node(flow,'user-answer','User Answer','Simulator or human',120,575,400,82,C.orange,C.warm),
  node(flow,'physics','PyBullet Panda','IK + fixed robot skills',1080,575,400,82),
  node(flow,'history','Updated public history',null,120,705,400,64,C.orange,C.warm),
  node(flow,'observation','New observation',null,1080,705,400,64),
  node(flow,'evaluator','Independent Evaluator','Final state + task order',600,585,400,94,C.green,C.mint)
 ];
 const edges=[
  ['state-gate','public-state','gate',[[800,266],[800,306]],C.blue],
  ['ask','gate','question-planner',[[590,347],[320,347],[320,445]],C.orange],
  ['continue','gate','action-planner',[[1010,347],[1280,347],[1280,445]],C.blue],
  ['question-user','question-planner','user-answer',[[320,527],[320,575]],C.orange],
  ['user-history','user-answer','history',[[320,657],[320,705]],C.orange],
  ['history-state','history','public-state',[[120,737],[60,737],[60,225],[565,225]],C.orange],
  ['action-physics','action-planner','physics',[[1280,527],[1280,575]],C.blue],
  ['physics-observation','physics','observation',[[1280,657],[1280,705]],C.blue],
  ['observation-state','observation','public-state',[[1480,737],[1540,737],[1540,225],[1035,225]],C.blue],
  ['done','action-planner','evaluator',[[1080,486],[800,486],[800,585]],C.green]
 ];
 for(const [id,from,to,points,color]of edges)line(flow,id,points,color);
 text(flow,'ask-label','ASK',130,384,160,42,30,C.orange,true,'center');
 text(flow,'continue-label','CONTINUE',1310,384,210,42,30,C.blue,true,'center');
 text(flow,'done-label','DONE',825,531,170,39,29,C.green,true);
 text(flow,'public-boundary','Only public information',565,406,470,36,25,C.muted,false,'center');
 text(flow,'loop-caption','ASK updates history without stepping physics. Actions execute before the next observation.',80,806,1440,45,26,C.muted);

 const tasks=old[2];edit(tasks,'title','Benchmark Task Design');page(tasks,4);
 const dataset=old[3];edit(dataset,'title','Dataset Construction & Physical Validation');page(dataset,5);
 const methods=old[4];edit(methods,'title','Three Methods, One Shared Planner');page(methods,6);
 const results=old[6];edit(results,'title','Results: Success & Clarification Burden');page(results,7);
 edit(results,'cost-table-heading','Preference requests and task failures');
 p.delete(results.tables.items[0].toSnapshot().aid);
 table(results,'success-burden-results',[['Method','Burden / ep.'],['NoAsk','0.000'],['LLM-Gate','0.333'],['Jev-Gate','0.333']],890,325,[335,300],78,28);
 edit(results,'latency-scope','NoAsk guessed the wrong buffer or item.\nBoth gates requested 4 slots in total.');
 const efficiency=old[7];edit(efficiency,'title','Results: Speed & Estimated API Cost');
 edit(efficiency,'estimated-usd-heading','Whole-workflow totals');
 edit(efficiency,'estimated-usd-scope','12 episodes per method; API time excludes robot motion');
 get(efficiency,'estimated-usd-scope').text.style={fontSize:23,typeface:'Arial',color:C.muted,alignment:'left',verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};
 p.delete(efficiency.tables.items[0].toSnapshot().aid);
 table(efficiency,'workflow-time-cost',[['Method','API total','Est. USD'],...report.methods.map((m,i)=>[['NoAsk','LLM-Gate','Jev-Gate'][i],m.api_latency_s.toFixed(2)+' s','$'+m.estimated_total_usd.toFixed(4)])],820,325,[230,240,240],78,27);
 const demo=old[8];edit(demo,'title','Results & Demonstration: Real Execution');
 // Make the synchronized replay 19% wider while retaining its full 16:9 image.
 demo.images.items[0].frame={left:75,top:327,width:950,height:534.375};
 const moves={
  'demo-real-title':{left:1080,top:394,width:450,height:75},
  'demo-first-score':{left:1080,top:492,width:450,height:50},
  'demo-first-action':{left:1080,top:550,width:450,height:73},
  'demo-second-score':{left:1080,top:647,width:450,height:50},
  'demo-second-action':{left:1080,top:707,width:450,height:77},
  'timing-caveat':{left:1080,top:795,width:450,height:63}
 };
 for(const [n,pos]of Object.entries(moves))get(demo,n).position=pos;
 get(demo,'demo-real-title').text.style={fontSize:32,typeface:'Arial',color:C.navy,bold:true,insets:0,autoFit:'none',wrap:'square',verticalAlignment:'middle'};
 get(demo,'timing-caveat').text.style={fontSize:23,typeface:'Arial',color:C.muted,insets:0,autoFit:'none',wrap:'square',verticalAlignment:'middle'};
 // Compact the two exploratory timing rows to make room for the enlarged movie.
 for(const [i,names]of [['llm',['timing-llm-label','llm-ask','llm-ask-box','llm-arrow-1','llm-open','llm-open-box','llm-arrow-2','llm-retrieve','llm-retrieve-box']],['jev',['timing-jev-label','jev-open','jev-open-box','jev-arrow-1','jev-ask','jev-ask-box','jev-arrow-2','jev-retrieve','jev-retrieve-box']]]){
   for(const n of names){const q=get(demo,n);q.position={...q.position,top:q.position.top-(i==='llm'?23:35)};}
 }
 const closing=old[9];edit(closing,'title','Discussion & Conclusions');
 edit(closing,'finding-0','A benchmark for three clarification regimes');
 edit(closing,'finding-1','Layout isolation and real physical validation');
 edit(closing,'finding-2','Shared planning with auditable model costs');
 edit(closing,'limits','12 Test groups; binary choices; assisted grasp\nPrompt and threshold sensitivity\nPrice estimates depend on cache and rates');
 edit(closing,'next-body','More independent layouts and repeated runs;\npre-register timing metrics and cost checks.');
 p.slides.reorder([old[0],old[1],old[5],old[2],old[3],old[4],old[6],old[7],old[8],old[9]].map(s=>s.id));
 for(const [i,s]of p.slides.items.entries()){page(s,i+1);s.speakerNotes.text=script.slides[i].script+'\n\nEvidence and cautions (not spoken): '+script.slides[i].evidence;}
 const spec={nodes,edges:edges.map(([id,from,to,points,color])=>({id,from,to,points,color})),
             rules:{gate_outputs:['ASK','CONTINUE'],done_source:'action-planner',question_does_not_step_physics:true,
                    public_only_agents:true,benchmark_uses_simulator:true,human_answers_supported_in_html:true}};
 await fs.writeFile(path.join(BASE,'flow_spec.json'),JSON.stringify(spec,null,2)+'\n');
 return {slides:10,team:11,members:script.members,preservedSlideIds:old.map(s=>s.id),flowNodes:nodes.length,flowEdges:edges.length,targetSeconds:570};
}
