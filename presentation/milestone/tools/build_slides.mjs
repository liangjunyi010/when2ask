// Author editable slides with Artifact Tool. Media embedding is a separate OOXML step.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {BASE, BUILD, requireRuntime} from './runtime.mjs';
const {Presentation, PresentationFile}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);

const script=JSON.parse(await fs.readFile(path.join(BASE,'speaker_script.json'),'utf8'));
const notes=script.slides.map(s=>s.script);
const wordCounts=notes.map(n=>n.split(/\s+/).length);
const schedule=JSON.parse(await fs.readFile(path.join(BASE,'export_schedule.json'),'utf8'));
const highlight=schedule.exports.find(e=>e.view==='highlight');
const sources=[
`Source: outputs/phase2_live/paired_v2/validation_002/jev_gate/{episode.json,evaluation.json,api_attempts.jsonl,demo.gif}. Frame-indexed HTML replay: presentation/milestone/web/timeline.json. Inference instants within recorded frames were not captured and are not reconstructed. The ${(highlight.duration_ms/1000).toFixed(2)} s highlight compresses only display time, preserving source order and synchronized left/right states. Actual PyBullet Panda execution uses a documented constraint grasp.`,
`Sources: docs/phase3/dev_report.md; outputs/phase3/pytest_final.xml; outputs/phase3_live/dev/*/{episode.json,evaluation.json,api_attempts.jsonl}; frozen configs/frozen_test.yaml. All table values are rounded from original episode totals. LLM-NoAsk: 5/8, burden 0/8, latency 24.350076 s. LLM-Gate: 7/8, burden 12/8, latency 58.213124 s. Jev-Gate 0.5: 7/8, burden 11/8, latency 39.658448 s. Only two preference triples per template occur in the selected online subset; all selected blocks are green and all pack/cover lids black. Formal Test model calls remain zero. The 96-test figure describes the preserved Phase 3 milestone snapshot; separate replay tests are additional.`
];

await fs.writeFile(path.join(BASE,'speaker_notes.md'),
  `# When2Ask milestone speaker notes\n\nUser-provided script, preserved verbatim without Markdown emphasis. ${wordCounts.reduce((a,b)=>a+b,0)} spoken words. Target total: 115–125 seconds. Source notes below are not spoken.\n\n`+
  notes.map((n,i)=>`## Slide ${i+1} — ${script.slides[i].title}\n\nTarget: ${script.slides[i].target_seconds.join('–')} seconds (${wordCounts[i]} words).\n\n${n}\n\nSource notes: ${sources[i]}\n`).join('\n'));

const p=Presentation.create({slideSize:{width:1920,height:1080}});
const navy='#193755',ink='#29445F',muted='#627991',blue='#176FB9',bg='#F7FAFE';
function text(s,name,content,x,y,w,h,size=32,color=ink,bold=false,align='left'){
  const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  o.text=content;
  o.text.style={fontSize:size,typeface:'Arial',color,bold,alignment:align,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};
  return o;
}
const s1=p.slides.add();s1.background.fill=bg;
text(s1,'slide-1-title',script.slides[0].title,72,22,1776,70,52,navy,true);
text(s1,'research-problem','Only the cup choice is known. When should the robot ask, and when should it continue?',72,96,1776,45,29,ink);
const poster=new Uint8Array(await fs.readFile(path.join(BUILD,'highlight_frames/0000.jpg')));
s1.images.add({name:'synchronized-replay-video',blob:poster,contentType:'image/jpeg',position:{left:192,top:152,width:1536,height:864},fit:'contain',alt:'Real recorded Panda execution and synchronized Jev/DeepSeek decision flow. Embedded animation.'});
text(s1,'main-takeaway','0.14: continue with the known cup.     0.70: ask about the block and lid.',192,1026,1536,38,28,blue,true,'center');
s1.speakerNotes.text=notes[0]+'\n\n'+sources[0];

const s2=p.slides.add();s2.background.fill=bg;
text(s2,'slide-2-title',script.slides[1].title,72,28,1776,75,52,navy,true);
text(s2,'implementation-heading','Procedurally generated benchmark',80,162,625,52,34,blue,true);
text(s2,'task-types-heading','Two robotic task types',80,242,625,50,32,navy,true);
text(s2,'task-types','Packing and covering\nObjects into selected containers',80,300,625,100,30,ink);
text(s2,'dataset-size','32 Dev / 128 held-out Test samples',80,430,625,64,31,ink);
text(s2,'physical-checks','160/160 physical feasibility checks',80,505,625,64,31,ink);
text(s2,'automated-tests','96 automated tests passed',80,580,625,64,31,ink);
text(s2,'api-integration','DeepSeek and Jev integrated',80,655,625,64,31,ink);
text(s2,'dev-heading','8 development scenarios',745,162,1095,52,34,blue,true);
const table=s2.tables.add({rows:4,columns:4,left:745,top:240,width:1095,height:336,
  columnWidths:[385,185,260,265],values:[
    ['Method','Success','Avg. burden','API latency'],
    ['LLM-NoAsk','5/8','0.000','24.35 s'],
    ['LLM-Gate','7/8','1.500','58.21 s'],
    ['Jev-Gate (0.5)','7/8','1.375','39.66 s']
  ]});
table.cells.block({row:0,column:0,rowCount:4,columnCount:4}).assign({fill:'#FFFFFF',textStyle:{fontSize:29,typeface:'Arial',color:ink,verticalAlignment:'middle',alignment:'center',insets:15},margins:{left:18,right:18,top:15,bottom:15},anchor:'center'});
table.borders.assign({style:'solid',fill:'#DAE4EF',width:1});
for(let r=0;r<4;r++){
  table.rows[r].height=84;
  table.getCell(r,0).text.style={fontSize:29,typeface:'Arial',color:ink,alignment:'left',verticalAlignment:'middle'};
  for(let c=0;c<4;c++){
    if(r===0){table.getCell(r,c).fill='#E6EFF9';table.getCell(r,c).text.style={fontSize:28,typeface:'Arial',bold:true,color:navy,alignment:c===0?'left':'center',verticalAlignment:'middle'};}
    if(r===3){table.getCell(r,c).fill='#ECF4FC';table.getCell(r,c).text.style={fontSize:29,typeface:'Arial',color:blue,bold:true,alignment:c===0?'left':'center',verticalAlignment:'middle'};}
  }
}
text(s2,'latency-definition','API latency is cumulative over 8 episodes for each method.',745,594,1095,44,25,muted);
text(s2,'result-takeaway','Both gates: 7/8 success with similar burden\nJev: ~40 s total API latency vs ~58 s for LLM-Gate',745,670,1095,108,32,navy,true);
text(s2,'pilot-caveat','Preliminary Dev results (8 independent groups), with limited preference coverage.\nNot a statistical or held-out Test conclusion.',80,860,1760,88,27,muted);
text(s2,'next-step','Next: Held-out evaluation and clarification timing analysis',80,982,1760,55,36,blue,true);
text(s2,'test-status','128 held-out samples × 3 methods. Formal Test has not run.',80,1036,1760,30,24,muted);
s2.speakerNotes.text=notes[1]+'\n\n'+sources[1];

await fs.mkdir(path.join(BUILD,'author_previews'),{recursive:true});
for(const [i,s] of p.slides.items.entries()){
  const blob=await p.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(BUILD,`author_previews/slide-${i+1}-artifact.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(BUILD,'slides-authored.pptx'));
await fs.writeFile(path.join(BUILD,'speaker_notes.json'),JSON.stringify({notes,sources},null,2));
console.log(JSON.stringify({slides:2,canvas:[1920,1080],native_table_slide:2,spoken_words:notes.map(n=>n.split(/\s+/).length),draft:path.join(BUILD,'slides-authored.pptx')}));
