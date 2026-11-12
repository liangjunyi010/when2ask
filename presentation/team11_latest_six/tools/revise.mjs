import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const BASE=fileURLToPath(new URL('../',import.meta.url));
const ROOT=fileURLToPath(new URL('../../../',import.meta.url));
const FONT='Helvetica Neue';
const C={ink:'#111111',muted:'#53616D',line:'#D6DEE4',blue:'#2370A8',green:'#168570',orange:'#B77317',purple:'#875AAF',pale:'#EFF5F9'};
const names=['NoAsk','LLM-Gate','Jev-Gate','Single-call'];
const colors=['#8292A2',C.blue,C.green,C.purple];
function text(s,name,value,x,y,w,h,size=28,color=C.ink,bold=false,alignment='left'){
 const q=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=value;q.text.style={fontSize:size,typeface:FONT,color,bold,alignment,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};return q;
}
function clear(p,s){const items=[...s.shapes.items,...s.images.items,...s.tables.items,...s.charts.items];if(items.length)p.delete(items.map(x=>x.toSnapshot().aid));s.background.fill='#FFFFFF';}
function title(s,n,value,subtitle){text(s,'title',value,70,40,1450,80,46,C.ink,true);if(subtitle)text(s,'subtitle',subtitle,90,135,1430,70,28,C.muted);text(s,'page-number',String(n),1490,850,50,30,20,C.ink,false,'right');}
function line(s,name,pts,color=C.blue,arrow=true){for(let i=1;i<pts.length;i++){let [x1,y1]=pts[i-1],[x2,y2]=pts[i];s.shapes.add({name:name+'-'+i,geometry:'connector',kind:'straight',position:{left:Math.min(x1,x2),top:Math.min(y1,y2),width:Math.abs(x2-x1),height:Math.abs(y2-y1),horizontalFlip:x2<x1,verticalFlip:y2<y1},line:{fill:color,width:2.5},tail:{type:arrow&&i===pts.length-1?'triangle':'none',width:'med',length:'med'}});}}
function node(s,name,label,x,y,w,h,color=C.blue,fill=C.pale,size=24){s.shapes.add({name:name+'-box',geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:color,width:1.2}});text(s,name,label,x+10,y+5,w-20,h-10,size,C.ink,false,'center');}
async function image(s,name,file,x,y,w,h){s.images.add({name,path:file,position:{left:x,top:y,width:w,height:h},fit:'contain',alt:name});}
const pct=n=>(100*n).toFixed(1)+'%';

export async function revise({presentation:p,input}){
 const meta=JSON.parse(await fs.readFile(path.join(BASE,'assets/metrics.json'),'utf8'));
 const rows=meta.rows;const script=JSON.parse(await fs.readFile(path.join(BASE,'speaker_script.json'),'utf8'));
 for(const n of input.slides){
  const s=p.slides.getItem(n-1);clear(p,s);
  if(n===6){
   title(s,6,'Nine Robotic Task Types','Manipulation, navigation and inspection under partial information');
   const tasks=[
    [0,'Pack & Cover','Select items, pack them,\nthen cover the box.'],
    [1,'Two Containers','Choose objects and their\ndestination containers.'],
    [3,'Category Sorting','Sort categories using\na user-selected rule.'],
    [4,'Inventory Restock','Add items until the\nrequested counts are met.'],
    [5,'Retrieve & Restore','Open, retrieve the chosen\nitem, then close the box.'],
    [6,'Buffered Exchange','Swap two objects using\na selected temporary pad.'],
    [2,'Find & Approach','Search rooms and\napproach the target.'],
    [7,'Patrol & Return','Visit checkpoints,\nthen return to the start.'],
    [8,'Reveal & Inspect','Remove an obstruction\nand read the hidden label.']
   ];
   for(const [i,[idx,label,desc]] of tasks.entries()){
    const x=80+(i%3)*495,y=230+Math.floor(i/3)*187;
    await image(s,'Real scene: '+label,path.join(BASE,'assets/task_'+idx+'.png'),x,y,180,135);
    text(s,'task-'+i,label,x+198,y-1,275,47,28,C.ink,true);
    text(s,'description-'+i,desc,x+198,y+48,275,79,23,C.muted);
   }
   text(s,'coverage-summary','Vary information disclosure, user choices and layouts. Validate every case with real physics.',90,805,1430,40,25,C.muted);
  }
  if(n===7){
   title(s,7,'How the Three Gate Methods Work','The same DeepSeek planner turns each decision into a question or a robot action.');
   text(s,'method-noask','LLM-NoAsk',80,226,215,55,30,colors[0],true);
   node(s,'state-noask','Public state',320,220,190,70);
   node(s,'skip','Always\nCONTINUE',590,220,210,70,colors[0],'#F3F5F7',24);
   node(s,'action-noask','DeepSeek\nAction planner',950,220,245,70);
   node(s,'robot-noask','Robot action',1325,220,205,70);
   line(s,'noask-1',[[510,255],[590,255]],colors[0]);line(s,'noask-2',[[800,255],[950,255]],colors[0]);line(s,'noask-3',[[1195,255],[1325,255]],colors[0]);
   for(const [id,label,y,color,gate]of [['llm','LLM-Gate',435,C.blue,'DeepSeek Gate\nASK / CONTINUE'],['jev','Jev-Gate',675,C.green,'Jev Gate\nASK if p ≥ 0.5']]){
    text(s,'method-'+id,label,80,y-25,215,55,30,color,true);
    node(s,'state-'+id,'Public state',320,y-35,190,70);
    node(s,'gate-'+id,gate,590,y-35,210,70,color,id==='jev'?'#EDF7F3':C.pale,23);
    line(s,id+'-state-gate',[[510,y],[590,y]],color);
    const high=y-72,low=y+72;
    node(s,'question-'+id,'DeepSeek\nQuestion planner',950,high-35,245,70,C.orange,'#FFF5E8',24);
    node(s,'answer-'+id,'User answer',1325,high-35,205,70,C.orange,'#FFF5E8',24);
    node(s,'action-'+id,'DeepSeek\nAction planner',950,low-35,245,70,C.blue,C.pale,24);
    node(s,'robot-'+id,'Robot action',1325,low-35,205,70,C.blue,C.pale,24);
    line(s,id+'-ask',[[800,y],[840,y],[840,high],[950,high]],C.orange);
    line(s,id+'-continue',[[800,y],[840,y],[840,low],[950,low]],C.blue);
    text(s,id+'-ask-label','ASK',853,high-29,90,24,20,C.orange,true,'center');
    text(s,id+'-continue-label','CONTINUE',842,low+5,107,25,18,C.blue,true,'center');
    line(s,id+'-question-user',[[1195,high],[1325,high]],C.orange);
    line(s,id+'-action-robot',[[1195,low],[1325,low]],C.blue);
   }
   text(s,'extra-baseline','Additional baseline: Single-call DeepSeek chooses ASK, an action or DONE in one request.',90,811,1440,42,25,C.muted);
  }
  if(n===8){
   title(s,8,'Cross-Model Evaluation','Same LLM-Gate workflow: each model serves as both gate and planner.');
   const ds=rows.find(r=>r.method==='llm_gate');
   const values=[['API model','Task success','API time','Estimated\nAPI cost','Unnecessary\nASK rate'],['GPT-5.6','','','',''],['DeepSeek Flash',pct(ds.success),'100.0%','100.0%',pct(ds.fpr)],['GLM 5.2','','','','']];
   const widths=[340,240,260,280,320],t=s.tables.add({name:'cross-model-results',rows:4,columns:5,left:80,top:255,width:1440,height:380,columnWidths:widths,values});
   t.cells.block({row:0,column:0,rowCount:4,columnCount:5}).assign({fill:'#FFFFFF',textStyle:{fontSize:28,typeface:FONT,color:C.ink,alignment:'center',verticalAlignment:'middle'},margins:{left:16,right:16,top:12,bottom:12},anchor:'center'});
   t.borders.assign({fill:C.line,width:1,style:'solid'});
   for(let r=0;r<4;r++){t.rows[r].height=95;for(let c=0;c<5;c++){t.getCell(r,c).text.style={fontSize:r===0?27:30,typeface:FONT,color:C.ink,bold:r===0||r===2,alignment:c===0?'left':'center',verticalAlignment:'middle'};t.getCell(r,c).fill=r===0?'#F1F4F6':r===2?'#EAF3F9':'#FFFFFF';}}
   text(s,'normalization','API time and estimated cost: DeepSeek Flash = 100%. Lower is better.',90,670,1420,50,29,C.ink);
   text(s,'pending','Blank cells are reserved for experiments that have not yet been run.',90,738,1420,45,26,C.muted);
   text(s,'scope','Current evidence is a development pilot. It does not establish a cross-model ranking.',90,800,1420,40,25,C.muted);
  }
  if(n===9){
   title(s,9,'Method Comparison with a Shared Planner','Same nine-task Dev cases. API time and estimated cost are relative to LLM-Gate = 100%.');
   for(const [i,key,heading]of [[0,'success','Task success'],[1,'time','Relative API time'],[2,'cost','Relative estimated cost']]){
    const x=65+i*505;text(s,'chart-heading-'+key,heading,x,230,470,55,30,C.ink,true,'center');
    s.charts.add('bar',{name:'metrics-'+key,position:{left:x,top:295,width:470,height:335},categories:names,
     series:[{name:heading,values:rows.map(r=>Number(r[key].toFixed(10))),valuesFormatCode:'0.0%',fill:C.blue,points:colors.map((fill,idx)=>({idx,fill}))}],
     hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:80},
     dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:22,typeface:FONT,bold:true,color:C.ink}},
     xAxis:{textStyle:{fontSize:19,typeface:FONT,color:C.ink},majorTickMark:'none',minorTickMark:'none'},
     yAxis:{min:0,max:1.15,majorUnit:.25,numberFormatCode:'0%',textStyle:{fontSize:19,typeface:FONT,color:C.muted},majorGridlines:{fill:C.line,width:1,style:'solid'}},
     chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF'});
   }
   const j=rows.find(r=>r.method==='jev_gate');
   text(s,'savings',`Jev used ${pct(1-j.time)} less API time and ${pct(1-j.cost)} lower estimated cost than LLM-Gate.`,90,660,1430,52,30,C.green,true);
   text(s,'success-tradeoff','Success: 96.3% for Jev and Single-call, compared with 100.0% for LLM-Gate.',90,725,1430,43,27,C.ink);
   text(s,'false-alarm','Observed unnecessary ASK: 0% for the three asking methods. NoAsk: not applicable.',90,782,1430,37,24,C.muted);
   text(s,'pilot-caveat','Small Dev pilot; results do not establish a general ranking.',90,828,1350,32,23,C.muted);
  }
  if(n===10){
   await image(s,'command-center-video',path.join(ROOT,'presentation/command_center_demo_v1/screenshots/01_empty.png'),0,0,1600,900);
  }
  if(n===11){
   title(s,11,'Conclusions and Limitations');
   text(s,'benchmark-heading','A benchmark for clarification timing',90,200,1410,60,36,C.ink,true);
   text(s,'benchmark-body','Nine task types vary layouts, user preferences and available information.',90,269,1410,58,30,C.muted);
   text(s,'method-heading','A separate Jev decision gate',90,370,1410,60,36,C.ink,true);
   text(s,'method-body','Lower observed API time and estimated cost than the separate LLM gate,\nwith a small success-rate trade-off in this Dev pilot.',90,440,1410,104,30,C.muted);
   text(s,'limitation-heading','Limitations',90,585,650,52,32,C.ink,true);
   text(s,'limitation-body','Small Dev sample and fixed robot skills.\nPlanner errors occur even with complete instructions.\nReal-robot transfer remains untested.',90,650,700,135,27,C.muted);
   text(s,'next-heading','Next steps',900,585,610,52,32,C.ink,true);
   text(s,'next-body','More independent layouts and repeated runs.\nComplete the cross-model evaluation.\nKeep future Test settings fixed.',900,650,610,135,27,C.muted);
  }
  s.speakerNotes.text=script.slides.find(x=>x.slide===n).notes;
 }
 return {edited:input.slides,totalSlides:p.slides.items.length,modelsPending:['GPT-5.6','GLM 5.2'],metricsSource:meta.source};
}
