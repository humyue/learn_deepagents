---
num: 33
slug: frontend-sandbox
title: 前端模式三：IDE 式的沙箱界面
module: W6
tier: B
minutes: 11
desc: 文件浏览器、实时同步、diff 面板 —— 以及两个平面的联动
lede: 前两个模式消费的是状态。这一个不一样：它要把<b>沙箱里真实发生的文件变化</b>呈现给用户。这需要打通往返两条路——一条把文件放进去，一条把文件取回来。
source: https://docs.langchain.com/oss/python/deepagents/frontend/sandbox
source_title: Frontend · Sandbox（官方）
---

## 目标形态

官方对这个模式的定位是 **IDE-like UI**：

| 面板 | 作用 |
| - | - |
| **文件浏览器** | 看沙箱里有什么 |
| **代码查看器** | 看某个文件的内容 |
| **diff 面板** | 看 agent 改了什么 |

这正好对应第 09 课讲的**两个平面**：模型平面（agent 用工具改文件）和
控制平面（你的程序用 SDK 上传下载）。前端要同时用到两条。

## 一个容易卡住的地方：沙箱怎么被找到

这是官方专门用一节讲的问题：**"Resolve the sandbox from thread metadata"**。

<div class="flow col">
  <div class="node"><span class="k">用户刷新页面 / 换了另一个 API 实例</span><span class="v">沙箱对象不在内存里了</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">从 thread metadata 解析出沙箱</span><span class="v">而不是靠内存里的引用</span></div>
</div>

!!! warning "沙箱不是"前端的一个对象"，它是"thread 的一个属性""
    这个观念转变很重要。因为沙箱是 thread-scoped 的（第 09 课），
    **正确的获取方式是从 thread metadata 里解析**，
    而不是在前端进程里长期持有一个句柄。

    这样做的好处：刷新页面、重启服务、甚至换一个实例，只要 thread 还在，
    就还能找到同一个沙箱。

## 生命周期与两条路

官方把沙箱生命周期和"连接 agent 与 API server"分开讲，说明它们是两件事：

<div class="flow">
  <div class="node"><span class="k">Agent</span><span class="v">在沙箱里读写文件</span></div>
  <div class="arrow">↔</div>
  <div class="node hi"><span class="k">沙箱</span><span class="v">真实的环境</span></div>
  <div class="arrow">↔</div>
  <div class="node"><span class="k">API server</span><span class="v">提供文件浏览接口</span></div>
  <div class="arrow">↔</div>
  <div class="node dim"><span class="k">前端</span><span class="v">渲染浏览器与 diff</span></div>
</div>

### 播种项目文件（seeding）

任务开始前，用控制平面把初始文件放进沙箱。
官方的模式名就叫 **"Seed project files"**。

**为什么必须播种？** 因为沙箱是空的、隔离的。
agent 需要看到项目文件才能改它。

!!! trap "沙箱里的路径 vs 宿主机的路径"
    这是一个高频困惑点：**你在宿主机上读不到 agent 在沙箱里写的文件。**
    agent 说"我已经把报告写到 `/workspace/report.md`"——
    那个路径在沙箱里。要在宿主机上拿到它，必须走**取回产物（retrieving artifacts）**
    那条控制平面路径。

    前端的文件浏览器之所以需要一个 API server，根本原因就在这里。

## API server

官方给的实现路径是：

1. **创建 API server**：提供文件列表、读取、下载等接口
2. **配置 `langgraph.json`**：把它注册进部署

```python
# src/api/server.py —— 提供文件浏览 API
```

这个 API server 的职责是把**控制平面**的能力（provider SDK 的文件操作）
暴露成 HTTP 接口给前端。

!!! note "为什么要单独加一层 API server"
    因为浏览器不能直接和沙箱 provider 说话——
    它没有凭据，也不该有。API server 是那个"持有凭据、做权限检查"的中间人。

    这也意味着：**文件浏览 API 的权限检查是你的责任**，
    agent 侧的 `permissions`（第 08 课）管不到它。

## 前端要做的四件事

官方把前端工作拆成四块：

| 任务 | 说明 |
| - | - |
| **Thread creation** | 建 thread，并让沙箱与它绑定 |
| **File state management** | 维护"当前有哪些文件、内容是什么" |
| **Real-time file sync** | 让文件变化实时反映到 UI |
| **Detecting changed files** | 判断哪些文件被改过 |

### 实时文件同步

这是最有意思的一块。两个可能的策略：

<div class="compare">
<div class="yes">
<h4>轮询</h4>
<ul>
<li>实现简单</li>
<li>延迟取决于间隔</li>
<li>长任务里会做很多无用请求</li>
</ul>
</div>
<div class="no">
<h4>基于流的触发</h4>
<ul>
<li>工具调用发生时同步</li>
<li>延迟低</li>
<li>需要关联工具事件与文件</li>
</ul>
</div>
</div>

官方给的实现涵盖 "Real-time file sync" 与 "Detecting changed files" 两节，
思路是把**工具调用事件**（谁在什么时候写了哪个文件）与文件快照结合起来。

!!! tip "一个实用的设计判断"
    **agent 的 `write_file` / `edit_file` 工具调用本身就是"文件可能变了"的信号。**
    你不需要一个文件系统 watcher——流里已经告诉你了。

    这也解释了为什么 `edit_file` 的"精确字符串替换"语义对 diff 很友好：
    **替换的 before/after 就在工具参数里，diff 几乎是白送的。**

### 显示 diff

官方有一节 "Displaying diffs" 和 "Changed files summary"。

| 层次 | 内容 |
| - | - |
| 单文件 diff | 这个文件改了什么 |
| 变更摘要（changed files summary） | 这次任务总共动了哪些文件 |

**变更摘要**在生产里比单文件 diff 更重要：一个跑了十分钟的任务改了 30 个文件，
用户需要先看一份"总账"，再决定要不要下钻。

## 最佳实践

官方给了专门的 best practices 一节，核心关切可以归成三类：

| 关切 | 建议方向 |
| - | - |
| **安全** | 文件浏览 API 要有自己的权限检查；不要暴露沙箱凭据给浏览器 |
| **性能** | 大文件分页读；变更摘要先于全量 diff |
| **一致性** | 前端缓存与沙箱真实状态可能不一致，要有刷新/校验路径 |

!!! warning "别把沙箱当前端的状态源"
    前端维护的是一份**缓存**，沙箱才是真相。
    长任务里 agent 可能改了很多次同一个文件，
    缓存很容易落后。设计时要想清楚"什么时候强制重新拉取"。

## 三课串起来

<div class="flow col">
  <div class="node"><span class="k">Todo List</span><span class="v">消费 agent state → 进度</span></div>
  <div class="node"><span class="k">Subagent Card</span><span class="v">消费 subagent 投影 → 工作者视图</span></div>
  <div class="node hi"><span class="k">Sandbox IDE</span><span class="v">消费控制平面 + 工具事件 → 真实文件与 diff</span></div>
</div>

共同点：**三者都不需要解析自然语言。**
前两个消费结构化状态，第三个消费工具调用事件与真实文件。

```quiz
Q: 前端沙箱界面为什么需要一个单独的 API server？
- 因为沙箱提供商会主动推送文件变化
- 因为 LangGraph 不允许前端访问沙箱
* 因为浏览器没有沙箱凭据，需要一个持有凭据并做权限检查的中间人
- 因为沙箱的文件格式与浏览器不兼容
E: 浏览器不能也不该持有沙箱 provider 凭据。API server 是持有凭据、做权限校验并把控制平面能力暴露为 HTTP 接口的中间层。

Q: 沙箱在刷新页面后应该怎么被找到？
- 由前端在内存中缓存的句柄恢复
- 重新创建一个新的沙箱
* 从 thread metadata 中解析出来
- 由 agent 通过工具调用返回
E: 官方专门讲了 Resolve the sandbox from thread metadata。因为沙箱是 thread-scoped 的，从 thread metadata 解析可以跨越页面刷新与实例重启。

Q: 判断"agent 改了哪些文件"，最直接的信号来源是什么？
- 文件系统 watcher 的变更事件
* 流里的 write_file 与 edit_file 工具调用
- 定时轮的目录哈希比较
- 沙箱 provider 的审计日志
E: 工具调用事件本身就是"文件可能变了"的信号，且 edit_file 的精确替换语义让 before/after 直接出现在参数里，diff 几乎可以直接构造。

Q: 一个跑了十分钟、修改了 30 个文件的任务，前端应该优先展示什么？
- 全部 30 个文件的完整 diff
* 变更摘要，再让用户按需下钻单个 diff
- 只展示最后一个被修改的文件
- 只有用户主动点击时才拉取任何文件信息
E: 官方把 changed files summary 作为独立一节，说明总账先于细节：用户需要先看清整体改动范围，再决定下钻哪个文件。
```

## 模块 F 结束

到这里，"看得见"讲完了。最后一个模块回到地面：
**官方给的四个成品模式，以及把它们送进生产要补的课。**
