---
num: 35
slug: deep-research-agent
title: 成品模式一：Deep Research Agent
module: W7
tier: B
minutes: 10
desc: 一个把 subagent、文件系统、压缩全用上的综合案例
lede: 官方给的第一个成品模式。它的价值不在于代码，而在于<b>你可以逐项指认出每个机制在这里扮演什么角色</b>——这是一次把前面 34 课串起来的练习。
source: https://docs.langchain.com/oss/python/deepagents/deep-research
source_title: Build a deep research agent（官方）
---

## 任务形状

"调研一个问题，写出一份报告。" 听起来简单，但它同时触发多个 harness 机制：

| 阶段 | 触发的机制 | 对应课程 |
| - | - | - |
| 拆解问题 | 任务规划 | 第 24 课 |
| 多路检索 | subagent 隔离 | 第 19 课 |
| 存放原始材料 | 虚拟文件系统 | 第 06 课 |
| 大搜索结果 | offloading | 第 15 课 |
| 汇总成报告 | 写文件 + 综合 | 第 06 课 |
| 长会话 | summarization | 第 15 课 |

**这是一个几乎每个机制都会被用到的任务形状**，所以官方把它放在最前面。

## 核心循环

官方在 quickstart 那一步给了同一类任务的工作流程描述。把它展开：

<div class="flow col">
  <div class="node"><span class="k">① 通过 internet_search 搜集</span><span class="v">工具调用</span></div>
  <div class="node"><span class="k">② 用文件系统管理上下文</span><span class="v">write_file / read_file 卸载大结果</span></div>
  <div class="node"><span class="k">③ 按需派生 subagent</span><span class="v">把复杂子任务委派出去</span></div>
  <div class="node hi"><span class="k">④ 综合成报告</span><span class="v">把发现整理成连贯回答</span></div>
</div>

!!! key "注意第 ② 步的措辞"
    官方写的是 "**Manages context** by using file system tools to **offload large search results**"。

    这说明即使在你**没有**显式配置任何东西的情况下，
    harness 也会引导 agent 去卸载大结果——因为内建的 offloading 机制
    和系统提示里的文件系统指引是配套的。

    **harness 不只是提供了工具，它还通过提示引导模型使用这些工具。**
    这是第 04 课"装配"的另一半：装配完还要让模型知道要用。

## 需要什么

| 项 | 说明 |
| - | - |
| 一个模型 | quickstart 用 `provider:model` 字符串或模型实例 |
| **一个搜索工具** | 这是唯一必须你自己提供的能力 |
| 可选：LangSmith tracing | 用来观察工具调用、subagent 委派、LLM 响应 |

!!! tip "搜索工具可以直接用 provider 的内建能力"
    官方在 quickstart 里指出：**Google、OpenAI、Anthropic 提供内建的 web search 工具，
    在服务端运行**——不需要额外包或 API key，直接把 provider 的工具 dict
    传给 `create_deep_agent` 就行。

    另一条路是用 Tavily 之类的第三方搜索（任何 provider 都能用）。

    **这个细节说明 harness 对"搜索"没有立场**：
    它只要求"有一个能拿外部信息的工具"，具体是谁提供的不关心。

## 加法：任务规划

官方在 quickstart 结尾建议：

> To add structured task planning with `write_todos`, opt in with `TodoListMiddleware`.

一个"调研 + 写报告"的任务，天然有多个阶段（搜集、整理、撰写、修订）。
加一个进度载体是合理的选择——而且前端还能直接渲染成进度列表（第 31 课）。

## 为什么这个模式适合作为第一个案例

<div class="compare">
<div class="yes">
<h4>它覆盖了核心机制</h4>
<ul>
<li>工具调用（搜索）</li>
<li>上下文管理（文件 + 卸载）</li>
<li>委派（subagent）</li>
<li>综合（写报告）</li>
</ul>
</div>
<div class="no">
<h4>它不需要额外基础设施</h4>
<ul>
<li>不需要沙箱（不跑代码）</li>
<li>不需要数据库（不建索引）</li>
<li>不需要长记忆（一次性任务）</li>
<li>不需要人工审批（无破坏性操作）</li>
</ul>
</div>
</div>

**这是"最小可演示 harness 价值"的任务形状。** 也正因如此，它是最适合用来
向你解释"harness 到底帮你干了什么"的例子。

## 一道自我检测

读完这一课，试着不看上文回答：

!!! note "如果不使用 harness，这个任务会怎么失败？"
    提示：想一想第 01 课的三个天花板。

    - **上下文**：一个主题搜索 20 次，每次返回几千 token，很快塞满窗口
    - **并行**：只能串行调研，任务时间线性增长
    - **记忆**：如果用户要求"接着上次的调研继续"，朴素 agent 做不到

    而这三条恰好对应 harness 的三个能力：卸载、隔离、长期记忆。

```quiz
Q: 官方描述的 deep research agent 工作流程里，"管理上下文"具体指什么？
- 限制搜索工具的返回条数
- 把搜索结果摘要后再展示给用户
* 用文件系统工具卸载大的搜索结果
- 为每个主题分配一个独立的模型
E: quickstart 的 How does it work 一节写明：通过使用文件系统工具（write_file、read_file）卸载大的搜索结果来管理上下文。

Q: 构建 deep research agent 时，唯一必须由你提供的能力是什么？
- 一个向量数据库
- 一个沙箱环境
* 一个能获取外部信息的搜索工具
- 一个自定义的 state schema
E: harness 提供了文件系统、子代理、压缩等能力，但外部信息必须由一个工具提供。官方给出两条路：provider 内建的 server-side web search，或 Tavily 等第三方搜索。

Q: 这个模式为什么被官方放在第一个案例？
- 因为它的代码最短
- 因为它不需要模型
* 因为它覆盖核心机制且不需要额外基础设施
- 因为它演示了沙箱与解释器的组合
E: 它同时用到工具调用、上下文卸载、subagent 委派与综合，但不依赖沙箱、向量库、长期记忆或人工审批，因此是演示 harness 价值的最小完整形状。
```

## 下一课

第二个成品模式会引入一个新东西：**沙箱与文件上传**。
数据分析 agent 需要真的跑代码，这改变了整个架构。
