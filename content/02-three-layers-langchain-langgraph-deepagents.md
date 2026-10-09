---
num: 2
slug: three-layers-langchain-langgraph-deepagents
title: 三层分工：LangChain / LangGraph / Deep Agents
module: W1
tier: A
minutes: 9
desc: framework、runtime、harness —— 谁负责什么，边界在哪里
lede: 官方文档里这三个名字经常混着出现。分不清它们，你就无法判断"这个问题该去哪一层解决"。这一课把它们钉死在各自的位置上。
source: https://docs.langchain.com/oss/python/concepts/products
source_title: Concepts · Frameworks, runtimes, and harnesses（官方）
---

## 一句话分工

<div class="stack">
  <div class="layer req"><span class="idx">3</span><span class="nm">Deep Agents</span><span class="ds">harness —— 预装好的能力包：文件系统、subagent、记忆、压缩</span></div>
  <div class="layer req"><span class="idx">2</span><span class="nm">LangGraph</span><span class="ds">runtime —— 图的执行引擎：持久化、中断、流式、durable execution</span></div>
  <div class="layer req"><span class="idx">1</span><span class="nm">LangChain</span><span class="ds">framework —— 积木：模型、工具、消息、middleware 抽象</span></div>
</div>

层级是**依赖关系**，不是替代关系。`deepagents` 依赖 LangChain 的 middleware 抽象，
又跑在 LangGraph 的 runtime 上。所以：

!!! key "定位问题时的第一句话"
    **"这是不是一次模型调用/一次工具调用？"** → 是，就去 LangChain 找答案。
    **"这是不是关于状态、恢复、中断、流式的问题？"** → 去 LangGraph。
    **"这是不是关于上下文太长、要并行、要记忆的问题？"** → 才是 Deep Agents 的领域。

## 每一层到底提供什么

### LangChain：可替换的积木

LangChain 提供的是**抽象**，不是行为：

- **Chat models**：统一各家的模型接口，`init_chat_model("gpt-5.5")` 和 `ChatOpenAI(...)` 用法一致。
- **Tools**：`@tool` 装饰器把一个 Python 函数变成模型能调用的工具，schema 从类型注解和 docstring 推导。
- **Messages**：`HumanMessage` / `AIMessage` / `ToolMessage`，统一的消息模型。
- **Middleware**：把"模型调用前后要插一段逻辑"这件事变成标准接口。
- **`create_agent`**：用这些积木拼出一个普通 agent。

```python
# LangChain 层：你在这里定义"积木"
from langchain.tools import tool

@tool
def internet_search(query: str, max_results: int = 5) -> dict:
    """Run a web search."""
    return tavily_client.search(query, max_results=max_results)
```

### LangGraph：真正跑循环的引擎

LangGraph 是**运行时**。Deep Agents 编译出来的对象，
类型是 `CompiledStateGraph`——它是一个 LangGraph 图：

```python
# create_deep_agent 的返回类型（官方签名）
-> CompiledStateGraph[AgentState[ResponseT], ContextT, InputAgentState, OutputAgentState[ResponseT]]
```

这一层负责的事情，你在 harness 文档里几乎看不到，但它们决定了很多上限：

| LangGraph 提供 | 在 Deep Agents 里表现为 |
| - | - |
| Checkpointer（检查点） | thread 内的短期记忆；`thread_id` 必须一致才能续上状态 |
| Store（跨 thread 存储） | 长期记忆的底座，`StoreBackend` 就建在它上面 |
| Interrupt（中断） | `interrupt_on` 的实现基础，人工批准后才能继续 |
| Durable execution | 长任务可恢复；`PatchToolCallsMiddleware` 专门修补中断留下的悬空 tool call |
| Streaming | 所有 `stream_events` / `astream` 的来源 |

!!! trap "最常见的误判"
    很多人把"为什么我的 agent 重启后忘了之前的对话"当成 Deep Agents 的 bug。
    这是一个 **LangGraph checkpointer** 的问题：没有传 `checkpointer`，
    或者每次调用的 `thread_id` 不一样。
    —— 定位错误发生在了错误的层，就会修错地方。

### Deep Agents：预装的能力包

Deep Agents 做的事情只有一件：**把一组 middleware 按固定顺序装配好**，
再给你一个虚拟文件系统。第 04 课会把装配顺序逐条列出来。

## 一张对照表

<div class="compare">
<div class="yes">
<h4>用 Deep Agents，当……</h4>
<ul>
<li>任务是多步的、长的，上下文会爆</li>
<li>需要并行探索多个方向</li>
<li>需要跨会话记住用户偏好</li>
<li>需要真的读写文件、跑代码</li>
<li>需要人工在关键点上把关</li>
</ul>
</div>
<div class="no">
<h4>不用 Deep Agents，当……</h4>
<ul>
<li>任务是一两步就结束的问答</li>
<li>工具调用是确定性的固定流程</li>
<li>上下文永远够用（小输入小输出）</li>
<li>你需要精确控制图的每一个节点</li>
<li>你不希望模型自主决定要不要开子任务</li>
</ul>
</div>
</div>

后面两种情况，官方给的替代方案很明确：
用 LangChain 的 [`create_agent`](https://docs.langchain.com/oss/python/langchain/agents)，
或者直接手写一个 [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) 工作流。

!!! tip "成本视角"
    harness 每一项能力都有代价：更多的 middleware 意味着**更多的 token 花在系统提示和工具 schema 上**，
    更多的委派意味着**更多的模型调用**。
    对简单任务，harness 是纯粹的浪费。这是第 04 课之后你会反复看到的一条主线。

```quiz
Q: "我传了 checkpointer 但 agent 还是忘了上下文"，这个问题属于哪一层？
- LangChain 的工具 schema 定义层
* LangGraph 的运行时状态与检查点层
- Deep Agents 的 middleware 装配层
- 模型提供商的 token 计费与限流层
E: 会话历史存在 LangGraph 的 checkpoint 里，按 thread_id 索引。忘了上下文通常是 thread_id 不一致或没挂 checkpointer，属于 runtime 层的问题。

Q: 下面哪一项最贴切地描述了 Deep Agents 这一层做的事？
- 提供统一的模型与消息抽象
- 提供图执行、持久化与流式能力
* 按固定顺序装配一组内建 middleware 与虚拟文件系统
- 提供把函数变成工具所需的 schema 推导
E: 模型与消息抽象、工具 schema 推导属于 LangChain；图执行与持久化属于 LangGraph。Deep Agents 的新增价值就是"预装装配"。

Q: 若你的任务只有一次工具调用、输入输出都很小，官方推荐的替代是什么？
- 继续用 Deep Agents 但关闭所有 middleware
- 把 middleware 全部替换成自定义实现
* 用 LangChain 的 create_agent 或手写 LangGraph 工作流
- 换一个上下文窗口更大的模型即可
E: 官方明确说明：不需要这些内建能力时，考虑用 create_agent 或直接构建自定义 LangGraph 工作流。harness 的开销在简单任务上是净损失。

Q: deepagents 编译出来的对象类型说明了什么？
- 它是一份与 LangGraph 无关的独立实现
- 它是一个普通的 Python 函数包装器
* 它是一张 LangGraph 图，因此继承 runtime 的全部能力
- 它是一个纯文本提示词模板集合
E: 返回类型是 CompiledStateGraph。这直接解释了为什么中断、检查点、流式这些能力"免费"出现在 Deep Agents 里——它们是 runtime 自带并被 harness 用上了。
```

## 下一课

地图有了，接下来打开那个黑盒：
**一次 `create_deep_agent()` 调用，究竟在你没看见的地方做了什么？**
