// Node 22 loads the config via --env-file; no shell evaluation of credential values.
import { mkdirSync,readFileSync,writeFileSync,existsSync } from 'node:fs';
import { resolve,dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const agentDir=process.env.PI_CODING_AGENT_DIR || resolve(root,'.runtime/pi');
process.env.PI_CODING_AGENT_DIR=agentDir;
mkdirSync(agentDir,{recursive:true,mode:0o700});
const load=(name)=>existsSync(resolve(agentDir,name))?JSON.parse(readFileSync(resolve(agentDir,name),'utf8')):{};
const model=process.env.DEEPSEEK_MODEL || 'deepseek-flash';
const config=load('models.json');
config.providers ??= {};
config.providers.deepseek={...(config.providers.deepseek||{}),
  baseUrl:process.env.DEEPSEEK_BASE_URL||'https://api.deepseek.com',
  api:'openai-completions',apiKey:'${DEEPSEEK_API_KEY}',
  models:[{id:model,input:['text'],reasoning:false,maxTokens:8192}]};
writeFileSync(resolve(agentDir,'models.json'),JSON.stringify(config,null,2),{mode:0o600});
const settings=load('settings.json');
settings.defaultProvider='deepseek';settings.defaultModel=model;
settings.defaultThinkingLevel='off';
writeFileSync(resolve(agentDir,'settings.json'),JSON.stringify(settings,null,2),{mode:0o600});
const args=['--no-extensions','--no-skills','--no-prompt-templates','-e',resolve(root,'agent/extensions/brain-eval.ts'),
  '--provider','deepseek','--model',model,...process.argv.slice(2)];
const result=spawnSync(process.execPath,[resolve(root,'agent/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'),...args],
  {cwd:resolve(root,'agent'),env:process.env,stdio:'inherit'});
if(result.error){console.error(result.error.message);process.exit(1);}
process.exit(result.status??1);
