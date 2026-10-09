---
num: 19
slug: subagents-fundamentals
title: Subagent 原理
module: W4
tier: A
minutes: 14
desc: task 工具、上下文隔离、单次交接 —— context quarantine 的实现
lede: 如果只允许用一个机制来解释"为什么 Deep Agents 比裸 agent 强"，那就是 subagent。它做的事情听起来平淡无奇：开一个子任务、拿回一个结果。但它顺手解决了 agent 架构里最贵的那个问题。
source: https://docs.langchain.com/oss/python/deepagents/subagents
source_title: Subagents（官方）
---

## 它解决的问题：上下文膨胀

官方把动机写得很直白：

!!! note "官方原话"
    Subagents solve the **context bloat problem**. When agents use tools with large outputs
    (web search, file reads, database queries), the context window fills up quickly with
    intermediate results. Subagents isolate this detailed work—the main agent receives
    only the final result, not the dozens of tool calls that produced it.

    关键词是 **only the final result, not the dozens of tool calls**。

## 对比：不用 subagent vs 用 subagent

假设任务是"调研三个主题，然后写一份综合报告"。

不用 subagent：

<div class="flow col">
  <div class="node"><span class="k">主 agent</span><span class="v">搜索主题 A（12 次搜索）</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">主 agent</span><span class="v">搜索主题 B（15 次搜索）</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">主 agent</span><span class="v">搜索主题 C（18 次搜索）</span></div>
  <div class="arrow">↓</div>
  <div class="node dim"><span class="k">主 agent</span><span class="v">45 次搜索结果全部在窗口里，还要写报告</span></div>
</div>

用 subagent：

<div class="flow">
  <div class="node hi"><span class="k">主 agent</span><span class="v">只看到 3 份结论摘要</span></div>
</div>
<div class="flow">
  <div class="node"><span class="k">subagent A</span><span class="v">12 次搜索（自己的窗口）→ 摘要</span></div>
  <div class="arrow">↗</div>
  <div class="node"><span class="k">subagent B</span><span class="v">15 次搜索（自己的窗口）→ 摘要</span></div>
  <div class="arrow">↗</div>
  <div class="node"><span class="k">subagent C</span><span class="v">18 次搜索（自己的窗口）→ 摘要</span></div>
</div>

!!! key "这就是 context quarantine"
    官方正文里给出的术语来源是 Drew Breunig 的文章
    [How to fix your context](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html#context-quarantine)。
    **隔离**：把产生大量噪音的工作，放进一个独立的上下文窗口里做，
    只把干净的产出带回主窗口。

    注意它不是"压缩"——**它压根没让那些噪音进入主窗口**。
    这是它比 summarization 更彻底的地方：摘要是有损压缩已存在的噪音，
    隔离是**从一开始就不产生噪音**。

## 五个设计约束

官方用五个特征描述了 subagent 的运行语义。每一条都有设计理由：

| 特征 | 含义 | 为什么这样设计 |
| - | - | - |
| **Fresh context** | 每次调用创建全新 agent 实例，有自己的上下文 | 隔离的前提；也避免了状态污染 |
| **Autonomous execution** | 独立运行到完成，中途父 agent 不干预 | 同步模式下父 agent 只需等待 |
| **Single handoff** | 只返回一份最终报告给主 agent | 控制父窗口的膨胀 |
| **Stateless messaging** | subagent **无状态**，不能发多条消息回来 | 强制"一次交接"，防止变成闲聊 |
| **Token efficiency** | 重活留在隔离区，压成紧凑结果 | 这就是全部收益 |

!!! warning "无状态这一点经常被误解"
    "Stateless" 意味着**父 agent 不能在 subagent 干活时反复给它追加指示**。
    这在同步 subagent 上是个硬约束。

    如果你确实需要"长跑 + 中途可操纵"，那**不是**这个机制能解决的——
    官方把它指向 [Async subagents](https://docs.langchain.com/oss/python/deepagents/async-subagents)（第 23 课）。

## 默认就有一个

`create_deep_agent` 会自动添加一个名为 **`general-purpose`** 的同步 subagent，
除非你自己提供了一个同名的（那就替换掉它）。

它自带文件系统工具，可以通过 `tools` / `middleware` 定制。
作用：**主 agent 有一个"什么活都能接的通用帮手"**，不需要你先定义专门的 subagent 就能体验隔离。

三种操作方式：

| 想做什么 | 怎么做 |
| - | - |
| 替换它 | 传一个自己定义的、名字叫 `general-purpose` 的 subagent |
| 改名 / 改提示 | 在 harness profile 上设 `general_purpose_subagent=GeneralPurposeSubagentProfile(...)` |
| 禁用它 | 见下 |

## 怎么完全去掉委派能力

官方给了**必须两步**的做法：

1. 在 harness profile 上设 `general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)`
2. 通过 `subagents=` 传入**空的**同步 subagent 列表

只有当**至少存在一个同步 subagent** 时，`SubAgentMiddleware`（和 `task` 工具）才会被装上。
两者都满足，agent 就真的没有委派能力了。

!!! trap "不要去 excluded_middleware 里删 SubAgentMiddleware"
    官方明确警告：**这是必需脚手架，列进去会抛 `ValueError`。**
    正确的旋钮是 `general_purpose_subagent.enabled = False`。

    另外注意：**异步 subagent 不受影响**——它们走自己的 middleware 与工具。

## 什么时候**不**该用 subagent

官方给的反面清单同样重要：

| 不该用 | 原因 |
| - | - |
| 简单的单步任务 | 开销（一次完整的子 agent 运行）大于收益 |
| 你需要保留中间上下文时 | subagent 只带回结论，中间过程父 agent 看不到 |
| 开销大于收益时 | 尤其当子任务本身只有一两次工具调用 |

!!! tip "一条经验判据"
    问自己：**这个子任务产生的中间噪音，比它的结论大多少倍？**
    - 比例很高（20 次搜索 → 1 页结论）→ 值得隔离
    - 比例接近 1（1 次查询 → 1 条结果）→ 不值得

## 和"压缩"的配合

这两个机制不是二选一，而是分工：

<div class="flow">
  <div class="node"><span class="k">能外派的活</span><span class="v">→ subagent 隔离（不产生噪音）</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">必须自己做的活</span><span class="v">→ offloading + summarization（产生后压缩）</span></div>
</div>

一个成熟的 agent 提示词通常两条都写：
"把独立的调研任务交给 subagent；把大结果写进文件，只把关键结论留在对话里。"

```quiz
Q: subagent 解决的核心问题是什么？
- 让模型可以并行使用多个不同的模型
- 让 agent 可以突破上下文窗口的硬上限
* 把产生大量中间结果的工作隔离在独立窗口里
- 让工具调用可以被人工审批拦截
E: 官方说法是 subagents solve the context bloat problem。重活留在隔离区，主 agent 只收到最终结果，而不是产生它的几十次工具调用。

Q: subagent 与 summarization 在"处理噪音"上的根本差别是？
- 一个由模型触发，一个由 token 阈值触发
- 一个在文件系统里做，一个在内存里做
* 一个从一开始就不让噪音进入主窗口，一个是事后压缩已存在的噪音
- 一个只对工具结果生效，一个只对消息历史生效
E: 隔离是"噪音不产生在主窗口"；摘要是"噪音已经产生后再有损压缩"。前者更彻底，但只适用于可以外派的工作。

Q: 关于 subagent 的 "stateless messaging"，正确的理解是？
- subagent 之间不能共享文件系统
- subagent 不能调用任何工具
* 它只做单次交接，父 agent 无法中途追加多条指示
- 它不能被多次调用，每次运行都是全新的
E: 官方把它列为一条特征：subagents are stateless and cannot send multiple messages back，配合 single handoff 控制父窗口膨胀。需要中途操纵应改用 async subagents。

Q: 要移除 task 工具，官方指定的正确做法是？
- 在 excluded_middleware 里列出 SubAgentMiddleware
* 关闭 general-purpose subagent，且不传任何同步 subagents
- 把 subagents 参数设为 None
- 把 general-purpose 的 tools 设为空列表
E: excluded_middleware 里列 SubAgentMiddleware 会抛 ValueError。官方要求两步：profile 上设 general_purpose_subagent.enabled=False，并且不通过 subagents= 传同步 subagent。
```

## 下一课

原理讲完了，进入怎么用：**定义一个 subagent 需要写哪几个字段**，
以及 `SubAgent`（字典）与 `CompiledSubAgent`（预编译图）的分界线在哪里。
