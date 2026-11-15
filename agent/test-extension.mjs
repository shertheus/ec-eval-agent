// Integration with the actual Pi SDK; no mock LLM and no paid model call.
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join,resolve,dirname } from "node:path";
import { createAgentSession,DefaultResourceLoader,SessionManager,SettingsManager } from "@earendil-works/pi-coding-agent";

const extensionDir=dirname(new URL(import.meta.url).pathname);
const agentDir=mkdtempSync(join(tmpdir(),"brain-eval-pi-"));
const settingsManager=SettingsManager.inMemory({});
const resourceLoader=new DefaultResourceLoader({cwd:process.cwd(),agentDir,settingsManager,
  noExtensions:true,noSkills:true,noPromptTemplates:true,noThemes:true,noContextFiles:true,
  additionalExtensionPaths:[resolve(extensionDir,"extensions/brain-eval.ts")]});
await resourceLoader.reload();
const loaded=resourceLoader.getExtensions();
assert.equal(loaded.errors.length,0,JSON.stringify(loaded.errors));
const {session}=await createAgentSession({cwd:process.cwd(),agentDir,settingsManager,resourceLoader,
  sessionManager:SessionManager.inMemory()});
try {
  await session.bindExtensions({onError:(e)=>{throw new Error(JSON.stringify(e));}});
  const tools=session.getActiveToolNames();
  assert.equal(tools.length,11,JSON.stringify(tools));
  assert.ok(!tools.includes('bash'));
  const definition=session.getToolDefinition('list_capabilities');
  const result=await definition.execute('sdk-contract-test',{},new AbortController().signal,()=>{},{});
  assert.ok(!result.isError,JSON.stringify(result));
  const catalog=JSON.parse(result.content[0].text);
  assert.equal(catalog.methods.length,5);
  console.log(JSON.stringify({passed:true,pi_tools:tools,backend_methods:catalog.methods.map(m=>m.name),
    scope:'Actual Pi extension loading and tool-to-backend call; LLM end-to-end is not tested'}));
} finally {session.dispose();}
