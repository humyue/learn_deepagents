---
num: 23
slug: async-subagents
title: Async Subagents：跨请求长跑的子任务
module: W4
tier: B
minutes: 11
desc: 生命周期、transport、部署拓扑 —— 当子任务比一次请求活得久
lede: 同步 subagent 有一个硬约束：父 agent 必须等。如果子任务要跑二十分钟，或者用户想在它跑的时候接着聊别的，就需要把委派从"一次函数调用"升级成"一个可查询的任务"。
source: https://docs.langchain.com/oss/python/deepagents/async-subagents
source_title: Async subagents（官方）
---

## 什么时候需要它

官方在同步 subagent 页面上把适用场景点得很清楚：
**长跑任务、并行工作流、以及需要中途操纵（mid-flight steering）与取消的场景。**

| 需求 | 同步 subagent | Async subagent |
| - | - | - |
| 父 agent 等结果 | 必须等 | 不等，可继续 |
| 中间给指示 | 无状态，不行 | 可以 |
| 取消 | 不行 | 可以 |
| 跨请求存活 | 不行 | 可以 |
| 复杂度 | 低 | 高（要管生命周期） |

<div class="flow">
  <div class="node dim"><span class="k">同步</span><span class="v">task() 阻塞 → 返回结果</span></div>
  <div class="arrow">vs</div>
  <div class="node hi"><span class="k">异步</span><span class="v">launch → 拿到句柄 → 之后查询状态</span></div>
</div>

## 生命周期

异步 subagent 的模型从"调用"变成了"任务"。典型循环：

<div class="flow col">
  <div class="node"><span class="k">launch</span><span class="v">启动子任务，立刻拿到标识</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">轮询或事件驱动</span><span class="v">queued → running → done / failed</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">取回结果</span><span class="v">完成后再读</span></div>
</div>

!!! warning "别刚启动就立刻轮询"
    官方专门列了一条 troubleshooting：**"Supervisor polls immediately after launch"**。
    刚启动时状态必然还是 queued 或 running，立刻轮询只是浪费调用。
    正确做法是让 supervisor 在合理的间隔后查询，或者由完成事件驱动。

## 两个必须做的选择

### 选择一：传输方式（transport）

| 方式 | 适用 |
| - | - |
| **ASGI transport** | co-deployed —— subagent 与 supervisor 部署在一起，同进程通信 |
| **HTTP transport** | remote —— subagent 部署在别处，通过网络调用 |

### 选择二：部署拓扑

| 拓扑 | 形态 | 适用 |
| - | - | - |
| **Single deployment** | supervisor 与 subagent 同一个部署 | 简单、低延迟 |
| **Split deployment** | 完全分开部署 | 独立扩缩容、独立发布、隔离失败域 |
| **Hybrid** | 部分本地、部分远程 | 常见：核心子任务本地，重活外派 |

<div class="flow">
  <div class="node"><span class="k">Single</span><span class="v">一个部署，ASGI</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">Split</span><span class="v">两个部署，HTTP</span></div>
  <div class="arrow">·</div>
  <div class="node hi"><span class="k">Hybrid</span><span class="v">本地 + 远程混合</span></div>
</div>

!!! key "这个选择本质上是"失败域"的选择"
    Split deployment 的收益不只是扩缩容，而是**隔离故障**：
    subagent 崩了，supervisor 还能活着报告"那个任务失败了"。
    Single deployment 里，一个内存泄漏会带走整个系统。

## 状态管理

官方明确提醒：**异步 subagent 有自己的状态管理语义**，与同步模式不同。
关键点是——不能指望它像同步 subagent 那样自动把结果塞回父上下文。
你需要自己维护"任务 ID → 状态 → 结果"的映射。

这带来一个必须设计的细节：**任务标识放在哪里？**

- 放进 thread 的 metadata（推荐：能跨 turn 找回）
- 放进自定义 state（第 17 课）
- 放进外部存储

## 最佳实践

官方列的三条：

| 实践 | 内容 |
| - | - |
| **给本地开发配 worker pool 大小** | 不要开太多，本地机器扛不住 |
| **写清楚的 subagent description** | 和同步模式一样：决定何时委派 |
| **用 thread ID 做 trace** | 异步执行跨请求，没有 thread ID 就无法把 trace 串起来 |

!!! tip "第三条在生产上几乎是必需的"
    异步任务的问题不是"能不能跑完"，而是**"跑完之后我怎么知道它是谁"**。
    官方给出的答案是：用 thread ID 作为关联键做 tracing。
    没有这个，你在 LangSmith 里会看到一堆无主的运行记录。

## 排障清单

官方列了四类常见问题，都很典型：

| 症状 | 原因 / 对策 |
| - | - |
| Supervisor 刚启动就轮询 | 应延迟查询或改为事件驱动 |
| 状态陈旧（stale status） | 缓存了旧状态；要重新拉取 |
| 任务 ID 查不到 | 标识没持久化，或命名空间不对 |
| 启动变成排队而不执行 | worker pool 太小，或 worker 未启动 |

```quiz
Q: 什么时候应该从同步 subagent 换成异步 subagent？
- 当 subagent 的工具数量超过十个时
- 当需要减少 token 消耗时
* 当任务长跑、需要中途操纵、或需要取消时
- 当 subagent 需要访问文件系统时
E: 官方把异步 subagent 定位给长跑任务、并行工作流，以及需要 mid-flight steering 与取消的场景。同步 subagent 会阻塞且无状态，无法中途干预。

Q: 官方列出的第一条排障项"supervisor polls immediately after launch"说明了什么设计约束？
- 异步 subagent 必须先预热才能启动
- 轮询频率必须与模型调用次数一致
* 刚启动时状态必然未完成，立即轮询是错误做法
- supervisor 不能直接查询 subagent 状态
E: 刚 launch 时任务还在 queued 或 running，立刻轮询只是浪费。正确做法是合理间隔后查询，或由完成事件驱动。

Q: 用 thread ID 做 tracing 在异步场景下为什么特别重要？
- 因为异步 subagent 不产生任何日志
- 因为 thread ID 决定了 subagent 的模型选择
* 因为执行跨请求，没有关联键就无法把 trace 串起来
- 因为 LangSmith 只对带 thread ID 的运行计费
E: 官方把它列为最佳实践：异步执行发生在多个请求之间，用 thread ID 关联才能追踪到具体是哪次任务。

Q: Split deployment 相对 Single deployment 的主要收益是什么？
- 减少模型调用的总次数
- 消除 transport 层的配置需求
* 独立扩缩容、独立发布与故障域隔离
- 让 subagent 可以访问 supervisor 的内存状态
E: 分开部署让两个部分可以独立扩缩容与发布，同时隔离失败域。代价是必须改用 HTTP transport 并处理网络失败。
```

## 下一课

三种 subagent 讲完了。但"多步任务"还有另一半问题：**模型自己怎么记账？**
下一课：任务规划与 `write_todos`。
