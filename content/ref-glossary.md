---
kind: reference
sort: 1
slug: glossary
title: 术语表
lede: 全课程统一使用的术语。每节课都遵守这里的译法与定义；遇到不熟的词先回来查这里。
desc: Deep Agents 与 agent harness 的核心术语
---

## 怎么读这张表

- **中文（English Term）** 是统一叫法，课程里首次出现时用完整形式，之后可只用英文。
- 官方文档里没有正式名称、但课程里反复用到的概念，标注为「本课程用语」。
- 每条都给了出处，方便你去原文核对。

## 架构层次

<dl class="glossary">
<dt>挽具 / 外壳 <span class="en">harness</span></dt>
<dd>套在同一个 tool-calling 循环外面的能力层。Deep Agents 是 agent harness。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/concepts/products">Concepts · Frameworks, runtimes, and harnesses</a>；第 01 课</span></dd>

<dt>运行时 <span class="en">runtime</span></dt>
<dd>图的执行引擎。在 Deep Agents 语境里指 LangGraph，负责持久化、中断、流式、durable execution。
<span class="src">出处：同上一行；第 02 课</span></dd>

<dt>中间件栈 <span class="en">middleware stack</span></dt>
<dd><code>create_deep_agent</code> 按固定顺序装配的 middleware 列表。顺序由「谁变化、谁稳定」决定，直接影响 prompt 缓存命中率。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/customization#deep-agents-stack">Customize · Deep Agents stack</a>；第 04 课</span></dd>

<dt>裸栈 <span class="en">bare stack</span></dt>
<dd>只传 <code>model</code> 时得到的栈：FilesystemMiddleware、SubAgentMiddleware、SummarizationMiddleware、PatchToolCallsMiddleware、prompt caching。
<span class="src">出处：同上；第 03 课</span></dd>

<dt>必需脚手架 <span class="en">required scaffolding</span></dt>
<dd>不可通过 <code>excluded_middleware</code> 移除的 middleware：<code>FilesystemMiddleware</code>、<code>SubAgentMiddleware</code>、内部权限 middleware。列出会抛 <code>ValueError</code>。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/profiles">Profiles</a>；第 27 课</span></dd>
</dl>

## 执行环境

<dl class="glossary">
<dt>虚拟文件系统 <span class="en">virtual filesystem</span></dt>
<dd>harness 提供给 agent 的文件抽象。八个工具：<code>ls</code>、<code>read_file</code>、<code>write_file</code>、<code>edit_file</code>、<code>delete</code>、<code>glob</code>、<code>grep</code>，沙箱下额外有 <code>execute</code>。是 offloading、skills、memory、代码执行的共同底座。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/overview#virtual-filesystem-access">Overview · Virtual filesystem access</a>；第 06 课</span></dd>

<dt>后端 <span class="en">backend</span></dt>
<dd>虚拟文件系统的可插拔实现。决定文件存哪、作用域多大、能否执行命令。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/backends">Backends</a>；第 07 课</span></dd>

<dt>状态后端 <span class="en">StateBackend</span></dt>
<dd>默认 backend。文件存在 LangGraph 图状态里，thread 作用域，支持跨 turn 不跨 thread，不支持 <code>execute</code>。</dd>

<dt>存储后端 <span class="en">StoreBackend</span></dt>
<dd>建在 LangGraph store 上，<b>跨 thread 持久化</b>。行为由 <code>namespace</code> 决定（放 user_id / assistant_id / thread_id）。</dd>

<dt>组合后端 <span class="en">CompositeBackend</span></dt>
<dd>按路径前缀路由到不同 backend。<b>路径前缀就是路由规则</b>。<code>default=</code> 接住未匹配的路径。</dd>

<dt>命名空间 <span class="en">namespace</span></dt>
<dd>① <code>StoreBackend(namespace=lambda rt: (...))</code>：决定记忆/文件的作用域。② 流式里的 namespace：标识事件来自委派树的哪个位置。两处含义相关但不同。
<span class="src">第 07、14、28 课</span></dd>

<dt>沙箱 <span class="en">sandbox</span></dt>
<dd><b>一类 backend</b>，额外提供 <code>execute</code> 工具与隔离边界。权限规则对它不生效。生命周期通常是 thread 级或 assistant 级。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/sandboxes">Sandboxes</a>；第 09 课</span></dd>

<dt>模型平面 / 控制平面 <span class="en">model plane / control plane</span></dt>
<dd>本课程用来区分文件访问的两条路：模型平面 = agent 通过工具操作；控制平面 = 宿主程序用 provider SDK 上传下载（播种与取回产物）。
<span class="src">依据 <a href="https://docs.langchain.com/oss/python/deepagents/sandboxes#two-planes-of-file-access">Sandboxes · Two planes of file access</a>；第 09、33、36 课</span></dd>

<dt>解释器 <span class="en">interpreter</span></dt>
<dd>作用域受限的内存内 QuickJS 运行时，提供 <code>eval</code> 工具。无 shell、无包安装、无文件系统、无网络。用于组合工具与保留状态，与沙箱分工不同。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/interpreters">Interpreters</a>；第 10 课</span></dd>

<dt>程序化工具调用 <span class="en">programmatic tool calling (PTC)</span></dt>
<dd>允许解释器里的代码调用选定工具。默认关闭，需显式允许列表。中间结果留在解释器内存，不进模型上下文。
<span class="src">出处：同上；第 10 课</span></dd>

<dt>文件系统权限 <span class="en">filesystem permissions</span></dt>
<dd>声明式规则表，三字段：<code>operations</code>、<code>paths</code>、<code>mode</code>。<b>首匹配胜出；无匹配则允许。</b>不适用于沙箱。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/permissions">Permissions</a>；第 08 课</span></dd>
</dl>

## 上下文工程

<dl class="glossary">
<dt>输入上下文 <span class="en">input context</span></dt>
<dd>启动时进入 system prompt 的内容：system prompt、memory、skills、tool prompts。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/context-engineering">Context engineering</a>；第 11、12 课</span></dd>

<dt>运行时上下文 <span class="en">runtime context</span></dt>
<dd>每次调用传入的<b>不可变</b>配置（用户元数据、凭据、feature flag）。通过 <code>context_schema</code> 定义，<code>runtime.context</code> 读取，<b>会传播到 subagent</b>。
<span class="src">第 17 课</span></dd>

<dt>卸载 <span class="en">offloading</span></dt>
<dd>把超过 <b>20,000 token</b> 的工具输入/结果写进文件系统，上下文中替换为文件路径引用 + 前 10 行预览。无损，可读回。
<span class="src">第 15 课</span></dd>

<dt>摘要 <span class="en">summarization</span></dt>
<dd>上下文达到模型窗口约 <b>85%</b> 且无可卸载内容时，用 LLM 生成结构化摘要替换历史，保留 10% token 作为最近上下文；同时把原始消息文本渲染进文件系统。兜底值 170,000 token / 保留 6 条消息。
<span class="src">第 15 课</span></dd>

<dt>上下文隔离 <span class="en">context isolation</span></dt>
<dd>用 subagent 把重活放到独立窗口执行，只带回最终结果。术语来源 <span class="en">context quarantine</span>。
<span class="src">出处：<a href="https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html#context-quarantine">Drew Breunig</a>；第 19 课</span></dd>

<dt>技能 <span class="en">skill</span></dt>
<dd>一个含 <code>SKILL.md</code> 的目录（可选 <code>scripts/</code>、<code>references/</code>、<code>assets/</code>）。启动只读 frontmatter 的 <code>name</code> 与 <code>description</code>，正文按需 <code>read_file</code>。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/skills">Skills</a>、<a href="https://agentskills.io/">Agent Skills 标准</a>；第 13 课</span></dd>

<dt>渐进式披露 <span class="en">progressive disclosure</span></dt>
<dd>技能的加载策略：启动只加载摘要，需要时才读正文，正文里提到别的文件再按需读。<b>匹配质量完全压在 <code>description</code> 上。</b>
<span class="src">第 13 课</span></dd>

<dt>记忆 <span class="en">memory</span></dt>
<dd><code>AGENTS.md</code> 文件，通过 <code>memory=</code> 传入，<b>总是加载</b>。与 skills 相对：memory 用 token 换"不会忘"，skills 用"可能多读一次文件"换"不用时不花钱"。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/memory">Memory</a>、<a href="https://agents.md/">AGENTS.md</a>；第 14 课</span></dd>

<dt>情景记忆 <span class="en">episodic memory</span></dt>
<dd>过去发生过什么、顺序如何、结果怎样。由 <b>checkpointer</b> 持久化的 thread 历史支撑；要可检索需包成工具。
<span class="src">第 14 课</span></dd>

<dt>后台整合 <span class="en">background consolidation / sleep time compute</span></dt>
<dd>在对话之间由另一个整合 agent 抽取关键事实并合并进记忆 store，通常由 cron 触发。<b>整合频率不应远高于用户对话频率。</b>
<span class="src">第 14 课</span></dd>

<dt>提示缓存 <span class="en">prompt caching</span></dt>
<dd>对系统提示的静态前缀做缓存。Anthropic 与 Bedrock 模型上默认开启。它是 middleware 排序的直接原因：稳定的靠前，易变的靠后。
<span class="src">第 04、16 课</span></dd>

<dt>自定义状态 <span class="en">custom state schema</span></dt>
<dd>必须继承 <code>DeepAgentState</code>（以保留 <code>messages</code> 上的 <code>DeltaChannel</code> reducer，保证 checkpoint 线性增长）。声明式 subagent 继承，CompiledSubAgent 与 AsyncSubAgent 不继承。
<span class="src">第 17 课</span></dd>

<dt>增量通道 <span class="en">DeltaChannel</span></dt>
<dd><code>messages</code> 上的内建 reducer，让 checkpoint 增长随对话长度保持线性。
<span class="src">第 17 课</span></dd>
</dl>

## 委派

<dl class="glossary">
<dt>子代理 <span class="en">subagent</span></dt>
<dd>处理隔离子任务的临时子 agent。有全新上下文、自主执行、单次交接、无状态消息四条语义。由 <code>task</code> 工具触发。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/subagents">Subagents</a>；第 19 课</span></dd>

<dt>单次交接 <span class="en">single handoff</span></dt>
<dd>subagent 只向父 agent 返回一份最终报告，不能发多条消息。这是控制父窗口膨胀的关键约束。
<span class="src">第 19 课</span></dd>

<dt>隔离模式 / 派生模式 <span class="en">isolated / fork</span></dt>
<dd>subagent 的 <code>mode</code>。<code>isolated</code>（默认）只看到被派发的任务，必须自带 system_prompt；<code>fork</code> 继承父级的对话与系统提示。
<span class="src">第 20、21 课</span></dd>

<dt>通用子代理 <span class="en">general-purpose subagent</span></dt>
<dd>默认自动添加的同步 subagent（除非你提供同名的一个）。它是 <code>SubAgentMiddleware</code> 与 <code>task</code> 工具出现的原因。<b>只有它继承主 agent 的 skills。</b>关闭方式：<code>GeneralPurposeSubagentProfile(enabled=False)</code> 且不传同步 subagents。
<span class="src">第 19 课</span></dd>

<dt>动态子代理 <span class="en">dynamic subagents</span></dt>
<dd>从解释器代码里用内建 <code>task()</code> 全局函数派发 subagent。让编排变成确定性的循环而非逐次模型决策。参数：<code>description</code>、<code>subagentType</code>、<code>responseSchema</code>。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/dynamic-subagents">Dynamic subagents</a>；第 22 课</span></dd>

<dt>异步子代理 <span class="en">async subagents</span></dt>
<dd>跨请求长跑、可中途操纵与取消的委派。需要选择 transport（ASGI 同部署 / HTTP 远程）与部署拓扑（single / split / hybrid）。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/async-subagents">Async subagents</a>；第 23 课</span></dd>

<dt>递归语言模型 <span class="en">recursive language model (RLM)</span></dt>
<dd>把工作集保留在解释器变量里、选择切片、用 <code>task()</code> 调用 subagent、在代码里合成结果的工作流。
<span class="src">出处：<a href="https://arxiv.org/abs/2512.24601">Recursive Language Models</a>；第 22 课</span></dd>

<dt>待办列表 <span class="en">write_todos / TodoListMiddleware</span></dt>
<dd>opt-in 的任务规划。<b>从 v0.7 起不再默认包含。</b>状态：<code>pending</code> / <code>in_progress</code> / <code>completed</code>，存在 agent state 里，可被流式渲染。
<span class="src">第 24 课</span></dd>
</dl>

## 运行时管控

<dl class="glossary">
<dt>人在回路 <span class="en">human-in-the-loop (HITL)</span></dt>
<dd>通过 <code>interrupt_on</code> 在工具调用前暂停。<b>必须有 checkpointer，恢复时 thread_id 必须一致。</b>四种决策：approve / edit / reject / respond。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/human-in-the-loop">Human-in-the-loop</a>；第 25 课</span></dd>

<dt>补丁工具调用 <span class="en">PatchToolCallsMiddleware</span></dt>
<dd>修复中断或畸形参数留下的悬空 tool call。排在栈的第 4 位——必须在摘要、缓存、记忆之前把历史修干净。
<span class="src">第 04 课</span></dd>

<dt>评价量表 <span class="en">grading rubric</span></dt>
<dd><code>RubricMiddleware</code>，用独立模型按标准评判产出并在 <code>max_iterations</code> 内迭代到达标。适合验收标准可被明确陈述的产出（如可执行代码）。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/rubric">Grading rubrics</a>；第 38 课</span></dd>

<dt>配置文件 <span class="en">harness profile</span></dt>
<dd>按 provider 或 model 注册的 harness 调整：<code>base_system_prompt</code>、<code>system_prompt_suffix</code>、<code>tool_description_overrides</code>、<code>excluded_tools</code>、<code>excluded_middleware</code>、<code>extra_middleware</code>、<code>general_purpose_subagent</code>。重复注册是<b>合并</b>而非替换，合并规则按字段不同。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/profiles">Profiles</a>；第 27 课</span></dd>

<dt>供应商配置文件 <span class="en">provider profile</span></dt>
<dd>只影响模型<b>构造</b>（temperature、timeout 等），不影响 harness。官方认为大多数调用者不需要它。
<span class="src">第 27 课</span></dd>
</dl>

## 流式与前端

<dl class="glossary">
<dt>子图流式 <span class="en">subgraph streaming</span></dt>
<dd><code>agent.stream(..., subgraphs=True)</code>。开启后 chunk 形状变为 <code>(namespace, data)</code>；多 mode 时为 <code>(namespace, mode, data)</code>。
<span class="src">第 28 课</span></dd>

<dt>子代理投影 <span class="en">stream.subagents</span></dt>
<dd>Deep Agents 在 LangGraph 流式之上加的一层：每次被委派的 <code>task</code> 调用一个句柄。<b>惰性打开</b>——只有访问消息等投影时才真正订阅。字段：<code>name</code>、<code>messages</code>、<code>subagents</code>、<code>output</code>、<code>path</code>、<code>status</code>、<code>tool_calls</code>。入口是 <code>stream_events(..., version="v3")</code>。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/event-streaming">Event streaming</a>；第 29 课</span></dd>

<dt>发现快照 <span class="en">SubagentDiscoverySnapshot</span></dt>
<dd><b>轻量发现记录</b>：告诉你某个 subagent 存在、在委派树的哪个位置、处于什么生命周期状态。<b>不含</b>消息与工具调用内容——那些要通过 selector hook 按需订阅。
<span class="src">第 32 课</span></dd>

<dt>协调者—工作者 <span class="en">coordinator-worker</span></dt>
<dd>Deep Agents 的架构模式：主 agent 规划与委派，专门 subagent 隔离执行。前端对应"根流 + subagent 发现快照 + 作用域视图"。
<span class="src">第 30 课</span></dd>

<dt>编辑器协议 <span class="en">ACP · Agent Client Protocol</span></dt>
<dd>把 agent 接入编辑器（Zed、Toad 等）的协议。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/acp">ACP</a>、<a href="https://agentclientprotocol.com/">agentclientprotocol.com</a>；第 40 课</span></dd>

<dt>界面协议 <span class="en">AG-UI</span></dt>
<dd>把 agent 事件流交给前端的协议。含事件流、前端连接、Programmatic API 三部分。
<span class="src">出处：<a href="https://docs.langchain.com/oss/python/deepagents/ag-ui">AG-UI</a>；第 40 课</span></dd>

<dt>模型上下文协议 <span class="en">MCP · Model Context Protocol</span></dt>
<dd>把外部服务的能力以标准接口暴露给 agent。解决 M×N 集成问题（降为 M+N），但不改善工具描述质量、不降低 token 成本、不提供审批。
<span class="src">出处：<a href="https://modelcontextprotocol.io/">modelcontextprotocol.io</a>；第 05 课</span></dd>
</dl>
