// Author editable slides with Artifact Tool. Media embedding is a separate OOXML step.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {BASE, BUILD, requireRuntime} from './runtime.mjs';
const {Presentation, PresentationFile}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);

const notes=[
`When2Ask asks a simple question: when should a robot ask for clarification, and when can it already make useful progress?

This replay comes from a real recorded PyBullet episode with a Panda arm. The user has specified the blue cup, but has not yet chosen a block or a lid. Jev first returns an ASK probability of 0.14, so the shared DeepSeek planner packs the cup. Only then does Jev return 0.70, and the robot asks which block and lid to use. The simulated user answers, and the robot packs the block and covers the box.

The robot frames and highlighted flow share one recorded timeline. These are actual simulated physics actions with a documented constraint grasp, not hardware execution. An independent physical evaluator checks the final result.

The key idea is to clarify only when missing information blocks useful progress.`,
`The milestone system now supports two task templates: pack and cover, and placing objects into selected containers. We generated 32 Dev samples and 128 held-out Test samples, separated by base physical layout groups. All 160 passed actual physical oracle execution. The Phase 3 system also passed 96 automated tests and integrates real DeepSeek and Jev APIs.

This table shows a small Dev comparison across eight independent groups. NoAsk succeeded in five of eight cases. Both clarification gates succeeded in seven. Jev at threshold 0.5 used slightly less clarification and showed 39.66 seconds of cumulative API latency, compared with 58.21 seconds for the LLM gate. These are totals across eight episodes, not averages.

This is preliminary evidence, with limited preference coverage in the online subset. It does not establish a statistical advantage. Our next step is the frozen evaluation: 128 held-out samples, each run with all three methods. That Test has not run yet.`
];
const sources=[
`Source: outputs/phase2_live/paired_v2/validation_002/jev_gate/{episode.json,evaluation.json,api_attempts.jsonl,demo.gif}. Frame-indexed HTML replay: presentation/milestone/web/timeline.json. Inference instants within recorded frames were not captured and are not reconstructed. The 19.16 s highlight compresses only display time, preserving source order and synchronized left/right states.`,
`Sources: docs/phase3/dev_report.md; outputs/phase3/pytest_final.xml; outputs/phase3_live/dev/*/{episode.json,evaluation.json,api_attempts.jsonl}; frozen configs/frozen_test.yaml. All table values are rounded from original episode totals. LLM-NoAsk: 5/8, burden 0/8, latency 24.350076 s. LLM-Gate: 7/8, burden 12/8, latency 58.213124 s. Jev-Gate 0.5: 7/8, burden 11/8, latency 39.658448 s. Only two preference triples per template occur in the selected online subset; all selected blocks are green and all pack/cover lids black. Formal Test model calls remain zero. The 96-test figure describes the preserved Phase 3 milestone snapshot; separate replay tests are additional.`
];

await fs.writeFile(path.join(BASE,'speaker_notes.md'),
  '# When2Ask milestone speaker notes\n\nApproximately 2 minutes at 140–155 words per minute (294 spoken words). Sources below are not spoken.\n\n'+
  notes.map((n,i)=>`## Slide ${i+1} (about 60 seconds)\n\n${n}\n\nSource notes: ${sources[i]}\n`).join('\n'));

const p=Presentation.create({slideSize:{width:1920,height:1080}});
const navy='#193755',ink='#29445F',muted='#627991',blue='#176FB9',bg='#F7FAFE';
function text(s,name,content,x,y,w,h,size=32,color=ink,bold=false,align='left'){
  const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  o.text=content;
  o.text.style={fontSize:size,typeface:'Arial',color,bold,alignment:align,verticalAlignment:'middle',insets:0,autoFit:'none',wrap:'square'};
  return o;
}
const s1=p.slides.add();s1.background.fill=bg;
text(s1,'slide-1-title','When2Ask: When Should a Robot Ask?',72,22,1776,70,52,navy,true);
text(s1,'research-problem','Robots must decide when clarification is necessary and when they can make useful progress.',72,96,1776,45,29,ink);
const poster=new Uint8Array(await fs.readFile(path.join(BUILD,'highlight_frames/0000.jpg')));
s1.images.add({name:'synchronized-replay-video',blob:poster,contentType:'image/jpeg',position:{left:192,top:152,width:1536,height:864},fit:'contain',alt:'Real recorded Panda execution and synchronized Jev/DeepSeek decision flow. Embedded animation.'});
text(s1,'main-takeaway','Clarify only when missing information blocks useful progress.',192,1026,1536,38,28,blue,true,'center');
s1.speakerNotes.text=notes[0]+'\n\n'+sources[0];

const s2=p.slides.add();s2.background.fill=bg;
text(s2,'slide-2-title','Implementation Progress & Preliminary Evaluation',72,28,1776,75,52,navy,true);
text(s2,'implementation-heading','Implemented and physically verified',80,162,605,52,34,blue,true);
const achievements=[
  'Two robotic task templates',
  'Procedurally generated benchmark',
  '32 Dev / 128 held-out Test samples',
  '160/160 physical oracle validation',
  '96 automated tests passed',
  'Real DeepSeek/Jev integration'
];
achievements.forEach((item,i)=>text(s2,`achievement-${i+1}`,item,80,244+i*79,610,64,31,ink));
text(s2,'dev-heading','Small Dev comparison',745,162,1095,52,34,blue,true);
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
text(s2,'result-takeaway','Both clarification gates achieved 7/8 success.\nJev showed lower observed API latency.',745,670,1095,108,33,navy,true);
text(s2,'pilot-caveat','Preliminary Dev results (8 independent groups), with limited preference coverage.\nNot a statistical or held-out Test conclusion.',80,860,1760,88,27,muted);
text(s2,'next-step','Next: Frozen held-out evaluation, 128 samples × 3 methods',80,982,1760,55,36,blue,true);
text(s2,'test-status','Formal Test has not run.',80,1036,1760,30,24,muted);
s2.speakerNotes.text=notes[1]+'\n\n'+sources[1];

await fs.mkdir(path.join(BUILD,'author_previews'),{recursive:true});
for(const [i,s] of p.slides.items.entries()){
  const blob=await p.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(BUILD,`author_previews/slide-${i+1}-artifact.png`),new Uint8Array(await blob.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(BUILD,'slides-authored.pptx'));
await fs.writeFile(path.join(BUILD,'speaker_notes.json'),JSON.stringify({notes,sources},null,2));
console.log(JSON.stringify({slides:2,canvas:[1920,1080],native_table_slide:2,spoken_words:notes.map(n=>n.split(/\s+/).length),draft:path.join(BUILD,'slides-authored.pptx')}));
