---
num: 3
slug: create-deep-agent-anatomy
title: create_deep_agent 全景解剖
module: W1
tier: A
minutes: 13
desc: 一次调用之后，你免费得到了哪些工具、哪些 middleware、哪些子图
lede: 这一课把 <code>create_deep_agent()</code> 当成一台机器拆开，逐件清点出厂配件。读完你应该能回答："我什么都没配，凭什么它就能读写文件、开子任务、压缩历史？"
source: https://docs.langchain.com/oss/python/deepagents/customization
source_title: Customize Deep Agents（官方）
---

## 最小调用

```python
from deepagents import create_deep_agent

agent = create_deep_agent(model="openai:gpt-5.5")
```

只有一个模型。但下面这些**已经全部就位**了。

## 出厂配件清单一：模型能看到的工具

harness 自动注入了一批"内建工具"。它们不是你的业务工具，而是 harness 自己的手：

| 工具 | 做什么 | 依赖 |
| - | - | - |
| `ls` | 列目录，带 size / modified time | 任意 backend |
| `read_file` | 读文件，带行号，支持 `offset` / `limit`；也支持图片返回多模态块 | 任意 backend |
| `write_file` | 新建或覆盖文件 | 任意 backend |
| `edit_file` | 精确字符串替换（支持全局替换模式） | 任意 backend |
| `delete` | 删文件，或递归删目录 | backend 支持才行 |
| `glob` | 按模式找文件，如 `**/*.py` | 任意 backend |
| `grep` | 搜内容，多种输出模式（只给文件名 / 带上下文 / 只给计数） | 任意 backend |
| `execute` | 跑 shell 命令 | **仅** sandbox 类 backend 才有 |
| `task` | 派生 subagent | 存在至少一个同步 subagent 时才有 |

!!! key "两个"凭空的"来源"
    `execute` 和 `task` 都是**条件注入**的：
    - `execute`：只有当 backend 实现了 sandbox 协议才出现。
    - `task`：只有当至少存在一个同步 subagent 时才出现（默认的 `general-purpose` 也算）。

    这解释了一个很常见的困惑：**"为什么我的 agent 明明有 execute 工具却报错？"**
    因为默认的 `StateBackend` 不支持执行命令——它只是一个存在图状态里的虚拟文件系统。

!!! trap "边际成本：每一个工具都要花 token"
    上面每个工具的名字、描述、参数 schema，都会在**每一次模型调用**里重复发送。
    工具越多，你在系统提示上的固定开销越大。
    这正是官方提供 `excluded_tools`（第 27 课）的原因：
    **不用把 `delete` 藏在 prompt 里让模型自己别用，直接从工具列表里拿掉，同时也省掉它的 schema。**

!!! warning "文件系统工具不能整个删掉"
    可以用 `excluded_tools` 把它们从**模型可见的工具列表**里隐藏，
    但**不能**通过 `excluded_middleware` 移除 `FilesystemMiddleware` 本身——
    它是 harness 的必需脚手架，写进 `excluded_middleware` 会直接 `ValueError`。

## 出厂配件清单二：middleware 栈

只有一个 `model` 的"裸栈"（bare stack），按顺序是：

<div class="stack">
  <div class="layer req"><span class="idx">1</span><span class="nm">FilesystemMiddleware</span><span class="ds">文件读写导航；传入 permissions 时，权限检查也在这里</span></div>
  <div class="layer req"><span class="idx">2</span><span class="nm">SubAgentMiddleware</span><span class="ds">自动加入的 general-purpose subagent 带来的；提供 task 工具</span></div>
  <div class="layer req"><span class="idx">3</span><span class="nm">SummarizationMiddleware</span><span class="ds">历史太长时压缩成摘要</span></div>
  <div class="layer req"><span class="idx">4</span><span class="nm">PatchToolCallsMiddleware</span><span class="ds">修补中断后残留的悬空 tool call</span></div>
  <div class="layer req"><span class="idx">5</span><span class="nm">Prompt caching middleware</span><span class="ds">Anthropic / Bedrock 各一个，总是注册，不适用的模型上自动 no-op</span></div>
</div>

注意第 2 条：**你什么都没配，却已经有一个 subagent 了。**
`create_deep_agent` 会自动添加一个名为 `general-purpose` 的同步 subagent，
除非你自己提供了一个同名的。这是很多人第一次读文档时会漏掉的一件事。

## 出厂配件清单三：默认 backend

不传 `backend=` 时，用的是 `StateBackend`：

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend

agent  = create_deep_agent(model="openai:gpt-5.5")
agent2 = create_deep_agent(model="openai:gpt-5.5", backend=StateBackend())  # 等价
```

它的语义是：**文件存在 LangGraph 的图状态里，作用域是 thread**。

| 特性 | StateBackend |
| - | - |
| 文件存在哪 | 图状态（state） |
| 跨 turn 保留吗 | 保留（靠 checkpointer 序列化） |
| 跨 thread 共享吗 | **不共享** |
| 支持 `execute` 吗 | 不支持 |
| 生命周期 | 跟着 thread 走 |

这意味着"agent 写的临时笔记"会随对话保存下来，但**换一个 `thread_id` 就全部消失**。
需要跨会话的东西（偏好、记忆、技能库）必须换 backend——那是第 07 课的内容。

## 出厂配件清单四：默认没有的东西

反过来同样重要。下面这些**不在**默认栈里：

| 能力 | 默认状态 | 怎么开 |
| - | - | - |
| 任务规划 `write_todos` | **不包含**（v0.7 起改为 opt-in） | 传 `TodoListMiddleware` |
| 长期记忆 | 不包含 | 传 `memory=[...]` |
| 技能 | 不包含 | 传 `skills=[...]` |
| 人工批准 | 不包含 | 传 `interrupt_on={...}` |
| 代码执行 | 不包含 | 换 sandbox backend |
| 结构化输出 | 不包含 | 传 `response_format=` |

!!! note "为什么 `write_todos` 从默认变成了 opt-in"
    官方给的理由很直接：它**不是对所有任务都有用**。
    对复杂多步任务、对能力较弱的模型（需要一个显式的问责工具）、
    以及需要把进度流式渲染到 UI 的场景有用；对简单任务纯粹是浪费 token 和一次模型调用。
    这是 harness 设计哲学的一个缩影：**默认装的东西必须是普适的，专用能力靠 opt-in。**

## 一次完整对照

把"你写的"和"框架替你做的"并排放：

```python
# 你写的 —— 就这么几行
agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[internet_search],          # 你的业务工具
    system_prompt="You are a research assistant.",
)

# 框架替你做的：
#   ├─ 注入 7 个文件系统工具
#   ├─ 装配 5 层 middleware（文件系统 / 子代理 / 摘要 / 修补 / 缓存）
#   ├─ 创建 StateBackend 作为虚拟文件系统
#   ├─ 添加 general-purpose subagent + task 工具
#   ├─ 拼装系统提示：你的 prompt + 内建 harness 指引 + 工具说明
#   └─ 编译成一张 LangGraph 图
```

最后一步值得单独强调：`create_deep_agent` 返回的是
`CompiledStateGraph`。它已经被 `.compile()` 过了——所以你的 agent 天生就是一个
**可被 checkpointer 持久化、可被 interrupt 打断、可被流式观测**的图。

```quiz
Q: 什么都不配置时，为什么 agent 已经有 task 工具了？
- FilesystemMiddleware 会顺带注册 task
- SummarizationMiddleware 需要 task 才能压缩
* 默认会自动添加一个 general-purpose 同步 subagent
- LangGraph 运行时默认给每个图都挂上 task
E: create_deep_agent 默认自动添加一个名为 general-purpose 的同步 subagent（除非你提供了同名的一个）。存在同步 subagent 时，SubAgentMiddleware 才会被装上，task 工具才会出现。

Q: 默认的 StateBackend 在跨 thread 这件事上的行为是？
- 所有 thread 共享同一份文件
- 文件随进程退出而立即消失
* 文件只在同一个 thread 内可见，换 thread 就没了
- 文件会写进本地磁盘的临时目录
E: StateBackend 把文件存在图状态里，按 thread 隔离，靠 checkpointer 在 turn 之间保留。要跨 thread 持久化必须换成 StoreBackend 之类的后端。

Q: 为什么 FilesystemMiddleware 不能被 excluded_middleware 移除？
- 因为它同时负责模型调用与工具执行
- 因为它由 LangGraph 运行时强制注入
* 因为它是 harness 的必需脚手架，移除会直接报错
- 因为它承载了 summarization 的全部逻辑
E: 官方明确说 FilesystemMiddleware 是 required scaffolding，列进 excluded_middleware 会 ValueError。要减少模型可见的工具，应该用 excluded_tools 或给 FilesystemMiddleware 传 tools 白名单。

Q: 关于 write_todos，下面哪个说法与官方一致？
- v0.7 起被默认包含进裸栈
- 它由 FilesystemMiddleware 自动提供
* v0.7 起改为 opt-in，需要显式传入中间件
- 它只在 sandbox 后端下才可用
E: 任务规划从 v0.7 起是 opt-in only，早期版本才默认包含。开启方式是给 middleware 参数传 TodoListMiddleware。
```

## 下一课

清点完了配件，接下来看**装配顺序**——为什么 `PatchToolCallsMiddleware` 必须在 prompt caching 之前，
为什么 `MemoryMiddleware` 被刻意放在最后。顺序不是随意的，每一条都有原因。
