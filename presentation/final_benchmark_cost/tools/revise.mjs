// Focused edits to the existing nine slides, plus one native speed/cost slide.
// The same callback edits the saved Spaces deck and the permitted local fallback.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const BASE=fileURLToPath(new URL('../',import.meta.url));
const C={bg:'#F7F9FC',navy:'#163650',ink:'#243F56',muted:'#617589',blue:'#1975BC',pale:'#E9F2FA',green:'#218565',line:'#CCD9E5',gray:'#7F90A0'};
function get(s,name){const a=s.shapes.items.find(x=>x.name===name);if(!a)throw Error('Missing original shape '+name);return a;}
function update(s,name,t){const a=get(s,name);a.text=t;return a;}
function txt(s,name,t,x,y,w,h,size=30,color=C.ink,bold=false,align='left'){
 const q=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 q.text=t;q.text.style={fontSize:size,typeface:'Arial',color,bold,alignment:align,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};return q;
}
function table(s,values){
 const widths=[205,165,160,180];
 const t=s.tables.add({name:'estimated-api-costs',rows:values.length,columns:4,left:820,top:325,width:710,height:312,columnWidths:widths,values});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:4}).assign({fill:'#FFFFFF',textStyle:{fontSize:25,typeface:'Arial',color:C.ink,verticalAlignment:'middle',alignment:'center'},margins:{left:10,right:10,top:10,bottom:10},anchor:'center'});
 t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<values.length;r++){t.rows[r].height=78;for(let c=0;c<4;c++){t.getCell(r,c).text.style={fontSize:25,typeface:'Arial',color:r===0?C.navy:C.ink,bold:r===0||c===3,alignment:c===0?'left':'center',verticalAlignment:'middle'};if(r===0)t.getCell(r,c).fill=C.pale;}}
 return t;
}

export async function revise({presentation:p}){
 if(p.slides.items.length!==9)throw Error('Expected the preserved nine-slide base');
 const original=[...p.slides.items];
 const script=JSON.parse(await fs.readFile(path.join(BASE,'speaker_script.json'),'utf8'));
 const cost=JSON.parse(await fs.readFile(path.join(BASE,'analysis/cost_report.json'),'utf8'));
 const cover=original[0];
 update(cover,'research-question','Can a specialized gate reduce decision overhead while keeping tasks reliable?');
 for(const [i,t,d]of [[0,'Missing user preferences','Guessing risks the wrong outcome.'],[1,'Repeated LLM decisions','Each gate call adds latency and API cost.'],[2,'Benchmark question','Reliable clarification with less overhead.']]){
   update(cover,'contribution-'+i,t);update(cover,'contribution-detail-'+i,d);
 }
 const methods=original[4];
 update(methods,'title','Three methods, one shared planner');
 txt(methods,'noask-explanation','May guess missing preferences',75,490,430,30,24,C.muted,false,'center');
 txt(methods,'llm-explanation','Generates a JSON decision',585,490,430,30,24,C.muted,false,'center');
 txt(methods,'jev-explanation','Typed probability, parallel outputs',1095,490,430,30,24,C.muted,false,'center');
 for(const x of [75,585,1095])get(methods,'method-out-'+x).position={left:x+210,top:530,width:26,height:24};
 const metrics=original[5];
 update(metrics,'title','Success, burden and inference overhead');
 update(metrics,'subtitle','Final physical success, user interruption, measured API time and estimated API dollars.');
 update(metrics,'metric-title-2','Inference overhead');
 const definition=update(metrics,'metric-definition-2','Backend tokens + measured API latency\nUSD estimate with cache-aware prices\nAll stages, DONE and retries included');
 definition.position={left:78,top:620,width:650,height:118};definition.text.style={fontSize:26,typeface:'Arial',color:C.ink,alignment:'left',verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};
 update(original[6],'title','Reliability and whole-workflow latency');
 update(original[6],'latency-scope','Totals cover all agent calls, including DONE.\nAPI latency excludes robot execution time.');
 const timing=original[7];update(timing,'page-number','09');
 const closing=original[8];
 update(closing,'page-number','10');update(closing,'title','Conclusions and next experiment');
 update(closing,'subtitle','An auditable benchmark for the reliability and overhead of clarification decisions.');
 update(closing,'finding-0','Both gates: 12/12 success; NoAsk: 10/12');
 update(closing,'finding-1','Jev: lower observed gate response time');
 update(closing,'finding-2','Total estimated cost advantage is modest');
 update(closing,'limits','12 Test groups; binary choices; assisted grasp\nNo BERT or unseen-template comparison\nPrice estimates depend on cache and rates');
 update(closing,'next-body','More independent layouts and repeated runs;\npre-register timing measures and cost checks.');

 const s=p.slides.add({width:1600,height:900,background:{fill:C.bg}});
 txt(s,'title','Gate speed and estimated API cost',65,38,1465,70,46,C.navy,true);
 txt(s,'subtitle','Observed response times and current-price estimates from the same 36 saved Test episodes.',68,115,1462,52,28,C.muted);
 txt(s,'gate-speed-heading','Mean Gate API response (ms)',80,207,710,50,33,C.navy,true);
 const gates=['llm_gate','jev_gate'].map(m=>cost.stages.find(x=>x.method===m&&x.stage==='gate'));
 const chart=s.charts.add('bar',{
  position:{left:80,top:290,width:665,height:357},categories:['LLM-Gate','Jev-Gate'],
  series:[{name:'Mean Gate API response (ms)',values:gates.map(g=>Number(g.mean_latency_ms.toPrecision(15))),fill:C.blue,points:[{idx:0,fill:C.blue},{idx:1,fill:C.green}]}],
  barOptions:{direction:'column',grouping:'clustered',gapWidth:110},hasLegend:false,chartFill:'none',plotAreaFill:'none',
  xAxis:{visible:true,textStyle:{fontSize:27,fill:C.ink},line:{fill:C.line,width:1}},
  yAxis:{visible:true,min:0,max:1000,majorUnit:250,numberFormatCode:'0',textStyle:{fontSize:24,fill:C.muted},majorGridlines:{fill:C.line,width:1}},
  dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0',textStyle:{fontSize:31,bold:true,fill:C.navy}}});
 for(const st of [chart.dataLabels.textStyle,chart.xAxis.textStyle,chart.yAxis.textStyle])st.typeface='Arial';
 txt(s,'gate-sample-counts','53 LLM calls; 54 Jev calls. Different trajectories.',82,674,690,50,25,C.muted);
 txt(s,'speed-interpretation','About 2.8× faster mean Gate response',82,738,700,50,29,C.green,true);
 txt(s,'estimated-usd-heading','Estimated API cost (USD)',820,207,710,50,33,C.navy,true);
 txt(s,'estimated-usd-scope','Total across 12 episodes per method',820,266,710,42,26,C.muted);
 const labels=['NoAsk','LLM-Gate','Jev-Gate'];
 const values=cost.methods.map((m,i)=>[labels[i],'$'+m.estimated_deepseek_usd.toFixed(4),m.estimated_jev_usd===null?'—':'$'+m.estimated_jev_usd.toFixed(4),'$'+m.estimated_total_usd.toFixed(4)]);
 table(s,[['Method','DeepSeek','Jev','Total'],...values]);
 txt(s,'usd-interpretation','Jev vs LLM-Gate: about 3.7% less in total',820,671,710,51,28,C.green,true);
 txt(s,'usd-qualification','NoAsk remains fastest and cheapest overall.',820,738,710,50,27,C.muted);
 txt(s,'pricing-disclosure','Estimates, not invoices. Public prices checked 12 Nov 2026; actual cache hits/misses and off-peak rates.',80,812,1445,35,23,C.muted);
 txt(s,'page-number','08',1484,853,55,30,19,C.muted,false,'right');
 // Existing slide IDs and objects remain intact. Insert only the new evidence slide.
 p.slides.reorder([...original.slice(0,7).map(x=>x.id),s.id,...original.slice(7).map(x=>x.id)]);
 for(const [i,slide]of p.slides.items.entries()){
   slide.speakerNotes.text=script.slides[i].script+'\n\nEvidence and cautions (not spoken): '+script.slides[i].evidence;
 }
 return {slides:p.slides.items.length,originalSlideIdsPreserved:original.map(x=>x.id),newCostSlideId:s.id,
         scriptWords:script.slides.reduce((v,x)=>v+x.spoken_words,0),targetSeconds:580};
}
