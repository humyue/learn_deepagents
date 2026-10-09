---
num: 1
slug: agent-harness-mental-model
title: Agent Harness 的心智模型
module: W1
tier: A
minutes: 11
desc: 朴素 tool-calling 循环的三个天花板，以及 harness 为什么必须存在
lede: Deep Agents 不是"又一个 agent 框架"。它是一个 <b>harness</b>——套在同一个 tool-calling 循环外面的一层 middleware 外壳。这一课要做的，是让你在读完后面 39 课之前，先拿到一张正确的地图。
source: https://docs.langchain.com/oss/python/deepagents/overview
source_title: Deep Agents overview（官方）
---

## 先看没有 harness 的时候

一个"普通"的 LLM agent，本质就是一个循环。用 LangChain 的 `create_agent` 写出来是这样：

```python
from langchain.agents import create_agent

agent = create_agent(
    model="openai:gpt-5.5",
    tools=[search, fetch_url],
    system_prompt="You are a research assistant.",
)
```

它的运行时行为可以用一张图说完：

<div class="flow">
  <div class="node"><span class="k">用户消息</span><span class="v">messages</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">调用模型</span><span class="v">LLM</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">有 tool_call？</span><span class="v">是 → 执行工具</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">工具结果回填</span><span class="v">ToolMessage</span></div>
  <div class="arrow">↺</div>
  <div class="node dim"><span class="k">没有 tool_call</span><span class="v">返回最终答案</span></div>
</div>

这个循环本身没有任何问题。**问题在于它没有边界**。

## 朴素循环的三个天花板

官方文档把 Deep Agents 的能力归到几个方向上，但如果你把它们翻译成"朴素循环会怎么死"，会更容易记住：

| 天花板 | 朴素循环的表现 | Harness 的应对 |
| - | - | - |
| **上下文会满** | 一次搜索返回 200KB，几次之后窗口爆掉，任务中断 | 把大结果卸载到文件系统，只留路径和预览 |
| **只能想一件事** | 一个线程一条思路，无法并行探索多个方向 | 派生 subagent，用隔离的上下文窗口干活 |
| **关掉就忘** | 进程重启，学到的东西全部消失 | `AGENTS.md` 记忆文件，存在 backend 里 |
| **不能动手** | 只能调用你预先写好的那几个函数 | 虚拟文件系统 + 沙箱 + 解释器 |
| **不可控** | 删库、发邮件、花钱，全都自动执行 | `interrupt_on` 中断 + `permissions` 声明式权限 |

其中前三条是**能力**问题，后两条是**信任**问题。Deep Agents 的官方定位很清楚：

!!! note "官方原话"
    Deep Agents is an ["agent harness"](https://docs.langchain.com/oss/python/concepts/products#agent-harnesses-like-the-deep-agents-sdk).
    It is the same core tool calling loop as other agent frameworks, but with built-in capabilities
    that make agents reliable for real tasks.

    —— 注意 *the same core tool calling loop*。它没有换掉循环，只是在循环外面加了东西。

## Harness 的干预点：middleware

"在循环外面加东西"的具体机制，是 LangChain 的 middleware。middleware 是一组钩子，
可以在模型调用前后、工具调用前后插入逻辑：

<div class="flow col">
  <div class="node dim"><span class="k">Runtime</span><span class="v">LangGraph 负责循环、状态、持久化</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">Middleware 栈</span><span class="v">在每次模型调用 / 工具调用前后改写请求与结果</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">模型 + 工具</span><span class="v">真正干活的两位</span></div>
  <div class="arrow">↓</div>
  <div class="node dim"><span class="k">Backend（虚拟文件系统）</span><span class="v">middleware 用来临时寄存东西的地方</span></div>
</div>

所以你写的代码几乎没变：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[internet_search],
    system_prompt="You are a research assistant.",
)
```

但这一行 `create_deep_agent` 背后，已经替你装配好了一整套 middleware。
这个装配顺序就是**第 04 课**的主题——它是理解整个 harness 的关键。

!!! tip "本课要带走的一句话"
    **Deep Agents = 普通 agent 循环 + 一个预装的 middleware 栈 + 一个虚拟文件系统。**
    后面所有能力（上下文压缩、subagent、记忆、技能、代码执行）都是这三样东西的组合结果，
    没有一样是独立的新机制。

## `create_deep_agent` 的全部旋钮

先把完整的函数签名看一遍。不需要记住，只需要知道**旋钮被分成了哪几类**：

```python
create_deep_agent(
    model,                      # 用哪个模型
    tools,                      # 领域工具（你的业务逻辑）
    *,
    system_prompt,              # 静态系统提示
    middleware,                 # 额外 middleware，合并进默认栈
    subagents,                  # 自定义 / 异步 subagent
    skills,                     # 技能目录（按需加载的知识）
    memory,                     # AGENTS.md 路径（启动即加载）
    permissions,                # 声明式文件权限
    backend,                    # 虚拟文件系统后端
    interrupt_on,               # 哪些工具需要人工批准
    response_format,            # 结构化输出 schema
    state_schema,               # 自定义图状态
    context_schema,             # 单次调用的运行时上下文
    checkpointer, store,        # 短期 / 长期持久化
    debug, name, cache,
)
```

把它按类别归一下，课程结构立刻就清楚了：

<div class="flow">
  <div class="node"><span class="k">执行环境</span><span class="v">tools · backend · permissions</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">上下文</span><span class="v">system_prompt · memory · skills</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">委派</span><span class="v">subagents</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">管控</span><span class="v">interrupt_on · middleware</span></div>
</div>

> 这四类正好对应模块 B / C / D / E。也就是说，**这门课的结构就是 `create_deep_agent` 的参数表。**

!!! warning "一个容易误解的地方"
    harness 不是"更聪明的模型"。它不会让模型推理得更好。
    它做的事是**把模型从它不擅长的杂活里解放出来**：记住事情、压缩历史、搬运大文件、管权限。
    模型的智力上限没变，能完成的任务复杂度变了。

```quiz
Q: 官方对 Deep Agents 的定义里，最关键的限定词是什么？
- 一种全新设计的 agent 推理循环
* 同一个核心 tool calling loop，外加内建能力
- 一个用于训练 agent 模型的开源框架
- 一套替代 LangGraph 的图执行引擎
E: 官方原文写的是 "It is the same core tool calling loop as other agent frameworks, but with built-in capabilities"。循环本身没有被替换，harness 的价值全部来自循环之外的那层外壳。

Q: `backend=` 这个参数最接近下面哪一类作用？
- 指定调用哪个模型提供商
- 定义 agent 的系统提示词
* 决定虚拟文件系统把文件存在哪里
- 配置哪些工具需要人工批准
E: backend 是虚拟文件系统的可插拔实现：StateBackend 存在图状态里、StoreBackend 跨 thread 持久化、FilesystemBackend 落到本地磁盘、Sandbox 落到隔离环境。它是模块 B 的主角。

Q: 下面哪一项**不是** harness 试图解决的问题？
- 上下文窗口被大工具结果撑爆
* 模型在数学题上算错答案
- 单个线程无法并行推进多条探索路线
- 进程重启后 agent 忘掉之前学到的偏好
E: harness 管理的是上下文、并发、记忆、权限这些"工程边界"问题。模型自身的推理正确率不在它的职责范围内——它既不能也不会去修正模型的数学能力。

Q: 如果把 harness 的全部能力归纳成一个比喻，哪个最贴切？
- 给汽车换一台更强力的发动机
* 给汽车装上空调、安全带和自动驾驶辅助
- 把汽车从燃油改成纯电动
- 把汽车拆成零件重新造一辆
E: 发动机（模型）没变，改的是外围：让长途驾驶可行（上下文管理）、可以载客（并行 subagent）、出事有保护（权限与中断）。这正是 "harness"（挽具/外壳）这个词的字面含义。
```

## 下一课

知道了"它是什么"，下一步是搞清楚它**站在哪一层**——
LangChain、LangGraph、Deep Agents 三者的分工，是官方文档里最容易读混的一段。
