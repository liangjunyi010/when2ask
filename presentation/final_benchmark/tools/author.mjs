// Authoring callbacks run inside the connected Artifact Session.
// No API keys, model requests, benchmark mutations or simulated results.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const ROOT=fileURLToPath(new URL('../../../',import.meta.url));
const BASE=path.join(ROOT,'presentation/final_benchmark');
const C={bg:'#F7F9FC',navy:'#163650',ink:'#243F56',muted:'#617589',blue:'#1975BC',pale:'#E9F2FA',orange:'#C66B19',warm:'#FFF0DF',green:'#218565',line:'#CCD9E5',gray:'#7F90A0'};
function box(s,name,x,y,w,h,fill=C.pale,line='none',radius=false){return s.shapes.add({name,geometry:radius?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1}});}
function txt(s,name,t,x,y,w,h,size=30,color=C.ink,bold=false,align='left'){
 const q=box(s,name,x,y,w,h,'none');q.text=t;q.text.style={fontSize:size,typeface:'Arial',color,bold,alignment:align,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};return q;
}
function line(s,name,x,y,w,h,color=C.line){return box(s,name,x,y,w,h,color);}
function arrow(s,name,x,y,w=32,h=30,color=C.blue){return s.shapes.add({name,geometry:'rightArrow',position:{left:x,top:y,width:w,height:h},fill:color,line:{fill:'none',width:0}});}
function down(s,name,x,y,w=26,h=34,color=C.blue){return s.shapes.add({name,geometry:'downArrow',position:{left:x,top:y,width:w,height:h},fill:color,line:{fill:'none',width:0}});}
function node(s,name,t,x,y,w,h=68,fill=C.pale,color=C.ink,size=27){box(s,name+'-box',x,y,w,h,fill);txt(s,name,t,x+12,y+4,w-24,h-8,size,color,true,'center');}
async function image(s,name,rel,x,y,w,h){const blob=new Uint8Array(await fs.readFile(path.join(ROOT,rel)));return s.images.add({name,blob,contentType:'image/png',position:{left:x,top:y,width:w,height:h},fit:'contain',alt:name.replaceAll('-',' ')});}
function base(p,n,title,sub){const s=p.slides.add({width:1600,height:900,background:{fill:C.bg}});txt(s,'title',title,65,38,1465,70,46,C.navy,true);if(sub)txt(s,'subtitle',sub,68,115,1462,52,28,C.muted);txt(s,'page-number',String(n).padStart(2,'0'),1484,847,55,30,19,C.muted,false,'right');return s;}
function table(s,name,values,x,y,widths,rowHeight=73,font=27){
 const t=s.tables.add({name,rows:values.length,columns:widths.length,left:x,top:y,width:widths.reduce((a,b)=>a+b,0),height:values.length*rowHeight,columnWidths:widths,values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:widths.length}).assign({fill:'#FFFFFF',textStyle:{fontSize:font,typeface:'Arial',color:C.ink,verticalAlignment:'middle',alignment:'center'},margins:{left:17,right:17,top:12,bottom:12},anchor:'center'});
 t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++){t.rows[r].height=rowHeight;for(let c=0;c<widths.length;c++){t.getCell(r,c).text.style={fontSize:font,typeface:'Arial',color:r===0?C.navy:C.ink,bold:r===0,alignment:c===0?'left':'center',verticalAlignment:'middle'};if(r===0)t.getCell(r,c).fill=C.pale;}}return t;
}
async function notes(s,i){const a=JSON.parse(await fs.readFile(path.join(BASE,'speaker_script.json'),'utf8'));s.speakerNotes.text=a.slides[i-1].script+'\n\nEvidence (not spoken): '+a.slides[i-1].evidence;}

export async function cover({presentation:p}){
 p.slides.delete(0);
 const s=p.slides.add({width:1600,height:900,background:{fill:C.bg}});
 txt(s,'project-name','When2Ask',66,50,900,82,68,C.navy,true);
 txt(s,'presentation-title','Benchmarking Clarification Timing\nin Robotic Tasks',70,145,1460,126,48,C.navy,true);
 txt(s,'research-question','When should a robot ask, and when can it make useful progress?',72,288,1450,58,32,C.ink);
 await image(s,'real-panda-buffer-exchange','outputs/three_task_v8/oracle_r2/t8_r2_test_0_05_1/scene.png',735,369,795,449);
 const items=[['Controlled tasks','Task DAGs + hidden user preferences'],['Fair comparison','One planner; three gate mechanisms'],['Real execution','PyBullet physics + independent scoring']];
 for(let i=0;i<3;i++){const y=390+i*135;line(s,'contribution-accent-'+i,73,y+4,5,76,C.blue);txt(s,'contribution-'+i,items[i][0],95,y,590,40,31,C.navy,true);txt(s,'contribution-detail-'+i,items[i][1],95,y+49,590,50,27,C.muted);}
 txt(s,'page-number','01',1484,847,55,30,19,C.muted,false,'right');await notes(s,1);return {slides:p.slides.items.length};
}

export async function batch1({presentation:p}){
 const s=base(p,2,'What makes one benchmark sample?','A task is more than an instruction: it also defines what is known and what must be achieved.');
 txt(s,'example-instruction','“Open the box, deliver my chosen item,\nthen put the lid back.”',75,205,850,116,38,C.navy,true);
 txt(s,'disclosure','The item choice is initially undisclosed.',78,340,840,49,29,C.orange,true);
 const ns=[['Open box',77],['Retrieve chosen item',362],['Restore lid',747]];
 node(s,'dag-open',ns[0][0],77,438,235);arrow(s,'dag-edge-1',324,457,28);node(s,'dag-retrieve',ns[1][0],362,438,335);arrow(s,'dag-edge-2',709,457,28);node(s,'dag-close',ns[2][0],747,438,240);
 txt(s,'public-heading','Robot sees',1040,210,450,52,33,C.blue,true);txt(s,'public-content','Instruction\nVisible objects\nPublic answers + action history',1040,282,470,154,30);
 line(s,'privacy-divider',1020,485,480,2);
 txt(s,'private-heading','Kept private',1040,524,450,52,33,C.orange,true);txt(s,'private-content','True user preference\nEvaluator verdict\nOracle action sequence',1040,596,460,160,30);
 txt(s,'sample-components','Layout + seed · Task DAG\nHidden preference + initial disclosure',78,615,910,113,30,C.ink);
 txt(s,'sample-point','The same scene can require different clarification timing.',78,776,1420,55,32,C.navy,true);await notes(s,2);

 const t=base(p,3,'Three tasks, three clarification regimes','The benchmark separates missing user preferences from information the robot can observe.');
 const configs=[
 {title:'Buffer exchange',im:'0_04_3',method:'jev_gate',rule:'ASK before acting',detail:'A required temporary pad\nhas not been selected.',steps:['ASK: choose pad','Park A → move B → move A'],col:C.orange},
 {title:'Retrieve & restore',im:'1_04_1',method:'llm_noask',rule:'Make progress, then ASK',detail:'Opening is already allowed;\nthe item choice is still missing.',steps:['Open the box','ASK → retrieve → reclose'],col:C.blue},
 {title:'Occlusion inspection',im:'2_04_3',method:'jev_gate',rule:'Inspect instead of asking',detail:'The hidden world fact can be\nmeasured by required inspection.',steps:['Uncover → inspect','Report → restore'],col:C.green}];
 for(let i=0;i<3;i++){const a=configs[i],x=70+i*510;txt(t,'task-title-'+i,a.title,x,200,480,50,34,C.navy,true);await image(t,'task-scene-'+i,`outputs/three_task_v8/test_runs/t8_r2_test_${a.im}__${a.method}/scene.png`,x,264,470,264);line(t,'task-separator-'+i,x,550,470,3,a.col);txt(t,'task-rule-'+i,a.rule,x,577,475,48,30,a.col,true);txt(t,'task-info-'+i,a.detail,x,642,476,83,28);txt(t,'task-sequence-'+i,a.steps.join('\n'),x,751,470,72,26,C.muted);}
 await notes(t,3);return {slides:p.slides.items.length};
}

export async function batch2({presentation:p}){
 const s=base(p,4,'Build layouts first, then split by group','Preference changes and instruction rewrites stay with their original physical layout.');
 const labels=['Generate layouts','Group & split','Add task variants','Physical oracle'];const xs=[70,447,824,1201];
 for(let i=0;i<4;i++){node(s,'pipeline-'+i,labels[i],xs[i],207,i===3?326:306,70);if(i<3)arrow(s,'pipe-arrow-'+i,xs[i]+323,231,35,26);}
 table(s,'dataset-splits',[['Partition','Base layout groups','Samples','Unknown slots'],['Development','6','24','0 / 1 (balanced)'],['Held-out Test','12','12','0 / 1 (balanced)'] ],75,348,[320,365,260,500],83,30);
 txt(s,'physical-oracle-number','36 / 36',79,666,350,77,57,C.green,true);txt(s,'physical-oracle-caption','Physical oracle executions passed',445,674,1040,60,33,C.navy,true);
 txt(s,'dataset-guards','Three templates in each split; debug layouts excluded from Test.\nCorrect choices are balanced across candidate order and disclosure.',79,776,1430,75,27,C.muted);await notes(s,4);

 const t=base(p,5,'Compare gates while keeping the planner fixed','Each method receives the same public information and starts with a fresh environment.');
 node(t,'public-state','Public instruction + observation + history',365,205,870,70);
 line(t,'public-state-stem',806,275,2,21,C.blue);line(t,'public-state-branch',298,295,1021,2,C.blue);
 for(const [x,title,sub,fill] of [[75,'LLM-NoAsk','Always CONTINUE',C.pale],[585,'LLM-Gate','DeepSeek: ASK / CONTINUE',C.pale],[1095,'Jev-Gate','Jev Noul: p(ASK) ≥ 0.5',C.warm]]){down(t,'method-in-'+x,x+210,300);node(t,'method-'+x,title,x,355,430,70,fill);txt(t,'method-sub-'+x,sub,x,443,430,52,27,C.ink,false,'center');down(t,'method-out-'+x,x+210,520);}
 node(t,'shared-planner','Shared DeepSeek Planner',490,589,620,75);
 line(t,'shared-merge',298,559,1021,2,C.blue);down(t,'shared-merge-arrow',795,562,26,25,C.blue);
 txt(t,'shared-detail','ASK → question + user answer       CONTINUE → action or DONE',215,686,1170,56,29,C.navy,true,'center');
 txt(t,'shared-controls','Same skills · Same evaluator · Same task instances · Same budgets',130,791,1340,50,29,C.muted,false,'center');await notes(t,5);

 const u=base(p,6,'Score the world, not the model’s claim','Three primary metrics capture task completion, user interruption and backend inference.');
 const metrics=[['Task success','Successful episodes / scored episodes',C.blue],['Clarification burden','Distinct preference slots requested\nRepeated requests are charged again',C.orange],['Inference cost','Tokens per backend + API latency\nRetries and schema errors included',C.green]];
 for(let i=0;i<3;i++){const y=210+i*176;txt(u,'metric-title-'+i,metrics[i][0],78,y,490,50,33,metrics[i][2],true);txt(u,'metric-definition-'+i,metrics[i][1],78,y+61,640,86,28);}
 line(u,'evaluation-divider',780,206,2,557);
 txt(u,'evaluation-title','Independent physical evaluation',830,215,680,85,35,C.navy,true);
 const checks=['Full object footprint inside target','Correct support, coverage and stability','Gripper released; no robot contact','Required task order satisfied'];
 checks.forEach((a,i)=>{txt(u,'checkmark-'+i,'✓',830,340+i*91,42,45,33,C.green,true);txt(u,'check-'+i,a,887,339+i*91,620,55,29);});
 txt(u,'physical-limit','IK control with a near-range constraint grasp;\nreleased objects settle under PyBullet physics.',835,751,670,83,27,C.muted);await notes(u,6);return {slides:p.slides.items.length};
}

export async function batch3({presentation:p}){
 const summary=JSON.parse(await fs.readFile(path.join(ROOT,'outputs/three_task_v8/report/summary.json'),'utf8'));
 const s=base(p,7,'Both gates completed all 12 held-out tasks','12 independent Test layouts × 3 methods = 36 real API and PyBullet episodes.');
 txt(s,'success-chart-heading','Task success',80,207,740,48,34,C.navy,true);
 const chart=s.charts.add('bar',{position:{left:80,top:286,width:760,height:419},categories:['LLM-NoAsk','LLM-Gate','Jev-Gate'],series:[{name:'Success rate',values:summary.methods.map(m=>Number(m.success_rate.toPrecision(15))),fill:C.blue,points:[{idx:0,fill:C.gray},{idx:1,fill:C.blue},{idx:2,fill:C.green}]}],barOptions:{direction:'column',grouping:'clustered',gapWidth:85},hasLegend:false,chartFill:'none',plotAreaFill:'none',xAxis:{visible:true,textStyle:{fontSize:26,fill:C.ink},line:{fill:C.line,width:1}},yAxis:{visible:true,min:0,max:1.15,majorUnit:0.25,numberFormatCode:'0%',textStyle:{fontSize:24,fill:C.muted},majorGridlines:{fill:C.line,width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0%',textStyle:{fontSize:29,bold:true,fill:C.navy}}});
 for(let i=0;i<3;i++){const label=chart.series.getItemAt(0).dataLabelOverrides.add(i);label.text=summary.methods[i].successes+'/12';label.textStyle.fontSize=31;label.textStyle.typeface='Arial';label.textStyle.fill=C.navy;label.textStyle.bold=true;label.showLegendKey=false;}
 for(const style of [chart.dataLabels.textStyle,chart.xAxis.textStyle,chart.yAxis.textStyle])style.typeface='Arial';
 txt(s,'cost-table-heading','Burden and cumulative API latency',893,207,640,80,32,C.navy,true);
 table(s,'result-costs',[['Method','Burden / ep.','API total'],['NoAsk','0.000','57.91 s'],['LLM-Gate','0.333','105.41 s'],['Jev-Gate','0.333','78.56 s']],890,325,[240,190,205],78,26);
 txt(s,'latency-scope','Latency totals span 12 episodes per method.\nBackend tokens are tracked separately.',895,675,645,85,27,C.muted);
 txt(s,'result-limitation','Small held-out study: observed outcomes do not establish statistical superiority.',80,799,1445,58,29,C.muted);await notes(s,7);

 const t=base(p,8,'Clarification timing changes the execution order','On two undisclosed retrieval tasks, LLM-Gate asked first; Jev opened the box first.');
 txt(t,'timing-llm-label','LLM-Gate',77,207,240,47,30,C.blue,true);node(t,'llm-ask','ASK',335,203,190,60,C.warm,C.orange);arrow(t,'llm-arrow-1',545,221);node(t,'llm-open','Open',598,203,190,60);arrow(t,'llm-arrow-2',810,221);node(t,'llm-retrieve','Retrieve',863,203,230,60);
 txt(t,'timing-jev-label','Jev-Gate',77,292,240,47,30,C.green,true);node(t,'jev-open','Open',335,288,190,60);arrow(t,'jev-arrow-1',545,306);node(t,'jev-ask','ASK',598,288,190,60,C.warm,C.orange);arrow(t,'jev-arrow-2',810,306);node(t,'jev-retrieve','Retrieve',863,288,230,60);
 await image(t,'embedded-replay-poster','presentation/final_benchmark/assets/replay_poster.png',77,390,800,450);
 txt(t,'demo-real-title','Real Jev-Gate execution',930,399,598,52,34,C.navy,true);
 txt(t,'demo-first-score','0.11 → CONTINUE',933,489,578,50,34,C.blue,true);txt(t,'demo-first-action','Open the box before asking.',933,549,579,49,28);
 txt(t,'demo-second-score','0.62 → ASK',933,630,578,50,34,C.orange,true);txt(t,'demo-second-action','“Which item should I retrieve?”',933,690,590,52,28);
 txt(t,'timing-caveat','Exploratory timing analysis; playback is compressed 3× during physical motion.',930,771,590,76,24,C.muted);await notes(t,8);

 const u=base(p,9,'A benchmark for asking at the right time','Useful progress, user preference and observable uncertainty must be distinguished.');
 txt(u,'findings-heading','What we established',78,221,670,54,36,C.navy,true);
 const findings=['Three distinct clarification regimes','Leakage-aware layout groups and oracle checks','Shared-planner comparison with real execution'];findings.forEach((a,i)=>{line(u,'finding-line-'+i,82,322+i*104,5,58,C.blue);txt(u,'finding-'+i,a,107,311+i*104,643,79,30);});
 line(u,'closing-divider',803,214,2,534);
 txt(u,'limits-heading','What remains open',860,221,675,54,36,C.navy,true);
 txt(u,'limits','12 Test groups; binary preference choices\nSimple geometry and assisted grasping\nThree rejected commands needed repair',862,315,655,208,29);
 txt(u,'next-heading','Next experiment',860,582,660,53,34,C.blue,true);
 txt(u,'next-body','Scale independent layouts and preference slots;\npre-register timing labels and test robustness.',862,651,655,115,29);
 txt(u,'closing-line','Clarify when missing information blocks useful progress.',78,802,1440,56,34,C.navy,true);await notes(u,9);return {slides:p.slides.items.length};
}
