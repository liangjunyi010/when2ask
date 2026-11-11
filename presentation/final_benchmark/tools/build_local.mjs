// Identical authoring callbacks to the saved Spaces deck, with local media export.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {cover,batch1,batch2,batch3} from './author.mjs';
const BASE=fileURLToPath(new URL('../',import.meta.url));
const BUILD=path.join(BASE,'.build');await fs.mkdir(BUILD,{recursive:true});
const runtime=process.env.RUNTIME_NODE_MODULES||path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const req=createRequire(path.join(runtime,'runtime.cjs'));
const {Presentation,PresentationFile}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const p=Presentation.create({slideSize:{width:1600,height:900}});p.slides.add();
for(const fn of [cover,batch1,batch2,batch3])await fn({presentation:p});
await fs.mkdir(path.join(BASE,'slide_previews'),{recursive:true});
for(const [i,s]of p.slides.items.entries()){
 const b=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(BASE,'slide_previews',`slide-${i+1}.png`),new Uint8Array(await b.arrayBuffer()));
}
await(await PresentationFile.exportPptx(p)).save(path.join(BUILD,'authored.pptx'));
console.log(JSON.stringify({slides:p.slides.items.length,draft:path.join(BUILD,'authored.pptx')}));
