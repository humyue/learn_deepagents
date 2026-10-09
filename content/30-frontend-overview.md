---
num: 30
slug: frontend-overview
title: 前端架构：coordinator-worker
module: W6
tier: B
minutes: 10
desc: useStream、五类投影、以及 UI 该长成什么样
lede: Deep Agents 的前端不是"聊天框加个加载动画"。官方给的判断标准很直接：<b>当一个 agent 会委派时，把委派过程隐藏起来是浪费。</b>这一课讲前端该暴露什么。
source: https://docs.langchain.com/oss/python/deepagents/frontend/overview
source_title: Frontend · Overview（官方）
---

## 架构：coordinator-worker

Deep Agents 用的是**协调者—工作者（coordinator-worker）**架构：

<div class="flow">
  <div class="node hi"><span class="k">Coordinator</span><span class="v">主 agent：规划、委派、综合</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">Subagent A</span><span class="v">隔离运行</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">Subagent B</span><span class="v">隔离运行</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">结果回到 coordinator</span><span class="v">单次交接</span></div>
</div>

前端对应的结构：

| 位置 | 内容 |
| - | - |
| **根流（root stream）** | coordinator 的消息 |
| **subagent 发现快照** | 有哪些工作者、状态如何 |
| **按 subagent 作用域的视图** | 每个工作者的独立内容 |

!!! key "官方的一句话点出了全部动机"
    > Deep agents are most useful when the UI makes delegation visible.
    > Instead of showing a single opaque assistant bubble, the LangChain SDKs expose
    > the coordinator, subagent discovery, custom state, and sandbox-backed artifacts
    > so users can inspect **how a long-running task is being decomposed and completed**.

    注意最后半句：让用户看到**任务是怎么被拆解和完成的**。
    这不只是"好看"，它是**长任务的可信度来源**。
    一个跑了五分钟的黑盒和一份五分钟的进度报告，用户的心理体验完全不同。

## 接上前端

```typescript
import { useStream } from "@langchain/react";

function App() {
  const stream = useStream<typeof agent>({
    apiUrl: "http://localhost:2024",
    assistantId: "agent",
  });

  // Deep agent 的状态不止 messages
  const todos = stream.values?.todos;
  const subagents = [...stream.subagents.values()];
}
```

三个要点：

1. **`useStream` 与 `createAgent` 的用法一致**——Deep Agents 没有另起一套前端协议。
2. **传类型参数**（`useStream<typeof agent>`）以获得类型安全的流状态。
3. **`stream.values` 能拿到自定义状态**——比如 `todos`，就是第 24 课那个
   `write_todos` 的结果。

## 五类投影

官方表格列了前端 SDK 暴露的五类结构化投影：

| 投影 | 用来做什么 |
| - | - |
| `stream.messages` | coordinator 的对话与最终综合结果 |
| `stream.subagents` | 专门工作者的实时发现，含状态与任务元数据 |
| `stream.values` | 共享状态：todos、计划、报告章节、沙箱元数据、任何自定义键 |
| **工具调用状态** | 把文件系统、搜索、浏览器、领域工具渲染成带进度与结果的卡片 |
| **中断（Interrupts）** | 暂停被委派的工作等待批准或补充信息，且不丢失运行状态 |

!!! note "最后两行是"聊天框"和"工作台"的分界线"
    - **工具调用渲染成卡片**：用户能看到"读了哪个文件、搜了什么、结果是什么"，
      而不是只看到一句"正在思考…"
    - **中断渲染成待办**：用户能直接批准/修改/拒绝，而运行状态被保住

    官方对最终形态的描述是：**"feels closer to an IDE, task board, or workflow monitor
    than a plain chat transcript."**

## 三个模式

官方给的三个前端模式，正好对应前面三块后端能力：

| 模式 | 对应后端能力 | 形态 |
| - | - | - |
| **Subagent streaming** | 委派（第 19–23 课） | 可折叠的工作者卡片，带流式内容与进度 |
| **Todo list** | 任务规划（第 24 课） | 实时进度列表 |
| **Sandbox** | 沙箱（第 09 课） | IDE 式文件浏览器 + 代码查看 + diff 面板 |

<div class="flow">
  <div class="node"><span class="k">委派</span><span class="v">→ SubagentCard</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">规划</span><span class="v">→ TodoList</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">沙箱</span><span class="v">→ 文件浏览器 + diff</span></div>
</div>

!!! tip "注意这三个模式的共同点"
    它们都**直接消费第 24、29 课讲过的结构化状态**，
    而不是去解析 LLM 的自然语言输出。

    **这是 harness 给前端的最大礼物**：因为状态是结构化的、被持久化的、
    被投影出来的，前端不需要"猜"模型在干什么。这就是为什么官方能给出
    组件级的模式文档，而不是"如何解析模型输出"的提示词技巧。

## 版本提示

官方注明这些模式使用 **v1 前端 SDK 包**。
如果你用的是更早的版本，需要看 React / Vue / Svelte / Angular 各自的迁移指南。

```quiz
Q: 官方对 Deep Agents 前端的核心主张是什么？
- 尽量把 agent 执行细节隐藏起来
- 用自然语言摘要代替结构化状态
* 让委派过程可见，而不是只显示一个不透明的对话气泡
- 前端只需渲染最终答案以降低复杂度
E: 官方原话是 "Deep agents are most useful when the UI makes delegation visible"，并强调让用户能检查长任务是如何被拆解和完成的。

Q: stream.values 在前端的主要用途是什么？
- 存储用户界面的本地配置
- 缓存 LLM 的输出 token
* 读取 todos、计划、沙箱元数据等自定义状态
E: 官方把 stream.values 描述为共享状态投影，用于 todos、plans、report sections、sandbox metadata 以及 agent 写入的任何自定义键。
- 计算 token 使用量与费用
E: 官方把 stream.values 描述为共享状态投影，用于 todos、plans、report sections、sandbox metadata 以及 agent 写入的任何自定义键。

Q: 为什么前端模式可以做成组件级文档，而不需要提示词技巧？
- 因为前端 SDK 内置了一个更强的模型
- 因为 LangGraph 会自动生成 UI 组件
* 因为状态是结构化、被持久化并被投影出来的，前端无需猜测模型在做什么
- 因为前端只处理最终消息，不处理中间状态
E: todos、subagent 发现、工具调用状态都是结构化投影，可直接绑定到组件，因此官方能给出组件级模式而非解析自然语言的技巧。
```

## 下一课

三个前端模式逐个拆开。先讲最简单的那个：
**一个 todo 列表组件，如何从 agent state 变成实时进度条。**
