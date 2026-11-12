"""Build the independent English UI from preserved legacy display assets.

Only display copy changes. No model prompt, action or user utterance is translated.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'presentation/console_en'
WEB=BASE/'web'
WEB.mkdir(parents=True,exist_ok=True)
translations={
 '机器人画面墙':'Live robot wall','方法对比':'Method comparison','澄清队列':'Clarification queue',
 '远程派发 · 实时观察 · 在必要时澄清':'Dispatch tasks. Watch real execution. Clarify when needed.',
 '正在连接…':'Connecting…','执行器连接中':'Connecting to execution workers',
 '独立 PyBullet 世界':'Independent PyBullet worlds','只暂停正在提问的任务':'Only the asking robot is paused',
 '已评分任务 · 不含未完成任务':'Completed missions in this session','独立本机演示预算':'Separate interactive Dev budget',
 '创建独立任务':'Fresh world and history','装箱盖盒':'Pack and cover','双容器放置':'Two selected containers','三房间找物':'Three-room search',
 '自由演示 · 原场景':'Free Dev demonstration','全部已知':'All disclosed','一项未知':'One unknown','两项未知':'Two unknown','全部未知':'All unknown',
 '独立实验':'Independent Dev profile','位置记忆':'Public location memory','精简 Gate 输入':'Compact public Gate state',
 '真实模型 API':'Live model APIs','离线真实物理':'Offline policy / real physics','无 API':'No model API',
 '我来回答':'I will answer','启动任务':'Start Mission','自动三方法对比':'Compare Three Methods',
 'Human 模式只在模型真正 ASK 后显示回答表单；NoAsk 不会提问。右侧 Queue 处理待回答问题，任务卡可查看完整指令、对话和结束后的真值。':'Human replies appear only after an actual ASK. NoAsk never asks. Use the queue to answer, or open a mission for its instruction, conversation and final Ground Truth.',
 'Scripted 为规则策略，执行真实物理，不调用模型 API。':'Scripted policies execute real physics without model API calls.',
 '对比固定为自动回答 · 同一场景 · 3 个真实 API 任务':'Three live methods · Same Dev scene · Automatic replies',
 '显示已收起':'Show hidden missions','查看全部任务':'Show all missions',
 '选择任务后启动 Panda / Husky，或一键比较三种真实方法。':'Choose a task to start Panda or Husky, or compare the three live methods.',
 '每个画面来自独立执行器的实时全景。':'Every panoramic view comes from an independent physics worker.',
 '同一任务，三种澄清策略':'Same task. Three clarification policies.',
 '当前配对任务实测。API latency 为调用累计时间；wall time 包含排队与物理执行。各后端 token 分开统计。单个场景不代表正式 Benchmark 排名。':'This is one paired interactive Dev run. API latency is cumulative; wall time includes queueing and physics. Backend tokens are reported separately. This session is not a benchmark ranking.',
 '回答一个任务，其他机器人继续执行。':'Answer one robot while the others continue.',
 '尚无待回答的问题':'No pending questions','请选择任务查看当前回答模式与 Gate 状态。':'Select a mission to see its response mode and Gate status.',
 '问题与回答按 Task ID + Question ID 精确路由':'Each answer is routed by mission and question ID.',
 '关闭大画面':'Close expanded view','关闭 ×':'Close ×','放大的实时机器人全景':'Expanded live panoramic robot view','原始记录':'Original episode',
 '排队中':'Queued','初始化物理世界':'Initializing world','Gate 决策中':'Gate deciding',
 '生成澄清问题':'Planning question','ASK · 等待回答':'ASK · Awaiting answer','已收到回答':'Answer received',
 '规划下一步':'Planning next action','动作已发送':'Action dispatched','机器人执行中':'Robot executing',
 '独立物理评分中':'Physical evaluation','正在结束':'Stopping','已结束':'Stopped','执行完成':'Completed','执行 / API 错误':'Execution / API error',
 'Block bin / 方块分类箱':'Block bin','Block inventory / 方块目标库存':'Block inventory','Retrieve item / 取出物品':'Retrieval item',
 'Buffer pad / 临时缓冲区':'Buffer pad','Extra station / 额外巡检站':'Extra station','Inspection code / 检查标签':'Inspection code',
 'Knife location / 刀具位置':'Target location','Cup / 杯子':'Cup','Block / 方块':'Block','Lid / 盖子':'Lid','Cup destination / 目标容器':'Cup destination',
 ' · 公开状态 + 每轮重新规划] ':' · Public state + per-round replanning] ',
 'Scripted 是规则策略 · 真实物理 · 不调用模型 API。':'Scripted policy · Real physics · No model API.',
 'NoAsk 跳过 Gate · DeepSeek 根据公开信息生成动作。':'NoAsk skips Gate; DeepSeek plans from public information.',
 '真实 API 决策 · Human 仅在 Gate 发出 ASK 后显示输入。':'Live model decisions. Human input appears only after ASK.',
 '先点击“一键三方法对比”，创建同一场景的三个真实 API 任务。':'Choose Compare Three Methods to launch independent live runs on one Dev scene.',
 '结束任务':'Stop mission','等待执行器实时画面…':'Waiting for a real worker frame…','实时 PyBullet 机器人全景':'Live PyBullet panoramic robot view',
 '前往澄清队列 →':'Answer in queue →','指令 · 完整对话 · Ground Truth':'Instruction · Conversation · Ground Truth',
 '执行结束 · 任务未成功':'Completed · Task unsuccessful','物理场景已就绪':'Physical scene ready',
 '最终评分目标：':'Evaluated goal: ','Ground Truth：任务结束后揭示':'Ground Truth is revealed after termination',
 '收起':'Hide','结束':'Stop','执行器画面解码失败':'Could not decode worker frame',
 '并发上限 ':'Capacity ',' 排队中':' queued','请选择 / Select…':'Select…',
 '文字回答（填写后优先使用；也可留空使用候选选择）':'Type your answer, or select one candidate per requested slot.',
 '例如：菜刀在客厅柜子上':'Example: the target is on the living room cabinet',
 '例如：绿块、黑盖':'Example: green block, black lid','提交我的回答':'Submit Answer','自动回答本次':'Let Simulator Answer',
 '自动模拟器处理中…':'User Simulator is answering…','请输入回答，或为每项明确选择候选。':'Enter an answer or select a candidate for every slot.',
 '尚无待回答问题。':'No pending question.',
 'Scripted 规则策略；动作由真实 PyBullet 执行。':'Scripted public-only policy; actions execute in real PyBullet physics.',
 'NoAsk 跳过 Gate，直接调用共享 DeepSeek Planner。':'NoAsk skips Gate and uses the shared DeepSeek Planner.',
 '等待位置提示；真实目标不移动，物理世界保持静止。':'Waiting for a location hint. The fixed target and physics world do not move.',
 '正在等待偏好回答；当前世界保持静止。':'Waiting for a preference answer. This physics world is paused.',
 'Gate 基于公开指令、物理观察和历史决定是否需要澄清。':'The Gate uses the public instruction, observations and history to choose ASK or CONTINUE.',
 '初始任务指令 · 原文':'Initial Instruction · Verbatim',
 '本次任务由模板生成以上初始指令；Agent 只读取公开指令、观察和历史。':'The task template generated this instruction. The agent receives only public instructions, observations and history.',
 '公开对象 ID 与名称对照':'Public Object IDs and Names','公开 DAG · 任务前置条件':'Public Task DAG · Preconditions',
 '前往右侧队列回答 →':'Answer in the queue →','完整模型决策与用户对话':'Decisions and Conversation',
 '尚无决策或对话记录。':'No decision or conversation yet.','最终 Ground Truth / 评分目标':'Final Ground Truth / Evaluated Goal',
 '任务结束后才揭示隐藏真值；不会提前传给 Agent。':'Hidden truth is revealed only after termination; it is never supplied to the agent.',
 '偏好 / 事实':'Preference / Fact','预置隐藏参考':'Initial Hidden Reference','本次实际评分目标':'Evaluated Goal',
 '人工更新：':'Human preference update: ','独立物理评分':'Independent Physical Evaluation',
 'NEW TASKS · 六个新任务':'ADDITIONAL TASK TEMPLATES',
 '创建三个独立真实 API 任务，固定自动回答':'Launch three independent live-model runs with automatic replies',
 '需要开启 --live 且剩余至少三个 live episode 名额':'Requires live APIs and three remaining episode slots',
 '● 实时已连接':'● Connected','正在重连':'Reconnecting',
}

def translate(s):
    for a,b in sorted(translations.items(),key=lambda p:-len(p[0])):
        s=s.replace(a,b)
    assert not re.search(r'[\u4e00-\u9fff]',s), 'Untranslated display string remains'
    return s

html=translate((ROOT/'src/when2ask/console_web/index.html').read_text()).replace('lang="zh-CN"','lang="en"')
html=html.replace('<body>','<body><nav class="hub-nav" aria-label="Presentation navigation"><a class="hub-brand" href="#live">W<span>?</span> <b>When2Ask</b></a><div class="hub-links"><button data-view="live" aria-selected="true">Live Demo</button><button data-view="benchmark">Benchmark Results</button><button data-view="replay">Recorded Replay</button></div><div class="hub-actions"><button id="mission-controls" hidden>Mission Controls</button><button id="presentation-toggle" aria-pressed="false">Presentation View</button><button id="fullscreen" aria-label="Toggle full screen">Full Screen</button></div></nav><div id="live-page">')
html=html.replace('Gate Dev v7 · Compact public Gate state','Gate Dev v7 (recommended)')
html=html.replace('PHYSICAL TASK SCORE','SESSION OUTCOMES').replace('DAG PRESENTATION SCENARIO','DEV SCENARIO')
html=html.replace('</main>','</main>')
html=html.replace('<script src="/app.js"></script></body>', '</div><section id="benchmark-page" class="hub-page" hidden></section><section id="replay-page" class="hub-page" hidden></section><script src="/english.js"></script><script src="/app.js"></script><script src="/hub.js"></script></body>')
html=html.replace('</head>','<link rel="stylesheet" href="/hub.css"></head>')
html=html.replace('<section id="tasks"','<section id="mission-brief" class="panel" hidden></section><section id="tasks"')
(WEB/'index.html').write_text(html)
js=translate((ROOT/'src/when2ask/console_web/app.js').read_text())
js=js.replace('const value=await r.json();','const value=await r.json();if(url===\'/api/meta\')englishMetadata(value);')
js=js.replace('async function receive(t){','async function receive(t){t=englishTask(t);')
js=js.replace("throw Error(value.error||'HTTP '+r.status)","throw Error(englishError(value.error)||'HTTP '+r.status)")
js=js.replace("const all=[...tasks.values()],scored=all.filter", "const all=[...tasks.values()].filter(t=>!t.archived_readonly),scored=all.filter")
js=js.replace("c.hidden=archived.has(id)||!inGroup;", "const presentationHidden=document.body.classList.contains('presentation')&&(mode==='compare'?false:id!==selectedId);c.hidden=archived.has(id)||!inGroup||presentationHidden;")
js=js.replace("function renderInspector(){const t=tasks.get(selectedId);if(!t)return;", "function renderInspector(){const t=tasks.get(selectedId);if(!t)return;renderMissionBrief(t);")
js=js.replace("window.consoleView={tasks,groups,", "window.consoleView={tasks,groups,renderVisibility,renderInspector,")
js=js.replace("for(const [key,c]of views)c.classList.toggle('selected',key===id);renderInspector();}","for(const [key,c]of views)c.classList.toggle('selected',key===id);renderVisibility();renderInspector();}")
js=js.replace("saveDrafts();};textLabel.append","saveDrafts();answerError.textContent='';};textLabel.append")
js=js.replace("textInput.value=drafts.get(q.id)?._text||'';","textInput.placeholder=q.type==='confirm'?'Example: yes':'Example: '+q.requests.map(r=>q.candidates[r.candidate_ids?.[0]||r.candidate_id]).join(', ');textInput.value=drafts.get(q.id)?._text||'';")
js=js.replace("$('#task-count').textContent=tasks.size;","$('#task-count').textContent=document.body.classList.contains('presentation')?visible:tasks.size;")
js=js.replace("c.querySelector('h3').textContent=t.review?.scenario?.title||t.template_name;","c.querySelector('h3').textContent=t.comparison_id?methods[t.method]:(t.review?.scenario?.title||t.template_name);")
(WEB/'app.js').write_text(js)
(WEB/'style.css').write_text((ROOT/'src/when2ask/console_web/style.css').read_text())
print('Built independent English assets; preserved original frontend unchanged.')
