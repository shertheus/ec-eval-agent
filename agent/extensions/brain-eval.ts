import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const base = process.env.BRAIN_EVAL_URL || "http://127.0.0.1:8765";
const guidance = `你是脑连接评测助手。使用注册的brain工具完成实验，不编造数值。
先查询能力，再准备数据和验证协议，验证通过后提交。提交返回任务编号，不代表训练已结束。
仅当用户要求等待完成时，使用wait_seconds短等候查询；不要无限重复查询。
静态因果方法也可用于脑区时间序列，但必须记录其无环和观测样本假设；不要一概拒绝。
IID合成样本不能被自动当成有时间顺序的序列。模型参数和阈值不可根据最终真值挑选。
真实脑数据无真值时不报告结构恢复F1或SHD。结果必须注明实验编号、方法、数据、重复单位与证据路径。
不得仅凭样本数大于节点数声称样本充分。
短预算demo仅验证流程，不保证收敛或方法排名。失败运行必须披露。
重试保持原协议；修改参数应提交新实验。解释可能原因时与实际观测分开。
用户询问课程反思时提供实验记录，供用户独立撰写。`;

async function api(path: string, payload?: unknown, signal?: AbortSignal) {
  const response = await fetch(base + path, {
    method: payload === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(150000)]) : AbortSignal.timeout(150000),
  });
  const body = await response.json() as any;
  if (!response.ok || !body.ok) throw new Error(JSON.stringify(body.error || body));
  return body.data;
}

export default function (pi: ExtensionAPI) {
  const names: string[] = [];
  function register(name: string, description: string, parameters: any, call: (p: any, signal: AbortSignal | undefined) => Promise<any>) {
    names.push(name);
    pi.registerTool({ name, label: name, description, parameters,
      async execute(_id, params, signal) {
        try {
          const data = await call(params, signal);
          return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }], details: { data } };
        } catch (e) {
          const message = e instanceof Error ? e.message : String(e);
          return { content: [{ type: "text", text: JSON.stringify({ ok: false, error: message }) }], details: { error: message }, isError: true };
        }
      },
    });
  }
  register("inspect_environment", "检查评测后端与软件、GPU信息；不代表模型或所有算法已验证。", Type.Object({}), (_,s)=>api("/v1/environment",undefined,s));
  register("list_capabilities", "查询可用算法、数据生成器、参数范围和评价指标。", Type.Object({}), (_,s)=>api("/v1/capabilities",undefined,s));
  register("prepare_dataset", "导入或生成数据。import的path必须位于已配置input目录。rows为观测或时间，columns为脑区。", Type.Object({
    kind: Type.Union([Type.Literal("sem"),Type.Literal("var"),Type.Literal("import")]),
    name: Type.Optional(Type.String()), nodes: Type.Optional(Type.Integer()), samples: Type.Optional(Type.Integer()),
    edges: Type.Optional(Type.Integer()),seed: Type.Optional(Type.Integer()),
    mechanism: Type.Optional(Type.Union([Type.Literal("linear"),Type.Literal("mlp"),Type.Literal("tanh")])),
    noise_scale: Type.Optional(Type.Number()),path: Type.Optional(Type.String()),
    input_kind: Type.Optional(Type.Union([Type.Literal("iid"),Type.Literal("timeseries")])),
    node_ids: Type.Optional(Type.Array(Type.String())),source: Type.Optional(Type.String()),sample_interval: Type.Optional(Type.Number()),
  }), (p,s)=>api("/v1/datasets",p,s));
  const protocol = Type.Object({
    title: Type.String(),dataset_ids: Type.Array(Type.String(),{minItems:1}),
    methods: Type.Array(Type.Object({name:Type.Union(["notears","golem","dag_gnn","granger","neural_gc"].map(x=>Type.Literal(x))),
      device:Type.Union([Type.Literal("cpu"),Type.Literal("cuda")]),
      params:Type.Optional(Type.Record(Type.String(),Type.Union([Type.Number(),Type.String(),Type.Boolean()])))})),
    seeds:Type.Array(Type.Integer(),{minItems:1}),timeout_seconds:Type.Optional(Type.Integer()),
  });
  register("validate_protocol", "检查协议，返回规范化参数、风险提示和最大超时预算；不启动实验。", Type.Object({protocol}), (p,s)=>api("/v1/protocols/validate",p.protocol,s));
  register("submit_experiment", "提交已检查的协议。使用唯一幂等键防止重复提交。返回任务编号。",Type.Object({protocol,idempotency_key:Type.String()}), (p,s)=>api("/v1/experiments",p,s));
  register("inspect_experiment", "查询任务和日志。省略编号列出近期任务。可短暂等待状态变化，最多10秒。",Type.Object({
    experiment_id:Type.Optional(Type.String()),logs:Type.Optional(Type.Boolean()),wait_seconds:Type.Optional(Type.Integer({minimum:0,maximum:10}))}),
    async (p,s)=>{
      if (!p.experiment_id) return api("/v1/experiments",undefined,s);
      const path=`/v1/experiments/${encodeURIComponent(p.experiment_id)}?logs=${!!p.logs}`;
      let data=await api(path,undefined,s);
      const initial=JSON.stringify(data.counts);
      const end=Date.now()+(p.wait_seconds||0)*1000;
      while (Date.now()<end && ["queued","running"].includes(data.status)) {
        if (s?.aborted) throw new Error("Cancelled wait; experiment remains running");
        await new Promise(r=>setTimeout(r,1000));
        data=await api(path,undefined,s);
        if(JSON.stringify(data.counts)!==initial) break;
      }
      return data;
    });
  register("control_experiment", "取消任务或显式重试失败/中断任务；不会改动参数。",Type.Object({experiment_id:Type.String(),action:Type.Union([Type.Literal("cancel"),Type.Literal("retry")])}),
    (p,s)=>api(`/v1/experiments/${encodeURIComponent(p.experiment_id)}/actions`,{action:p.action},s));
  register("collect_results", "核验结果文件校验和，计算汇总，导出CSV、SVG与HTML报告。",Type.Object({experiment_id:Type.String()}),
    (p,s)=>api(`/v1/experiments/${encodeURIComponent(p.experiment_id)}/results`,undefined,s));
  register("inspect_dataset", "核验数据校验和并返回每个节点的描述统计，不返回原始时序。",Type.Object({dataset_id:Type.String()}),
    (p,s)=>api(`/v1/datasets/${encodeURIComponent(p.dataset_id)}`,undefined,s));
  register("compare_experiments", "对比已结束的实验，默认要求数据内容与语义相同，披露设备参数种子，不自动排名。",Type.Object({
    experiment_ids:Type.Array(Type.String(),{minItems:2,maxItems:20}),strict_dataset_match:Type.Optional(Type.Boolean())}),
    (p,s)=>api("/v1/comparisons",p,s));
  register("export_experiment", "核验并导出终态实验的证据ZIP，不含原始数据或模型密钥。返回服务端路径及SHA256。",Type.Object({experiment_id:Type.String()}),
    (p,s)=>api(`/v1/experiments/${encodeURIComponent(p.experiment_id)}/export`,{},s));
  pi.on("session_start", async (_event,ctx)=>{
    pi.setActiveTools(names);
    ctx.ui.notify("脑连接评测模式：11个领域工具已加载；输入需求开始。", "info");
  });
  pi.on("before_agent_start", async(event)=>({systemPrompt: `${event.systemPrompt}\n\n${guidance}`}));
}
