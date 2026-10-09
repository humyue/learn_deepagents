---
num: 17
slug: state-and-runtime-context
title: State Schema 与 Runtime Context
module: W3
tier: A
minutes: 12
desc: 可变状态与不可变输入 —— 两个容易搞混的概念，决定你 middleware 怎么写
lede: 这是写自定义 middleware 前的必修课。两者都是"传给 agent 的数据"，但一个是<b>可变的、会被 checkpoint 的图状态</b>，另一个是<b>每次调用的不可变输入</b>。搞混了，你会写出莫名其妙的并发 bug。
source: https://docs.langchain.com/oss/python/deepagents/context-engineering
source_title: Context engineering · Runtime context / Custom state schema（官方）
---

## 一句话区分

<div class="compare">
<div class="yes">
<h4>state_schema（可变状态）</h4>
<ul>
<li>属于 agent 的图状态，<b>会随 thread 被 checkpoint</b></li>
<li>通过 <code>runtime.state</code> 读写</li>
<li>工具写入，middleware 能读到，反之亦然</li>
<li>适合：计数器、累积值、标志位</li>
</ul>
</div>
<div class="no">
<h4>context_schema（不可变输入）</h4>
<ul>
<li>每次调用传入的静态配置</li>
<li>通过 <code>runtime.context</code> 读取</li>
<li><b>会传播到 subagent</b></li>
<li>适合：user ID、凭据、feature flag</li>
</ul>
</div>
</div>

官方给的判据很干脆：

!!! key "选择标准"
    用 `state_schema`，当数据**必须是 agent 可变图状态的一部分**、
    会被 thread checkpoint、或需要能通过 `runtime.state` 访问。

    对**不可变的、每次运行的输入**（如用户 ID、凭据、feature flag），
    优先用 **runtime context**。

## 自定义 state schema

```python
from deepagents import DeepAgentState, create_deep_agent
from langchain.tools import ToolRuntime, tool

class ResearchState(DeepAgentState):
    page_url: str
    file_urls: list[str]

@tool
def cite_page(runtime: ToolRuntime) -> str:
    """Return the current page URL."""
    return runtime.state["page_url"]

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[cite_page],
    state_schema=ResearchState,
)

result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Cite the current page"}],
        "page_url": "https://example.com/report",   # 初始值在 invoke 时播种
        "file_urls": [],
    },
)
```

!!! trap "必须继承 DeepAgentState，不能随便定义"
    官方明确要求：自定义 state schema **必须继承 `DeepAgentState`**。

    原因是它保留了 `messages` 上内建的 **`DeltaChannel` reducer**——
    这个 reducer 保证 checkpoint 的增长随对话长度是**线性**的。
    如果你绕过它，长对话的 checkpoint 会以更差的方式膨胀。

    `DeltaChannel` 这个名字值得记住：**它意味着"消息历史按增量存，而不是每次全量重存"。**

## 它能解决什么问题

官方列的四类用途，每一类都对应一种真实需求：

| 用途 | 例子 |
| - | - |
| 跨整个运行跟踪状态 | 计数器、标志位、累积值——要活过多次模型与工具调用 |
| 在工具与 middleware 之间共享数据 | 工具写入、middleware 读（或反之） |
| 实现横切关注点 | 限流、用量统计、审计日志——不改核心逻辑 |
| 在调用时播种初始值 | 每次运行开始时塞入字段，运行中由 agent 更新 |

!!! tip "横切关注点这条最实用"
    想给 agent 加"这次运行最多调用 20 次工具"这种限制，
    朴素做法是改 agent 逻辑；
    正确做法是写一个 middleware，把计数放进 state，在钩子里判断。
    **state 是你写 middleware 时的合法副存储。**

## state schema 的继承规则

官方这一段的细节很关键，因为不继承会导致难查的 bug：

| subagent 类型 | 是否继承父级 `state_schema` |
| - | - |
| 声明式 `SubAgent`（dict 定义） | ✅ 继承（由 Deep Agents 为 `task` 工具编译时） |
| `CompiledSubAgent` | ❌ **不继承**（图已经编译好了） |
| 远程 `AsyncSubAgent` | ❌ **不继承**（图单独托管） |

理由很直接：后两者的图**已经存在**，Deep Agents 没办法再往里注入字段。
官方给的补救是：**如果它们需要同样的 state 字段，就得用兼容的 schema 去编译那些图。**

## Context Schema

```python
from dataclasses import dataclass
from langchain.tools import ToolRuntime, tool

@dataclass
class Context:
    user_id: str
    api_key: str

@tool
def fetch_user_data(query: str, runtime: ToolRuntime[Context]) -> str:
    """Fetch data for the current user."""
    return call_api(runtime.context.user_id, runtime.context.api_key, query)

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[fetch_user_data],
    context_schema=Context,
)
```

传入方式是在 `invoke` 时通过 **`context`** 参数：

```python
agent.invoke(
    {"messages": [{"role": "user", "content": "..."}]},
    context=Context(user_id="u_123", api_key="..."),
)
```

官方说明它可以用 `dataclasses.dataclass` 或 `typing.TypedDict` 定义。

!!! key "runtime context 会传播到 subagent"
    这是它和 state 的一个实用差异：
    **你传入的 context 会被 subagent 读到**。
    所以"整个运行都需要的凭据与身份"放这里最合适——
    不用在每个 subagent 的配置里重复传一遍。

## 三者的分工图

<div class="flow col">
  <div class="node"><span class="k">system_prompt</span><span class="v">静态文本，不随调用变化</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">context_schema</span><span class="v">每次调用传入，不可变，传播到 subagent</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">state_schema</span><span class="v">可变，随 thread checkpoint，工具与 middleware 共享</span></div>
</div>

```quiz
Q: 要传"当前用户的 API key 与 feature flag"，官方推荐用哪个？
- state_schema，因为需要在运行中更新
- 直接拼进 system_prompt 字符串
* context_schema，因为它是不可变的每次运行输入
- backend 的 policy hooks，因为它们能拦截每次调用
E: 官方判据是：对不可变的、每次运行的输入（用户 ID、凭据、feature flag）优先用 runtime context。state 用于需要可变、需要 checkpoint 的数据。

Q: 自定义 state schema 为什么必须继承 DeepAgentState？
- 否则无法被 checkpoint 序列化
- 否则 middleware 不能读取它
* 否则会丢掉 messages 上的 DeltaChannel reducer
- 否则无法在 invoke 时播种初始值
E: 官方明确说明：继承 DeepAgentState 可以保留 messages 上内建的 DeltaChannel reducer，它让 checkpoint 的增长随对话变长保持线性。

Q: 哪一类 subagent 不会继承父级的 state_schema？
- 字典形式的声明式 SubAgent
- 自动添加的 general-purpose subagent
* CompiledSubAgent 与远程 AsyncSubAgent
- 所有设置了 skills 的 subagent
E: 声明式 SubAgent 在被编译给 task 工具时继承父级 state_schema；CompiledSubAgent 与远程 AsyncSubAgent 的图已编译或单独托管，因此不继承——需要兼容 schema 就自行编译。

Q: 想把"本次运行最多 20 次工具调用"做成一个可复用能力，正确做法是？
- 在 system_prompt 里写一条约束
- 给每个工具加一层装饰器
* 写一个 middleware，把计数放进自定义 state
- 换一个 context window 更小的模型
E: 官方把"实现横切关注点（限流、用量统计、审计日志）而不修改核心 agent 逻辑"列为自定义 state schema 的用途之一。计数需要跨多次工具调用存活，属于可变图状态的典型场景。
```

## 下一课

上下文模块的最后一课：**非文本内容**。图片、音频、PDF 怎么进出这个以文本为中心的循环。
