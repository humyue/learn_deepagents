---
num: 6
slug: virtual-filesystem
title: 虚拟文件系统：harness 的地基
module: W2
tier: A
minutes: 13
desc: 为什么 offloading、skills、memory、代码执行都建在同一层抽象上
lede: 如果只能记住 Deep Agents 的一个设计决策，就记这个：它给了 agent 一个<b>虚拟文件系统</b>。这不是"顺便加了文件读写"，而是整个 harness 的承重墙。
source: https://docs.langchain.com/oss/python/deepagents/overview#virtual-filesystem-access
source_title: Overview · Virtual filesystem access（官方）
---

## 一个反直觉的观察

朴素循环里，工具结果是**只能进不能出**的：一旦 `ToolMessage` 进了消息历史，
它就永远占着上下文窗口，直到整个对话结束。

而 harness 做的事情，本质上是给 agent 加了一个**可以主动往外搬东西的地方**：

<div class="flow">
  <div class="node"><span class="k">工具返回 200KB</span><span class="v">JSON / 网页 / 日志</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">写进虚拟文件系统</span><span class="v">write_file</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">上下文里只留</span><span class="v">路径 + 前 10 行预览</span></div>
  <div class="arrow">→</div>
  <div class="node dim"><span class="k">需要时再取回</span><span class="v">read_file / grep</span></div>
</div>

**"文件系统"在这里不是存储，是上下文管理的一种手段。**
官方原话把它的地位说得很清楚：

!!! note "官方原话"
    The virtual filesystem is used by several other harness capabilities such as
    **skills, memory, code execution, and context management**.

    也就是说，它不是一个功能，而是**多个功能的共同底座**。

## 八个文件操作

| 工具 | 语义 | 值得注意的细节 |
| - | - | - |
| `ls` | 列目录 | 返回 metadata（size、modified time） |
| `read_file` | 读内容 | 带行号；支持 `offset`/`limit` 分段读大文件；非文本文件返回**多模态内容块** |
| `write_file` | 新建或覆盖 | 覆盖语义，不是追加 |
| `edit_file` | 精确替换 | 支持全局替换模式 |
| `delete` | 删文件 / 递归删目录 | backend 不支持时该工具不会出现在工具列表里 |
| `glob` | 模式匹配找文件 | 如 `**/*.py` |
| `grep` | 搜内容 | 三种输出模式：只给文件名 / 带上下文 / 只给计数 |
| `execute` | 跑 shell | **只有 sandbox 类 backend 才有** |

两个设计细节很值得学：

**其一，`read_file` 支持 offset/limit。** 这意味着"读大文件"不是一次性的原子操作，
可以分页读。这直接支撑了后面 offloading 的恢复路径：
模型可以先 `grep` 定位，再 `read_file` 精确读那一段，而不是把整个文件塞回上下文。

**其二，`grep` 提供三种输出模式。** "只给文件名"和"只给计数"这两种模式存在的唯一理由就是**省 token**。
一个只想知道"哪个文件里有 `TODO`"的任务，不需要看到每一行匹配内容。

## 为什么说它是地基：四条依赖链

<div class="stack">
  <div class="layer req"><span class="idx">↑</span><span class="nm">Context offloading</span><span class="ds">大工具结果写进文件系统，上下文只留引用（第 15 课）</span></div>
  <div class="layer req"><span class="idx">↑</span><span class="nm">Skills</span><span class="ds">技能就是文件系统里的目录，按需 read_file 加载（第 13 课）</span></div>
  <div class="layer req"><span class="idx">↑</span><span class="nm">Memory</span><span class="ds">AGENTS.md 存在 backend 里，agent 用 edit_file 更新（第 14 课）</span></div>
  <div class="layer req"><span class="idx">↑</span><span class="nm">Code execution</span><span class="ds">sandbox backend 在上面加一个 execute 工具（第 09 课）</span></div>
  <div class="layer req"><span class="idx">=</span><span class="nm">Virtual filesystem</span><span class="ds">ls · read_file · write_file · edit_file · delete · glob · grep</span></div>
</div>

试想如果只有"工具调用"没有文件系统：

- **offloading 无从谈起**——没有地方可以卸载
- **skills 只能用"全量塞进 prompt"** 的方式，退化成一个大 system prompt
- **memory 只能存在数据库里**，agent 就无法用"编辑文件"这种它最熟悉的操作来维护记忆
- **代码执行只能返回 stdout 字符串**，无法留下产物文件

!!! key "本课要带走的一句话"
    **给 agent 一个文件系统，等于给了它一个可以自己管理的、容量近乎无限的扩展内存。**
    上下文窗口是它的"工作记忆"，文件系统是它的"笔记本"。
    后面所有聪明的机制，都是"怎么用好这本笔记本"。

## 一个容易混淆的问题：这是本机磁盘吗？

**不是。默认不是。**

虚拟文件系统背后的实现由 `backend` 决定（下一课的主题）：
可以存在图状态里、存在 LangGraph store 里、落在本地磁盘、或者落在隔离沙箱里。
`ls` / `read_file` 这些工具在所有 backend 上**语义一致**——
这正是"可插拔"的价值：换后端不改工具，也不改提示词。

```quiz
Q: 官方把虚拟文件系统描述为下列哪一组的共同底座？
- tools 与 MCP 集成
- 模型选择与 provider profile
* skills、memory、code execution 与 context management
- 流式、中断与检查点
E: 官方原文列举的是 skills、memory、code execution、context management。它们不是各自独立实现，而是共享同一个文件系统抽象。

Q: read_file 支持 offset/limit 与 grep 提供"只给文件名"模式，两者共同的设计意图是？
- 让 agent 能处理二进制文件
- 让文件系统能跨 thread 共享
* 让取回信息的粒度可控，从而节省 token
- 让权限检查更容易实现
E: 这两项都是"按需取用、控制粒度"的体现。offloading 的恢复路径依赖它们：先 grep 定位，再分段 read，而不是整体回灌。

Q: 关于默认虚拟文件系统，哪个判断是错的？
- 它的语义在所有 backend 上保持一致
- 它默认存在图状态里，按 thread 隔离
* 它默认指向本机的真实磁盘目录
- 换 backend 不需要改模型可见的工具
E: 默认是 StateBackend（存在图状态里）。要落到本机磁盘必须显式使用 FilesystemBackend 或 LocalShellBackend。
```

## 下一课

知道了"有文件系统"，接下来最关键的问题是：**文件到底存在哪里？**
六个内建 backend 各自代表一种完全不同的时间与作用域语义。
