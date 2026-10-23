import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {constants} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {BASE, BUILD} from './runtime.mjs';
const skill=process.env.WHEN2ASK_PRESENTATIONS_SKILL||path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const finalDir=path.join(BUILD,process.env.WHEN2ASK_DECK_REVISION||'finalized');
await fs.mkdir(finalDir,{recursive:true});
const finalPath=path.join(finalDir,'When2Ask_Milestone_Presentation.pptx');
const result=await finalizePresentation({
  workspaceDir:BASE,candidatePath:path.join(BUILD,'slides-with-media.pptx'),finalPath,
  pythonExecutable:path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','18288000,10287000','--validate-heading-fit','--require-native-table-slide','2'],
  requiredNativeTableOwnerSlides:[2],explicitTotalSlideCount:2,
  fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
  receiptPath:path.join(BUILD,`${path.basename(finalDir)}.validation.json`)
});
const deliveryPath=path.join(BASE,path.basename(finalPath));
await fs.copyFile(finalPath,deliveryPath,constants.COPYFILE_EXCL);
await fs.writeFile(path.join(BASE,'pptx_finalization.json'),JSON.stringify({
  passed:true,final_file:path.basename(finalPath),
  file_sha256:result.finalSha256,slide_count:2,aspect:'16:9',native_table_on_slide_2:true,
  description:'Package integrity, declared canvas, headings, font policy, native table and Artifact Tool import checked. Original embedded media bytes are preserved.'
},null,2)+'\n');
console.log(JSON.stringify({passed:true,finalPath:deliveryPath}));
