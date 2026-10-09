---
num: 31
slug: frontend-todo-list
title: 前端模式一：Todo List
module: W6
tier: B
minutes: 9
desc: 从 agent state 到进度条 —— 最轻量的一个前端模式
lede: 这是三个前端模式里最容易做的一个，也最能说明"结构化状态让 UI 变简单"这件事：进度条的数据不是算出来的，它<b>本来就在那儿</b>。
source: https://docs.langchain.com/oss/python/deepagents/frontend/todo-list
source_title: Frontend · Todo list（官方）
---

## 数据从哪来

一条链路，没有魔法：

<div class="flow col">
  <div class="node"><span class="k">① 模型调用 write_todos</span><span class="v">写下任务与状态</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">② 状态进入 agent state</span><span class="v">pending / in_progress / completed</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">③ stream.values.todos</span><span class="v">前端读到的就是它</span></div>
</div>

前提条件只有一个：**agent 侧要 opt-in 任务规划**（第 24 课）。

!!! note "所以这一课的前置知识是第 24 课"
    如果 agent 没有装 `TodoListMiddleware`，`stream.values.todos` 就是空的。
    前端写得再漂亮也没有数据。**这也是一个典型的"症状在 A 层、病因在 B 层"的例子**
    ——UI 不显示进度，先去检查后端有没有开任务规划。

## 前端读法

```typescript
const stream = useStream<typeof agent>({ apiUrl: "...", assistantId: "agent" });

const todos = stream.values?.todos;
```

## 要做四件事

官方把 `TodoList` 组件拆成四个部分：

| 组件 | 做什么 |
| - | - |
| **TodoList** | 整体容器 |
| **进度条（progress bar）** | 已完成比例 |
| **TodoItem** | 单条任务的渲染（含状态） |
| **进度计算** | 从 todos 数组算出比例 |

```typescript
// 进度计算的核心逻辑：数 completed
const done = todos?.filter((t) => t.status === "completed").length ?? 0;
const total = todos?.length ?? 0;
const percent = total === 0 ? 0 : Math.round((done / total) * 100);
```

!!! key "注意这里的"简单"是有原因的"
    进度条之所以是"数一数"，是因为**状态是离散且规范的**：
    `pending` / `in_progress` / `completed` 三个值，不是模型随口说的
    "差不多做完了"。

    **这就是把计划外化成结构化数据的复利。** 如果一个 agent 只在对话里说
    "我已经完成了一部分"，前端永远无法可靠地画出进度条。

## 与聊天消息的组合

官方有一节 "Combining with chat messages"。这是实际产品里必须处理的：

<div class="compare">
<div class="yes">
<h4>只显示 todo</h4>
<ul>
<li>清楚但干瘪</li>
<li>用户不知道 agent 具体在做什么</li>
<li>适合长任务的侧栏</li>
</ul>
</div>
<div class="no">
<h4>todo + 消息流</h4>
<ul>
<li>进度与细节都有</li>
<li>需要设计信息层级</li>
<li>适合主视图</li>
</ul>
</div>
</div>

常见做法是把 todo 作为**侧栏或顶部**的进度指示，把消息流作为主体。
这样用户既知道"到哪一步了"，也能随时下钻看细节。

## 空状态与加载状态

官方单独列了一节 "Handling empty and loading states"。这一点很实用，因为
**todo 列表是间歇性出现的**：

| 情况 | UI 应该怎么表现 |
| - | - |
| agent 还没写 todo（`todos` 为 undefined） | **不要显示空进度条**，直接隐藏整个组件 |
| todo 刚建立，还没开始 | 显示全部 pending |
| 全部完成 | 显示 100%，或收起 |

!!! tip "第一条是最容易做错的"
    渲染一个 `0/0 · 0%` 的进度条，比不渲染更糟——
    它暗示"有个东西卡住了"，而实际上只是这个 agent 不用任务规划。

    判断标准很简单：**没有数据时，组件就不该存在。**

## 适用场景

官方列的用例，本质上是同一件事的不同说法：

- 长跑任务的进度可见性
- 多步流程的当前阶段提示
- 让用户能预判"还要多久"

```quiz
Q: 前端要拿到 todos，必须满足的前置条件是什么？
- 前端必须订阅 stream.subagents
- backend 必须换成 StoreBackend
* agent 侧必须 opt-in 任务规划（传入 TodoListMiddleware）
- 必须在 create_deep_agent 里设置 response_format
E: stream.values.todos 的数据来自 write_todos 写入的 agent state。如果 agent 没装 TodoListMiddleware，这个键就是空的，与前端写法无关。

Q: 关于 todos 为空时的 UI 处理，官方建议的方向是？
- 渲染一个 0% 的进度条以保持布局稳定
- 显示"暂无可显示的任务"文案占位
* 处理空状态，而不是渲染空进度条
- 触发一次重试以获取 todos
E: 官方专门列了 handling empty and loading states。空 todos 表示该 agent 未使用任务规划，此时应隐藏组件而非展示空进度条，避免误导用户以为流程卡住。

Q: 为什么这个进度条可以用"数一数"的方式实现？
- 因为前端 SDK 内置了任务进度计算器
- 因为模型会输出一个百分比数字
* 因为状态是离散规范的三个枚举值
- 因为 todos 数组的长度固定
E: 状态只有 pending / in_progress / completed 三种规范取值，因此统计已完成数量即可得到可靠进度，不需要解析自然语言描述。
```

## 下一课

Todo 是"最轻"的前端模式。下一课是最能体现 Deep Agents 特色的那个：
**把每个 subagent 渲染成一张可展开的卡片。**
