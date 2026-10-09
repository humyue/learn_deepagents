---
num: 32
slug: frontend-subagent-streaming
title: 前端模式二：Subagent 卡片
module: W6
tier: B
minutes: 11
desc: selector-based 订阅、discovery snapshot、以及"按需挂载"如何让 UI 可扩展
lede: 这是最能体现 Deep Agents 前端特色的一个模式。它的核心设计是<b>发现与内容分离</b>：先拿一份轻量的"有哪些子代理"清单，只有当你真的展开某一张卡片时，才去订阅它的内容。
source: https://docs.langchain.com/oss/python/deepagents/frontend/subagent-streaming
source_title: Frontend · Subagent streaming（官方）
---

## 为什么不把所有东西都塞进根流

官方给的理由列了四条，读起来像一份分层原则：

| 流 | 内容 |
| - | - |
| `stream.messages` | **只有** coordinator 的消息 |
| `stream.subagents` | 发现快照：身份、namespace、状态 |
| 每个 subagent 的消息、工具调用、values | 通过 **selector helpers** 读取 |

> The UI stays clean: the coordinator's reasoning is separate from the specialists' work.

<div class="flow">
  <div class="node hi"><span class="k">根流</span><span class="v">只讲协调者的思路</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">发现清单</span><span class="v">有哪些工作者、什么状态</span></div>
  <div class="arrow">＋</div>
  <div class="node dim"><span class="k">按需订阅</span><span class="v">展开哪张卡片才读哪份内容</span></div>
</div>

## SubagentDiscoverySnapshot

这是模式的核心数据结构。官方对它的描述很精确：

> Each snapshot is a **lightweight discovery record** for a subagent running inside the thread.
> It tells your UI that a subagent exists, **where it sits in the subagent tree**,
> and **what lifecycle state it is in**.
>
> The snapshot does **not** include the subagent's streamed messages or tool calls.

!!! key "关键在最后那句"不包含""
    **快照是索引，不是内容。** 这一个设计决策带来三个后果：

    1. **成本低**：渲染 N 张卡片不需要订阅 N 条流
    2. **可扩展**：任务再大，"有哪些子代理"这份清单也很小
    3. **按需付费**：只有展开的那几张卡片会真正读取内容

    对比一下"把子代理内容全塞进根流"的做法：
    渲染一个 50 个子任务的运行，你得先传 50 份完整内容。

## selector hooks

快照拿到之后，用 selector hook 订阅具体内容：

```tsx
import { useMessages, useToolCalls, type AnyStream, type SubagentDiscoverySnapshot } from "@langchain/react";

function SubagentCard({ stream, subagent }: {
  stream: AnyStream;
  subagent: SubagentDiscoverySnapshot;
}) {
  const [expanded, setExpanded] = useState(true);
  const messages = useMessages(stream, subagent);       // 只订阅这个子代理的消息
  const toolCalls = useToolCalls(stream, subagent);     // 只订阅它的工具调用
  ...
}
```

官方对这两个 hook 的机制说明很值得注意：

> These hooks use the snapshot namespace to subscribe to the subagent's stream primitives
> **only when the corresponding card or panel is mounted**.

<div class="flow">
  <div class="node"><span class="k">卡片挂载</span><span class="v">→ hook 生效 → 订阅该 namespace</span></div>
  <div class="arrow">·</div>
  <div class="node dim"><span class="k">卡片卸载</span><span class="v">→ 订阅停止</span></div>
</div>

!!! tip "这是 React 的"免费"优化，但前提是 API 设计对了"
    "只在挂载时订阅"这句话之所以能成立，是因为**快照里带了 namespace**。
    没有 namespace，hook 就不知道该订阅哪条流，只能订阅全部。

    **所以"发现记录里存什么"这个后端设计决策，直接决定了前端能不能做到按需加载。**
    这是这一课最值得记住的因果链。

## 构建卡片

一张卡片通常展示四样东西（官方列举）：

| 内容 | 数据来源 |
| - | - |
| 专家的名字 | `subagent.name` |
| 状态 | `subagent.status` |
| 流式内容 | `useMessages(stream, subagent)` |
| 工具调用 | `useToolCalls(stream, subagent)` |

加上折叠/展开状态（`useState(true)`），就是一个可折叠的卡片。

## 进度追踪

```tsx
function SubagentProgress({ subagents }: { subagents: SubagentDiscoverySnapshot[] }) {
  const completed = subagents.filter((s) => s.status === "complete").length;
  const total = subagents.length;
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
  ...
}
```

和 Todo 进度条是同一套逻辑（第 31 课）：**数状态**。
注意这里的状态枚举是 `"complete"`，与第 29 课 `stream.subagents` 里
后端 `status`（`started` / `completed` / `failed` / `interrupted`）的写法有差异
——**写代码时以你所用 SDK 版本的实际类型定义为准。**

## 布局：卡片挂在哪

官方给的核心布局模式是：

> render coordinator messages from the root stream and **attach subagent cards to the
> AI message whose tool call spawned them**.

也就是：**卡片不是独立列表，而是挂在"派生它的那条 AI 消息"下面。**

<div class="flow col">
  <div class="node"><span class="k">AI 消息</span><span class="v">"我来分三路调研" + task tool_call</span></div>
  <div class="arrow">↓ 挂载</div>
  <div class="node hi"><span class="k">SubagentCard × 3</span><span class="v">卡片出现在产生它们的那个回合下面</span></div>
</div>

实现要点（官方说明）：**在聊天布局里，用派生它的 tool-call ID 作为索引**，
这样每张卡片就会出现在正确的协调者回合下面。

!!! note "这个细节决定了 UI 是否"讲得通""
    如果卡片都堆在底部，用户看到的是"一堆工作者"，但看不出**为什么**要有这些工作者。
    挂在对应的 AI 消息下面，因果关系就自己显示出来了：
    **"我说要分三路 → 于是有三个工作者。"**

## 可扩展性：官方给的最重要的一句话

> For large tasks, this also keeps the UI scalable. Users can skim the coordinator's
> high-level plan, **expand only the specialist work they care about**, and still
> retain the full subagent trace for debugging, audit, or replay.

三个收益：

| 收益 | 怎么来的 |
| - | - |
| 可浏览 | 协调者计划是"目录"，一眼看完 |
| 可下钻 | 展开只在需要时发生 |
| **可审计** | 完整 trace 仍然保留，可以复现 |

!!! key "最后一条是生产环境的硬需求"
    "只展开关心的"是体验优化；"完整 trace 仍然保留"是**审计与复现能力**。
    一个跑砸了的长任务，你必须能回头看清每个子代理当时看到了什么、做了什么。

    这两个需求看起来矛盾（一个要少显示，一个要全保留），
    而这个架构同时满足了它们：**数据都在，只是不都渲染。**

```quiz
Q: SubagentDiscoverySnapshot 里不包含什么？
- subagent 的名字与命名空间
- subagent 在树中的位置
* subagent 的消息与工具调用内容
- subagent 的生命周期状态
E: 官方明确说明快照是轻量发现记录，不含消息或工具调用内容；这些内容通过 useMessages、useToolCalls 等 selector hook 按需订阅。

Q: selector hook 能做到"仅在卡片挂载时订阅"的关键前提是什么？
- React 的 Suspense 机制
- 后端会主动推送全部子代理内容
* 快照里带有 namespace，hook 能据此定位要订阅哪条流
- 每个子代理使用独立的 API 端点
E: 官方说明这些 hook 使用快照的 namespace 去订阅该子代理的流原语。没有 namespace 就无法定位，只能订阅全部。

Q: subagent 卡片在聊天布局中应该挂在哪里？
- 统一放在页面底部的固定面板
- 放在它自己的独立路由页面
* 挂在派生它的那条 AI 消息下面，用 tool-call ID 索引
- 放在 todo 列表组件内部
E: 官方给的核心布局模式是把卡片附着到派生了该子代理的 AI 消息上，并在聊天布局里按 tool-call ID 索引，让因果关系直接可见。

Q: "只展开关心的卡片但仍保留完整 trace"同时满足了哪两个需求？
- 降低 token 消耗与提高模型准确率
* 可浏览的体验与可审计、可复现的能力
- 减少前端依赖与减少后端部署
- 更快的首屏渲染与更小的 bundle 体积
E: 官方指出用户可以不展开大任务的细节，同时完整 subagent trace 仍被保留，用于 debugging、audit 或 replay。前者是体验，后者是生产必需的能力。
```

## 下一课

Todo 和 Subagent 卡片消费的都是"状态"。最后一个是重头戏：
**当 agent 在沙箱里工作时，前端怎么变成一个 IDE。**
