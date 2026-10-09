---
num: 11
slug: four-context-layers
title: 上下文的四个层次
module: W3
tier: A
minutes: 12
desc: 输入、压缩、隔离、长期记忆 —— harness 存在的真正理由
lede: 如果把 harness 的全部工作压缩成一句话，那就是：<b>在有限的上下文窗口里，让 agent 完成无限长的任务。</b>这一课给这个问题的四个解法各归其位。
source: https://docs.langchain.com/oss/python/deepagents/context-engineering
source_title: Context engineering（官方）
---

## 问题的本质

上下文窗口是一个**固定容量的工作记忆**。而 agent 任务的特点恰恰是：

- 工具结果大小**不可预测**（一次搜索可能是 2KB，也可能是 2MB）
- 任务长度**不可预测**（可能是 3 轮，也可能是 300 轮）
- 有用的信息**散布在中间过程里**（哪个文件读过、哪个 URL 失败了）

朴素循环的应对方式是"祈祷窗口够大"。harness 的应对方式是**四套机制分工**。

## 四层结构

官方把它拆成四类"你可以控制什么"：

| 层次 | 你控制什么 | 作用域 | 何时生效 |
| - | - | - | - |
| **Input context** | 启动时进 prompt 的东西：system prompt、memory、skills | 静态，每次运行都应用 | 启动 |
| **Runtime context** | 调用时传入的静态配置：用户元数据、API key、连接 | 每次运行，**会传播到 subagent** | 调用时 |
| **Context compression** | 内建的 offloading 与 summarization | 自动，接近上限时 | 运行时 |
| **Context isolation** | 用 subagent 把重活隔离出去，只收回结果 | 每个 subagent | 委派时 |
| **Long-term memory** | 虚拟文件系统里的跨 thread 持久存储 | 跨会话持久 | 跨 thread |

注意第三行和第五行是一对：**压缩是在同一个窗口里省空间，隔离是干脆换个窗口。**

<div class="flow col">
  <div class="node hi"><span class="k">1 · 输入上下文</span><span class="v">控制"开局手里有什么"：prompt / memory / skills / 工具说明</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">2 · 压缩</span><span class="v">控制"运行中怎么不爆"：offloading + summarization</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">3 · 隔离</span><span class="v">控制"重活去哪儿做"：subagent 带回结果不带回过程</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">4 · 长期记忆</span><span class="v">控制"关掉之后留下什么"：文件系统里的跨会话状态</span></div>
</div>

## 官方给的四段式摘要

Deep Agents 文档对这个 flow 的描述是：

- **Input context**：system prompt、memory、skills、tool prompts 决定 agent 的起点。
- **Compression**：内建的 offloading 与 summarization 压缩历史与大中间结果。
- **Isolation**：subagent 隔离重任务，只返回最终结果。
- **Long-term memory**：虚拟文件系统里的持久存储把信息带过 thread。

!!! key "一串起来就是一句话"
    **起点要精简（输入）→ 过程中要能丢（压缩）→ 重活要外包（隔离）→ 结论要留存（记忆）。**

    这四件事恰好对应一个人做长期项目时的四种行为：
    带必要的资料上桌、把草稿扔进抽屉、把某个子课题交给同事、把结论写进笔记。

## 为什么这四层必须都有

拿掉任何一层，都会出现一个具体的失败：

| 拿掉 | 立刻出现的症状 |
| - | - |
| 输入上下文 | agent 不知道项目约定，每轮都要重新解释 |
| 压缩 | 第 30 轮报 `ContextOverflowError` |
| 隔离 | 主 agent 的窗口被"查资料"的过程塞满，没空间做综合判断 |
| 长期记忆 | 用户每开一个新会话都要重复一遍偏好 |

!!! note "压缩是自动的，不需要你配"
    官方特别说明：**每一次 `create_deep_agent` 调用都自带内建压缩**，
    不需要为了 offloading 或 summarization 额外加 middleware。
    这是第 03 课"出厂配件"的又一项——只是它藏在 middleware 栈里，不容易被注意到。

## 一个值得内化的判断

遇到"我的 agent 效果不好"时，先问一句：**这四层哪一层出了问题？**

<div class="flow">
  <div class="node"><span class="k">它忘了约定</span><span class="v">→ 输入上下文 / memory</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">它中途跑偏</span><span class="v">→ 压缩把关键信息压掉了</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">它答得很浅</span><span class="v">→ 该隔离的活没外包</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">它每次都要重说</span><span class="v">→ 长期记忆没接上</span></div>
</div>

```quiz
Q: 下列哪一组对应"压缩"与"隔离"的核心差别？
- 一个省 token，一个省模型调用
- 一个作用于工具结果，一个作用于 system prompt
* 一个在同一个窗口里省空间，一个换一个窗口干活
- 一个自动生效，一个必须手动触发
E: 压缩（offloading + summarization）是把同一份上下文变小；隔离（subagent）是把工作搬到另一个独立的上下文窗口，只把结果带回来。

Q: 关于内建的上下文压缩，官方的说法是什么？
- 需要显式添加 SummarizationMiddleware 才能生效
- 只在 Anthropic 与 Bedrock 模型上生效
* 每次 create_deep_agent 调用都自带，无需额外配置
- 仅在开启 write_todos 之后才会触发
E: 官方明确写明 "Every create_deep_agent call includes built-in context compression"，不需要为 offloading 或 summarization 添加 middleware。

Q: Runtime context 与 input context 的关键区别是？
- 一个是文本，一个是结构化数据
- 一个加密，一个不加密
* 一个每次运行传入并可传播到 subagent，一个是启动时的静态输入
- 一个只对主 agent 有效，一个只对 subagent 有效
E: Input context 是启动时就进 prompt 的静态内容（system prompt / memory / skills）；runtime context 是调用时传入的配置（用户元数据、API key、feature flag），并且会传播到 subagent。
```

## 下一课

从第一层开始拆：**输入上下文**。这是唯一你能直接编辑的一层，
也是唯一"写错了会一直错下去"的一层。
