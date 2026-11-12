import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL,fileURLToPath} from 'node:url';
const BASE=fileURLToPath(new URL('../',import.meta.url));
const SKILL=path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations/26.1104.22356/skills/presentations');
const runtime=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime,'node/node_modules');
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const ref=JSON.parse(await fs.readFile(path.join(BASE,'checks/source.json'),'utf8'));
const result=await finalizePresentation({workspaceDir:BASE,candidatePath:path.join(BASE,'.build/with-media.pptx'),
 finalPath:path.join(BASE,'deliverables/When2Ask_Team11_Updated_Final.pptx'),
 pythonExecutable:path.join(runtime,'python/bin/python3'),
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-heading-fit','--require-native-table-slide','8'],
 requiredNativeTableOwnerSlides:[8],requiredNativeChartOwnerSlides:[9],
 materializeLiteralChartWorkbooks:true,explicitTotalSlideCount:11,
 fontPolicy:{basis:'reference',families:['Helvetica Neue','Times New Roman'],referencePath:path.join(BASE,'.build/source.pptx'),referenceSha256:ref.sha256},
 verifyArtifactToolImport:true,receiptPath:path.join(BASE,'checks/finalization.json')});
console.log(JSON.stringify(result));
