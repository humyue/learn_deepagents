---
num: 40
slug: acp-and-ag-ui
title: 对外协议：ACP 与 AG-UI
module: W7
tier: B
minutes: 10
desc: 让编辑器和前端接进来 —— 两种协议解决两个方向的问题
lede: 最后一块拼图。<code>create_deep_agent</code> 造出来的 agent 是一个服务，它需要两种对外接口：一种朝<b>编辑器</b>，一种朝<b>前端 UI</b>。官方各给了一个协议。
source: https://docs.langchain.com/oss/python/deepagents/acp
source_title: Agent Client Protocol / AG-UI（官方）
---

## 两个方向

<div class="compare">
<div class="yes">
<h4>ACP（Agent Client Protocol）</h4>
<ul>
<li>朝向：<b>编辑器 / IDE</b></li>
<li>把 agent 变成编辑器里的一个"智能体后端"</li>
<li>客户端举例：Zed、Toad</li>
</ul>
</div>
<div class="no">
<h4>AG-UI（Agent User Interaction）</h4>
<ul>
<li>朝向：<b>Web / App 前端</b></li>
<li>把 agent 的事件流交给前端渲染</li>
<li>解决"逐 token 与工具调用怎么显示"</li>
</ul>
</div>
</div>

!!! key "为什么需要两个协议"
    因为前端和编辑器的需求不一样：

    - **编辑器**关心：文件上下文、代码位置、diff、光标处的建议。
      它需要 agent **知道自己正打开哪个文件、光标在哪**。
    - **前端**关心：消息流、工具调用卡片、进度、待批准。
      它需要 agent **把执行过程投影成可视化单元**。

    一个协议很难同时优雅地服务这两种交互形态。

## ACP：把 agent 装进编辑器

官方的 ACP 页面结构很简洁：**Quickstart + 客户端列表**。

| 客户端 | 说明 |
| - | - |
| **Zed** | 一个高性能的代码编辑器 |
| **Toad** | 官方文档里列出的另一个客户端 |

!!! note "这个模式的意义"
    接入 ACP 意味着你的 deep agent 可以在**别人的编辑器里**被使用，
    而不是只在你自己写的 UI 里。

    这带来一个架构后果：**agent 的产出要适配编辑器的交互习惯**。
    比如在编辑器里，"生成代码"通常应该表现为**一个可 review 的 diff**，
    而不是一段可以复制粘贴的文本。

    回顾第 33 课的前端沙箱模式——那里的 diff 面板是同一个思路，
    只是读者换成了编辑器。

## AG-UI：把事件流交给前端

AG-UI 的页面结构更完整，步骤也更清晰：

<div class="flow col">
  <div class="node"><span class="k">① Install dependencies</span><span class="v">装依赖</span></div>
  <div class="node"><span class="k">② Create a deep agent</span><span class="v">用 create_deep_agent 造 agent</span></div>
  <div class="node"><span class="k">③ Serve the agent</span><span class="v">把它作为服务暴露出去</span></div>
  <div class="node"><span class="k">④ Connect the AG-UI adapter</span><span class="v">接上适配器</span></div>
</div>

然后是两个关键章节：

| 章节 | 内容 |
| - | - |
| **Stream events** | AG-UI 定义的事件类型 —— 前端按事件渲染 |
| **Connect a frontend** | 把前端接到这条流上 |
| **Programmatic API** | 用代码直接驱动，不经过 UI |

!!! key "这三个章节其实对应三种消费方式"
    <div class="flow">
      <div class="node"><span class="k">事件流</span><span class="v">给 UI 框架消费</span></div>
      <div class="arrow">·</div>
      <div class="node"><span class="k">前端连接</span><span class="v">给现成组件消费</span></div>
      <div class="arrow">·</div>
      <div class="node hi"><span class="k">Programmatic API</span><span class="v">给自动化脚本消费</span></div>
    </div>

    最后一条经常被忽略但很有用：**不是所有消费方都是人。**
    一个 CI 流程、一个批处理脚本也可以"驱动一个 agent 并读它的事件"。

## 两个协议与 LangGraph 流式的关系

回顾第 28、29 课：Deep Agents 的底层能力是 **LangGraph 流式 + `stream.subagents` 投影**。

<div class="flow">
  <div class="node"><span class="k">LangGraph 流式</span><span class="v">底层机制</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">stream.subagents</span><span class="v">Deep Agents 的语义投影</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">AG-UI / ACP</span><span class="v">对外协议</span></div>
</div>

**注意这个分层**：协议是**最外面**的一层，它不改变内部机制。
换句话说：

!!! tip "换协议不用改 agent"
    你的 agent 逻辑、middleware 栈、subagent 配置都不需要为了接 AG-UI 而改动。
    协议只是在最外层把已有的事件流翻译成另一种格式。

    这也是"关注点分离"在 harness 里的又一次体现（和第 27 课 profile 的思路一致）。

## 生产上的位置

回到第 39 课的生产清单：官方提到 LangSmith Deployment
**可以把 agent 通过 MCP 或 A2A 暴露出去**。

所以"对外接口"其实有四个候选：

| 协议 | 面向 | 典型消费方 |
| - | - | - |
| **MCP** | 工具/能力暴露 | 其他 agent、MCP 客户端 |
| **A2A** | agent 间通信 | 其他 agent 系统 |
| **ACP** | 编辑器 | Zed、Toad 等 |
| **AG-UI** | 前端 UI | Web / App |

!!! key "四个方向，一个原则"
    **它们都是把"你的 agent 已经具备的能力"翻译成某种标准接口。**

    它们不改能力，只改**谁能用、以什么方式用**。
    所以选择哪个协议是一个**分发问题**，不是架构问题。

```quiz
Q: ACP 与 AG-UI 分别面向什么消费方？
- 两者都面向 Web 前端，只是协议版本不同
- ACP 面向 agent 间通信，AG-UI 面向工具暴露
* ACP 面向编辑器与 IDE，AG-UI 面向交互式前端
- ACP 面向 MCP 客户端，AG-UI 面向 A2A 服务
E: ACP（Agent Client Protocol）用于把 agent 接入编辑器类客户端（如 Zed、Toad）；AG-UI（Agent User Interaction Protocol）用于把 agent 事件流交给前端渲染。

Q: 接入 AG-UI 需要修改 agent 的内部逻辑吗？
- 需要，必须为每个 subagent 注册 UI 组件
- 需要，必须替换 middleware 栈
* 不需要，协议层只翻译已有的事件流
- 需要，必须改用 LangGraph 之外的另一套运行时
E: 协议处于最外层。底层是 LangGraph 流式机制与 Deep Agents 的 subagent 投影，协议只是把已有事件流翻译成另一种格式，不改变内部机制。

Q: AG-UI 的 Programmatic API 章节说明了什么？
- 前端组件必须使用特定框架
- 只有浏览器能消费 AG-UI 事件
* 消费方不只是人，脚本与自动化流程也可以驱动 agent 并读取事件
- 事件流必须经过人工审核才能消费
E: 除了事件流与前端连接，官方还提供 Programmatic API，说明存在非 UI 的消费方式，例如 CI 流程或批处理脚本。

Q: 把 MCP、A2A、ACP、AG-UI 放在一起看，它们共同的性质是什么？
- 它们都会改变 agent 的推理能力
- 它们都是 Deep Agents 独有的专有协议
* 它们都是把已有能力翻译成标准接口的分发层
- 它们都只能用于生产环境
E: 四个协议都不改变 agent 的能力，只改变"谁能用、以何种方式用"，因此选择协议是分发问题而非架构问题。
```

## 全课程结束

到这里，官方文档左侧导航的全部页面都覆盖了。

如果只能带走一句话：

!!! note "整个 harness 的一句话"
    **Deep Agents 给模型加了三样东西——一双能操作文件系统的手（执行环境）、
    一套能管理上下文的记忆系统（压缩与隔离）、以及一组能约束它行为的边界（权限与中断）。
    剩下的所有章节，都是这三样东西在不同场景下的组合。**

    现在回到任意一课，你应该都能指出它落在哪一样里。
