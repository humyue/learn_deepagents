---
num: 29
slug: event-streaming-subagents
title: stream.subagents：每个子任务一个句柄
module: W6
tier: A
minutes: 12
desc: 类型化投影、惰性打开、生命周期状态 —— 前端渲染委派树的基础
lede: 上一课讲的是"如何区分事件来自谁"。这一课讲 Deep Agents 在这之上加的专门抽象：<b>把每个被委派的任务投影成一个独立的对象</b>，你可以单独订阅它的消息、工具调用、甚至是它自己派生的子任务。
source: https://docs.langchain.com/oss/python/deepagents/event-streaming
source_title: Event streaming（官方）
---

## 从"事件流"到"对象"

<div class="compare">
<div class="yes">
<h4>原始流式</h4>
<ul>
<li>一维的事件序列</li>
<li>你在下游自己按 namespace 分组</li>
<li>逻辑自己维护</li>
<li>灵活但繁琐</li>
</ul>
</div>
<div class="no">
<h4>stream.subagents</h4>
<ul>
<li>每个委派任务一个句柄</li>
<li>句柄自带 messages / tool_calls / values / output</li>
<li>嵌套子任务也是一等公民</li>
<li>直接面向 UI</li>
</ul>
</div>
</div>

!!! note "官方原话"
    Deep Agents add a subagent projection on top of LangGraph streaming.
    Use `stream.subagents` when you want **one stream handle per delegated `task` call**.

## 一个关键的性能设计：惰性打开

> The projection is lightweight: it **discovers** subagent tasks first,
> and message, tool-call, and value streams are **opened only when you access them**
> on a subagent handle.

这一点很重要，因为它决定了成本模型：

<div class="flow">
  <div class="node"><span class="k">发现阶段</span><span class="v">只枚举出有哪些子任务</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">按需打开</span><span class="v">访问 subagent.messages 时才真正订阅</span></div>
</div>

**所以你只为"你真的要展示的东西"付费。**
如果一个 UI 只在侧栏显示"3 个子任务正在运行"，它完全不需要订阅任何 message 流。

## 名字来自哪里

这是设计上很干净的一点：

> Each handle's `name` is the sub-agent's configured name:
> the `subagent_type` the coordinator passes when it calls the `task` tool.

也就是说——**你在 subagent 定义里写的 `name`，就是流里能用来过滤和路由的标签。**
不需要额外注册、不需要 id 映射。

!!! key "这解释了一个设计约束"
    这也再次说明为什么 `name` 必须是"唯一标识符"（第 20 课）。
    它同时是：
    - `AIMessage` 的 metadata
    - 流式里的路由键
    - 前端卡片的分组依据

    改名字不只是改显示，会打断所有依赖它的过滤逻辑。

## 句柄上有什么

| 字段 | 内容 |
| - | - |
| `name` | 子 agent 名，取自 coordinator 在 task 调用里选的 `subagent_type` |
| `messages` | 子 agent 发出的消息 |
| `subagents` | **嵌套的**子 agent 调用 |
| `output` | 子 agent 的最终状态，或该委派任务的完成信号 |
| `path` | 该子 agent 流的 namespace 路径 |
| `status` | 生命周期状态：`started` / `completed` / `failed` / `interrupted` |
| `tool_calls` | 限定在该子 agent 范围内的工具调用 |

```python
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Write me a haiku about the sea"}]},
    version="v3",
)

for subagent in stream.subagents:
    print(subagent.name, subagent.path, subagent.status)

    for message in subagent.messages:
        print(message.text)
```

!!! note "注意三个细节"
    1. 入口是 **`stream_events`**（不是 `stream`），并且要传 **`version="v3"`**。
    2. `path` 就是 namespace——手工追踪时可以用它和原始流对上。
    3. `subagents` 字段的存在意味着**递归**：子任务还能再派子任务，
       投影会跟着树的形状长。

## 只需生命周期时

官方给了一条明确的优化建议：

> Use `stream.subagents` when you only need to show which subagents started and finished.
> You do not need to subscribe to message or value streams unless you access those
> projections on an individual subagent.

```python
stream = agent.stream_events(input, version="v3")

for subagent in stream.subagents:
    print(subagent.name, subagent.status)      # 只读状态，不碰 messages
```

**只读 `status` 就不会打开消息流。** 这是一个"在同一套 API 里表达不同成本"的设计。

## `status` 的四个值说明什么

| 状态 | 含义 | UI 应该怎么反应 |
| - | - | - |
| `started` | 已开始 | 显示进度指示器 |
| `completed` | 完成 | 收起指示器，可展开结果 |
| `failed` | 失败 | 显示错误，可能需要重试 |
| `interrupted` | 被中断 | 显示"等待人工批准"（第 25 课） |

!!! tip "`interrupted` 是 Deep Agents 特有的一种"
    它是"委派 + 人工批准"两个机制交叉的产物：
    子任务在等一个人批准某个工具调用。
    前端必须能表达这个状态，否则用户会以为卡住了。

## 并发消费

官方专门有一节 "Consume concurrently"。这是实战中的必需：

<div class="flow col">
  <div class="node"><span class="k">串行消费</span><span class="v">先读完 A 再读 B → 慢的会阻塞快的</span></div>
  <div class="arrow">vs</div>
  <div class="node hi"><span class="k">并发消费</span><span class="v">多个句柄同时读 → 实时反映真实并行度</span></div>
</div>

因为 subagent 本来就是并行的，**串行消费流会把并行的事实压成串行的表象**——
用户看到的是"一个接一个"，而实际是同时跑。

## subagents 与 subgraphs 的区别

官方特意加了一节澄清这两个容易混的概念：

| | subgraphs | subagents |
| - | - | - |
| 是什么 | LangGraph 的通用机制 | Deep Agents 的语义投影 |
| 粒度 | 任意子图 | 一次 `task` 委派 |
| 命名 | namespace 路径 | subagent 的 `name` |
| 建议 | 需要看内部步骤时 | 需要按委派任务组织 UI 时 |

**一句话：subgraphs 是机制，subagents 是语义。**
前者只关心"图里还有子图"，后者知道"这是一次委派"。

```quiz
Q: stream.subagents 的 name 字段来自哪里？
- 一个自动生成的运行 ID
- LangGraph 的 namespace 路径
* subagent 定义里的 name（即 task 调用传的 subagent_type）
- 主 agent 在提示词里给它起的别名
E: 官方说明每个 handle 的 name 就是 sub-agent 的 configured name，也就是 coordinator 调用 task 时传入的 subagent_type，因此与你定义的标签一致。

Q: 只读取 subagent.status 而不访问 messages，会带来什么？
- 会报错，必须先订阅 messages
- 会仍然打开全部子流
* 不会打开消息流，因为投影是惰性打开的
- 会导致 status 一直停在 started
E: 官方说明投影很轻量：先发现子任务，只有在句柄上访问 message / tool-call / value 投影时才真正打开对应流。因此只读状态成本最低。

Q: status 出现 interrupted 说明什么？
- 子 agent 因超时被取消
- 子 agent 等待模型限流恢复
* 子 agent 在等一次人工批准
- 子 agent 的模型调用失败了
E: interrupted 表示委派的任务因 human-in-the-loop 暂停。它是委派与审批机制交叉的产物，前端需要能表达这个状态。

Q: subgraphs 与 subagents 最准确的区分是？
- 前者用于 Python，后者用于 TypeScript
- 前者只在沙箱下可用，后者在任意 backend 下可用
* 前者是 LangGraph 的通用机制，后者是 Deep Agents 的语义投影
- 前者按工具分组，后者按模型分组
E: subgraphs 是 LangGraph 层面的能力（哪些子图在跑），subagents 是 Deep Agents 在委派语义上做的投影（哪次 task 委派在跑），命名也分别用 namespace 与 subagent name。
```

## 下一课

流式的原理讲完了。接下来四课进入前端：
**一个 agent 的树状执行，怎么变成一个用户能看懂的界面。**
