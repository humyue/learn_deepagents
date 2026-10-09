---
num: 24
slug: task-planning-todos
title: 任务规划与 write_todos
module: W4
tier: B
minutes: 9
desc: 一个可问责的进度载体，以及它为什么从 v0.7 起变成 opt-in
lede: 委派是把任务拆给别的 agent，而 todo 列表是把任务拆给<b>自己</b>。这一课讲 <code>TodoListMiddleware</code> 提供的那个很朴素却很有用的机制。
source: https://docs.langchain.com/oss/python/deepagents/overview#task-planning
source_title: Overview · Task planning（官方）
---

## 启用方式

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_deep_agent(
    model="openai:gpt-5.5",
    middleware=[TodoListMiddleware()],
)
```

装上之后，agent 多了一个 `write_todos` 工具，可以维护一份结构化任务列表。

!!! warning "v0.7 起是 opt-in"
    官方明确写了：**从 v0.7 开始，任务规划只能 opt-in。**
    更早的版本里，任务规划 middleware 是**默认包含**的。
    如果你读的是旧教程或旧代码，会看到它"天然存在"——现在不是了。

## 数据结构

每个任务有状态，存在 agent state 里：

| 状态 | 含义 |
| - | - |
| `pending` | 还没开始 |
| `in_progress` | 正在进行 |
| `completed` | 已完成 |

因为存在 state 里，所以它可以被**流式读取**——这正是前端 Todo 组件的数据来源（第 31 课）。

<div class="flow">
  <div class="node"><span class="k">write_todos</span><span class="v">模型写入任务列表</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">agent state</span><span class="v">任务列表 + 状态</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">两条消费路径</span><span class="v">模型自己参考 / 前端渲染进度</span></div>
</div>

## 官方列的三类适用场景

| 场景 | 为什么有用 |
| - | - |
| **长或复杂的多步任务** | 给模型一个外部的待办清单，抵抗在长对话里丢失目标 |
| **能力较弱的模型** | 官方原话：它们受益于一个**显式的问责工具**（explicit accountability tool） |
| **需要从 state 流式渲染进度的 UI** | 任务状态天然就是进度数据 |

!!! key "为什么它对弱模型特别有用"
    强模型能"在心里"维持一个计划；弱模型在长上下文里会漂移。
    `write_todos` 的作用是**把计划外化**——写下来的东西不会随上下文衰减。

    这和"让人写清单"是同一个心理学机制：**外化降低工作记忆负担。**

## 为什么它不是默认开的

官方给的定位是"基础能力里有用的可选项（Optional capabilities）"。
回顾第 03 课的出厂配件清单，它明确被列在"默认没有的东西"里。

理由不难推：

- **每一次写 todo 都是一次模型调用**，要花 token 与时间
- **简单任务不需要计划**，加进来纯粹是噪音
- **它会改变模型的输出风格**（模型会更倾向于"先列清单再干活"），而这未必是你想要的

!!! tip "试探性的判断方法"
    如果你发现 agent 在第 40 轮之后忘了最初的目标，或者把子任务做漏了，
    就加上 `TodoListMiddleware` 试试。
    **它是一个"症状驱动"的优化，而不是"默认最佳实践"。**

## 它和 subagent 的分工

两者都叫"拆任务"，但拆给了不同的对象：

<div class="compare">
<div class="yes">
<h4>write_todos（拆给自己）</h4>
<ul>
<li>任务仍在主 agent 的窗口里执行</li>
<li>产出：一个进度列表</li>
<li>不省 token（甚至多花）</li>
<li>解决：注意力漂移</li>
</ul>
</div>
<div class="no">
<h4>subagent（拆给别人）</h4>
<ul>
<li>任务在独立窗口里执行</li>
<li>产出：一份隔离后的结果</li>
<li>省大量 token</li>
<li>解决：上下文膨胀</li>
</ul>
</div>
</div>

一个长任务里，两者通常**同时**使用：todo 管自己的议程，subagent 消化重活。

## 与其他"规划"手段的区别

| 手段 | 谁在执行 | 在哪执行 |
| - | - | - |
| `write_todos` | 主 agent 自己 | 主窗口 |
| 同步 subagent | 子 agent | 隔离窗口 |
| dynamic subagent | 代码编排的多个子 agent | 隔离窗口 + 解释器 |
| LangGraph 手写工作流 | 你定义的图 | 由你决定 |

```quiz
Q: 从 v0.7 起，任务规划（write_todos）的默认状态是？
- 默认包含在裸栈中
- 默认包含，但只在长会话中激活
* 默认不包含，必须显式传入 middleware
- 默认包含，除非使用沙箱后端
E: 官方明确说明 Starting in v0.7 task planning is opt-in only，更早版本中任务规划 middleware 是默认包含的。

Q: 官方认为 write_todos 对哪类模型特别有用，理由是什么？
- 对多模态模型，因为它们需要视觉化的计划
- 对最强的模型，因为它们能处理更多任务
* 对能力较弱的模型，因为它提供了一个显式的问责工具
- 对所有模型，因为它能降低 token 消耗
E: 官方在适用场景里列出 less capable models that benefit from an explicit accountability tool。强模型通常能自行维持计划。

Q: todo 状态存在哪里，因此能带来什么额外能力？
- 存在文件系统里，因此可以跨 thread 共享
- 存在 store 里，因此可以长期保留
* 存在 agent state 里，因此可以被流式渲染成进度
- 存在 middleware 实例里，因此不占 token
E: 任务支持状态跟踪并持久化在 agent state 中，这使得 UI 可以从 state 流式渲染进度，也就是前端 Todo list 组件的数据来源。
```

## 模块 D 结束

委派层讲完了。接下来是让这一切**可以被信任地放进生产**的三课：中断、韧性、以及按模型打补丁的 profile。
