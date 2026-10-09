---
num: 39
slug: going-to-production
title: 走向生产
module: W7
tier: A
minutes: 14
desc: thread / user / assistant 三元组，以及生产上必须补的六课
lede: 这一课是全课程的收敛点。官方给出的生产化路径有一个非常清晰的骨架：<b>先把三个原语的边界想清楚，再逐项补上持久化、隔离与管控。</b>
source: https://docs.langchain.com/oss/python/deepagents/going-to-production
source_title: Going to production（官方）
---

## 先建立三个原语

官方在生产指南的开头就定义了三个概念。**它们是所有生产决策的坐标系**：

| 原语 | 定义 | 默认行为 |
| - | - | - |
| **Thread** | 一次对话 | 消息历史与草稿文件**按 thread 作用域**，默认不跨 thread 传递 |
| **User** | 与 agent 交互的人 | 记忆与文件可以是**用户私有**或**跨用户共享**；身份与授权来自你的 auth 层 |
| **Assistant** | 一个配置好的 agent 实例 | 记忆与文件可以绑定到**一个 assistant**，或**所有 assistant 共享** |

!!! key "这三行几乎决定了全部生产架构"
    回头看第 07 课的 `StoreBackend` namespace：

    ```python
    namespace=lambda rt: (rt.server_info.user.identity,)     # → User
    namespace=lambda rt: (rt.server_info.assistant_id,)      # → Assistant
    namespace=lambda rt: (rt.server_info.thread_id,)         # → Thread
    ```

    **生产文档里的"作用域"讨论，落到代码就是这一个 lambda。**
    先把"谁该看到什么"想清楚，剩下的都是配置。

    <div class="flow"><div class="node"><span class="k">产品问题</span><span class="v">这个记忆该给谁看？</span></div><div class="arrow">→</div><div class="node hi"><span class="k">工程答案</span><span class="v">namespace 里放什么</span></div></div>

## 部署路径

官方推荐的路径是 **Managed Deep Agents**：
一个 CLI-first 的托管运行时，用于在 LangSmith 里创建、运行、运维 deep agents。

关键判断标准：它**跑的是同一套 Deep Agents harness**，
区别只是你以"一组文件构成的项目"来声明 agent，而不是自己编译。

| 路径 | 适用 |
| - | - |
| **Managed Deep Agents** | 推荐路径；托管基础设施、认证、webhook、cron |
| **LangSmith Deployment** | 需要自定义应用代码、自定义路由、高级认证的团队 |

!!! note "两条路都会替你准备什么"
    官方说明：无论哪条路，都会为你 provision 好这些基础设施——

    - **threads**
    - **runs**
    - **store**（长期记忆的底座）
    - **checkpointer**（短期记忆的底座）

    这正是第 14 课那张"短期 vs 长期"对照表里提到的两个底座。
    **在生产上，你不需要自己搭它们。**

    LangSmith Deployment 额外还给你认证、webhooks、cron 任务与可观测性，
    并且可以把 agent 通过 MCP 或 A2A 暴露出去。

## 生产上要补的六课

官方把 "Production considerations" 拆成几块，逐块都有具体的工程含义。

### 一、调用方式（Invoking the agent）

从本地 `agent.invoke(...)` 变成"通过 API 调用一个部署好的服务"。
这带来认证、并发、超时这些常规服务化问题。

### 二、多租户（Multi-tenancy）

这是**最需要提前设计**的一块。官方给了示例，包括"在 agent 的工具内部"如何取身份：

```python
# Inside your agent's tool:
# 从运行时取身份，而不是信任模型传入的参数
```

!!! tip "和第 14 课那条经验是同一条"
    检索历史对话时，`user_id` 从 `runtime` 取而不是作为函数参数——
    因为**模型可以伪造参数，但不能伪造运行时**。

    多租户场景下，这条规则的代价会放大：一个被伪造的 `user_id`
    意味着**跨租户数据泄露**。

### 三、异步（Async）

长任务不阻塞请求。这与第 23 课的 async subagent 是同一类需求的两个层次。

### 四、持久性（Durability）

LangGraph 的 durable execution 保证长任务可恢复。
第 04 课里 `PatchToolCallsMiddleware` 存在的理由就在这里——
**恢复是常态，所以"修复被打断的历史"必须是内建能力。**

### 五、记忆的作用域与配置

官方生产指南里 "Memory" 一节专门讲 **Scoping** 与 **Configuration**。
这就是前面 Thread / User / Assistant 三元组的落地。

| 决策 | 影响 |
| - | - |
| 记忆绑定到 user | 个性化、隐私隔离 |
| 记忆绑定到 assistant | agent 有统一身份，跨用户学习 |
| 记忆绑定到 thread | 退化为会话内记忆 |

### 六、执行环境

官方把执行环境拆成 **Filesystem** 与 **Sandboxes** 两块。

<div class="compare">
<div class="yes">
<h4>Filesystem</h4>
<ul>
<li>文件资源的组织与隔离</li>
<li>对应第 07 课的 backend 选择</li>
<li>关键：与租户边界对齐</li>
</ul>
</div>
<div class="no">
<h4>Sandboxes</h4>
<ul>
<li>代码执行的隔离</li>
<li>对应第 09 课</li>
<li>关键：生命周期、TTL、成本</li>
</ul>
</div>
</div>

!!! warning "沙箱的生命周期表在生产文档里最详细"
    官方把完整的生命周期表、async graph factory 注意事项、TTL 行为、
    LangGraph Deployment 接线方式都放在生产文档里——而不是沙箱页面。

    信号很明确：**沙箱在开发时是个功能，在生产时是个资源管理问题。**
    每个活着的沙箱都在花钱，必须有人负责关掉它。

## 护栏（Guardrails）

官方把护栏归成三类：

| 类别 | 手段 | 对应课程 |
| - | - | - |
| **权限** | 声明式文件访问控制 | 第 08 课 |
| **容错** | 重试、降级、限额 | 第 26 课 |
| **数据隐私** | 不让敏感数据进入不该进的地方 | — |

!!! key "数据隐私这一条要单独想"
    它没有对应的"中间件"。它要求你在设计阶段就回答：

    - 哪些数据**可以**被写进记忆文件？（记忆会跨会话保留）
    - 哪些数据**可以**进沙箱？（沙箱里有代码在跑）
    - 哪些数据**可以**发给模型供应商？（这决定了 prompt 里能放什么）

    **这三条是产品与合规决策，不是技术决策。** harness 帮不了你。

## 前端

官方最后一节是 Frontend，指向第 30–33 课讲的那四个模式。

**注意它被放在最后**——这个顺序本身是一个建议：
**先把作用域、持久化、隔离、护栏想清楚，再考虑界面。**

## 一份生产检查清单

把这一课浓缩成可以逐项打勾的清单：

<div class="stack">
  <div class="layer req"><span class="idx">1</span><span class="nm">作用域</span><span class="ds">每份记忆与文件的 namespace 想清楚了吗（thread / user / assistant）</span></div>
  <div class="layer req"><span class="idx">2</span><span class="nm">身份</span><span class="ds">身份是否从 runtime 取，而不是作为工具参数</span></div>
  <div class="layer req"><span class="idx">3</span><span class="nm">持久化</span><span class="ds">checkpointer 与 store 都已就位，thread_id 管理正确</span></div>
  <div class="layer req"><span class="idx">4</span><span class="nm">执行环境</span><span class="ds">backend 选择与租户边界对齐；沙箱有 TTL 与关闭策略</span></div>
  <div class="layer req"><span class="idx">5</span><span class="nm">护栏</span><span class="ds">权限规则、重试与限额、敏感数据流向都已审过</span></div>
  <div class="layer opt"><span class="idx">6</span><span class="nm">可观测</span><span class="ds">tracing 已开，能按 thread 串起委派树</span></div>
  <div class="layer opt"><span class="idx">7</span><span class="nm">前端</span><span class="ds">委派可见、进度可见、待批准可见</span></div>
</div>

```quiz
Q: 官方定义的三个生产原语是什么？
- model、tool、backend
- agent、graph、node
* thread、user、assistant
- store、checkpointer、sandbox
E: 官方在生产指南开篇定义 thread（一次对话）、user（与 agent 交互的人）、assistant（配置好的 agent 实例），并说明记忆与文件在这三个维度上的作用域。

Q: 为什么检索历史对话的工具应该从 runtime 取 user_id 而不是作为参数？
- 因为参数传递会增加 token 开销
- 因为 runtime 中的 user_id 是加密的
* 因为模型可以伪造参数，但不能伪造运行时，涉及跨租户数据安全
- 因为工具参数不支持字符串类型
E: 作用域应由运行时决定。在多租户生产环境下，被伪造的 user_id 意味着跨租户数据泄露，因此官方示例从 runtime.server_info.user.identity 取值。

Q: 无论选哪条部署路径，平台都会为你准备哪四样基础设施？
- 沙箱、向量库、队列、缓存
- 前端、API 网关、CDN、日志
* threads、runs、store、checkpointer
- embedding 模型、reranker、索引、评测集
E: 官方说明两种部署路径都会 provision threads、runs、store 与 checkpointer，因此你不需要自己搭建短期记忆与长期记忆的底座。

Q: 官方把沙箱的完整生命周期表放在生产文档而非沙箱页面，说明了什么？
- 沙箱在生产环境才被启用
- 沙箱的 API 在生产环境会变化
* 沙箱在开发时是功能，在生产时是资源管理问题
- 只有生产环境支持沙箱的 TTL
E: 生命周期的完整表格、TTL 行为与部署接线都放在生产指南，因为每个存活的沙箱都消耗资源与成本，必须有明确的关闭与 TTL 策略。
```

## 下一课

最后一课：**让外部世界接进来**——编辑器与前端协议。
