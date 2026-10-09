---
num: 28
slug: streaming
title: 流式：把一棵树投影成几条流
module: W6
tier: B
minutes: 11
desc: stream_mode、subgraphs、namespace —— 委派之后为什么简单的流不够用了
lede: 一个单 agent 的执行是一条线，流式很简单。但一旦有了 subagent，执行就变成了一棵<b>树</b>。这一课讲 LangGraph 的流式机制如何应对这个变化，以及为什么需要"命名空间"。
source: https://docs.langchain.com/oss/python/deepagents/streaming
source_title: Streaming（官方）
---

## 问题：执行是树，流是一维的

<div class="flow col">
  <div class="node"><span class="k">主 agent</span><span class="v">想 → 调工具 → 再想 → 派子任务</span></div>
  <div class="arrow">↓ 分叉</div>
  <div class="node"><span class="k">subagent A</span><span class="v">自己的模型调用、工具调用、甚至更深的分叉</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">subagent B</span><span class="v">同上</span></div>
</div>

如果所有事件都平铺进一条流，你会看到：

<div class="flow">
  <div class="node dim"><span class="k">token</span><span class="v">这是谁生成的？</span></div>
  <div class="arrow">·</div>
  <div class="node dim"><span class="k">tool_call</span><span class="v">属于父还是子？</span></div>
  <div class="arrow">·</div>
  <div class="node dim"><span class="k">values</span><span class="v">是哪个子图的状态？</span></div>
</div>

**"这是谁的"这个问题，就是这一课的全部主题。**

## 第一层：开启 subgraph 流式

要看到 subagent 内部的步骤，需要显式开启子图流式：

```python
for chunk in agent.stream(
    {"messages": [...]},
    stream_mode="updates",
    subgraphs=True,          # ← 关键
):
    namespace, update = chunk
    ...
```

开启后，每个 chunk 会带一个 **namespace**（命名空间）来标识它来自树的哪个位置。

## 第二层：命名空间

<div class="stack">
  <div class="layer req"><span class="idx">()</span><span class="nm">根命名空间</span><span class="ds">主 agent 的事件</span></div>
  <div class="layer req"><span class="idx">(tools:...)</span><span class="nm">工具节点</span><span class="ds">主 agent 的工具执行</span></div>
  <div class="layer req"><span class="idx">(tools:...:task:...)</span><span class="nm">嵌套一层</span><span class="ds">subagent 内部的事件</span></div>
</div>

!!! key "namespace 就是路径"
    它的形状和文件路径一样：**越深的前缀 = 越深的委派层级。**

    这让你能做一件关键的事：**把事件按来源分流**。
    比如"只显示主 agent 的 token 给用户看，subagent 的 token 只记日志"。

## 第三层：多种 stream_mode

| 模式 | 给什么 |
| - | - |
| `"values"` | 每一步之后的完整状态 |
| `"updates"` | 每一步的状态**增量** |
| `"messages"` | 逐 token 的 LLM 输出（带 metadata） |
| `"custom"` | 你从工具或节点里主动发出的自定义更新 |
| `"debug"` | 内部节点的详细步骤（调试用） |

官方给了一组过滤内部噪音的写法：

```python
# 跳过内部 middleware 步骤，只看有意义的节点名
for chunk in agent.stream(input, stream_mode="debug"):
    if chunk["name"] in {"model", "tools"}:
        ...
```

!!! tip "`"messages"` 模式的 metadata 很有用"
    第 15 课里用过一次：摘要步骤的 token 会混进流里，
    靠 `metadata.get("lc_source") == "summarization"` 过滤掉。

    同样的手段还能识别**哪条流来自哪个 subagent**——metadata 里有 agent 标识。

## 常见模式

官方列了几个高频用法：

### 跟踪 subagent 生命周期

只想知道"哪些子任务开始了、哪些结束了"——这是最轻量的用法（下一课有专门的投影接口）。

### 处理 human-in-the-loop 中断

流式下中断会作为事件出现，而不是从 `invoke` 返回值里读（第 25 课）。
你的 UI 要能在这个事件上停下并渲染"等待批准"。

### 自定义更新

`stream_mode="custom"` 让工具/节点主动往外发东西。
适合"我正在下载第 3 个文件"这类**框架不知道、但用户想知道**的进度。

## 流 chunk 的形状

官方专门给了一节说明不同参数组合下 chunk 的形状差异：

| 组合 | chunk 形状 |
| - | - |
| 单一 mode + subgraphs | `(namespace, data)` |
| 多个 mode + subgraphs | `(namespace, mode, data)` |

!!! trap "开了 subgraphs 之后解包方式会变"
    这是升级时最常踩的坑：原本 `for chunk in ...` 直接拿到数据，
    加上 `subgraphs=True` 之后要先解包 namespace。
    **所以类型提示和下游渲染逻辑都要跟着改。**

```quiz
Q: 开启 subgraphs=True 之后，每个 chunk 多带了什么信息？
- 一个 token 计数
- 一个模型标识
* 一个 namespace，标识事件来自树的哪个位置
- 一个中断状态标志
E: namespace 是路径式的，越深的前缀代表越深的委派层级，用来区分事件属于主 agent 还是某个 subagent。

Q: 为什么在流式里需要 namespace？
- 因为 LangGraph 无法并行处理多个流
- 因为模型输出的 token 需要排序
* 因为执行是一棵树，必须区分"这个事件是谁产生的"
- 因为 namespace 用来加密传输内容
E: 一旦有 subagent 嵌套，事件会混合在一条流里。namespace 提供来源标识，让下游可以按来源分流、过滤或渲染。

Q: 想过滤掉摘要步骤产生的 token，官方给的依据是什么？
- chunk 的 namespace 前缀
- stream_mode 的取值
* metadata 里的 lc_source 等于 summarization
- chunk 的 name 字段等于 summarize
E: 官方示例用 metadata.get("lc_source") == "summarization" 来跳过摘要生成的 token。这是在 messages 模式下按 metadata 过滤。

Q: 开启 subgraphs 之后最容易出错的地方是？
- 模型选择不再生效
- 工具调用的结果不再返回
* chunk 的解包形状变了，需要先取出 namespace
- stream_mode 只能取单一值
E: 官方说明单一 mode 加 subgraphs 时 chunk 是 (namespace, data)，多个 mode 时是 (namespace, mode, data)。下游解包与渲染逻辑必须相应调整。
```

## 下一课

通用流式是"看得见"。但 Deep Agents 加了一层专门的投影：
**`stream.subagents`**——每个委派任务一个独立的句柄。
