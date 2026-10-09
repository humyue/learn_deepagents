---
num: 20
slug: custom-subagents
title: 自定义 Subagent 的字段设计
module: W4
tier: B
minutes: 11
desc: 继承表、description 的重要性、以及 SubAgent 与 CompiledSubAgent 的分界
lede: 定义一个 subagent 是写一个字典。<b>真正的难点不是语法，而是每个字段继承还是不继承。</b>这一课用一张表把继承关系钉死，避免你在调试时怀疑人生。
source: https://docs.langchain.com/oss/python/deepagents/subagents#custom-subagents
source_title: Subagents · Custom subagents（官方）
---

## 最小可用的 subagent

```python
research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "openai:gpt-5.5",     # 可选，默认用主 agent 的模型
}

agent = create_deep_agent(
    model="google_genai:gemini-3.6-flash",
    subagents=[research_subagent],
)
```

三个必填字段：`name`、`description`、`system_prompt`（后者对默认的 `isolated` 模式是必需的）。

## 继承表（最重要的一张表）

这是官方文档里信息密度最高的一张表。**"不继承"的项是坑的高发区**：

| 字段 | 默认行为 | 关键提醒 |
| - | - | - |
| `name` | 必填 | 成为 `AIMessage` 的 metadata 与流式的标签 |
| `description` | 必填 | **主 agent 靠它决定何时委派** |
| `system_prompt` | isolated 模式必填 | **不继承**主 agent；自定义 isolated subagent 必须自己写 |
| `mode` | `"isolated"` | 或 `"fork"`（继承父级对话，见下一课） |
| `tools` | **继承主 agent** | 一旦指定就是**整体覆盖**，不是追加 |
| `model` | **继承主 agent** | 可为不同任务配不同模型 |
| `middleware` | **不继承** | 合入"同步 subagent 栈" |
| `interrupt_on` | **继承主 agent** | subagent 的值覆盖默认 |
| `skills` | **不继承** | 只有 general-purpose subagent 继承主 agent 的 skills |
| `response_format` | 无 | 设置后父 agent 收到的是 JSON 而不是自由文本 |
| `permissions` | **继承主 agent** | 一旦设置就是**整体替换** |

!!! key "三类字段，三种语义"
    - **继承主 agent**：`tools`、`model`、`interrupt_on`、`permissions`
    - **不继承**：`system_prompt`、`middleware`、`skills`
    - **覆盖而非追加**：`tools`、`permissions`

    把这三类分清楚，调试时就不会问"为什么我的 subagent 没有继承那个配置"。

## `description` 是最重要的一个字段

因为**主 agent 靠它决定要不要委派**。官方给的指导是
"Be specific and action-oriented"。

<div class="compare">
<div class="yes">
<h4>好的 description</h4>
<ul>
<li>"Reviews code for security issues, citing lines and severity"</li>
<li>说了做什么 + 产出什么</li>
</ul>
</div>
<div class="no">
<h4>差的 description</h4>
<ul>
<li>"A helpful agent"</li>
<li>没有可匹配的信号</li>
</ul>
</div>
</div>

这和 skills 的 `description` 是同一个道理（第 13 课）：
**在"渐进式披露"的系统里，那一行文字就是全部的检索键。**

## `tools` 要尽量少

官方在最佳实践里专门列了 "Minimize tool sets"，并给了正反例：

```python
# ✅ Good: 聚焦的工具集
tools=[read_file, grep]

# ❌ Bad: 工具太多
tools=[read_file, write_file, edit_file, glob, grep, delete,
       internet_search, fetch_url, run_sql, send_email, ...]
```

理由不是"安全"，而是**准确率**：候选工具越多，选错的概率越高。

## `response_format`：让子任务返回结构化结果

设置之后，父 agent 收到的不是一段自由文本，而是符合 schema 的 JSON。
官方支持的形态：Pydantic 模型、`ToolStrategy(...)`、`ProviderStrategy(...)`、或裸 schema 类型。

!!! tip "这是"单次交接"的强化版"
    subagent 的一个软肋是"返回的是自然语言，父 agent 还得解析"。
    `response_format` 把这个交接点变成**契约**：
    字段名、类型都由你定，父 agent 拿到的是可编程的数据。
    需要"子任务结果要参与后续逻辑判断"时，这是首选。

## 用不同模型跑不同 subagent

```python
subagents = [
    {"name": "cheap-scanner", "description": "...",
     "system_prompt": "...", "model": "openai:gpt-5-mini"},
    {"name": "deep-analyst",  "description": "...",
     "system_prompt": "...", "model": "anthropic:claude-sonnet-5"},
]
```

官方在最佳实践里明确写了 **"Choose models by task"**。
典型分工：扫描/分类用便宜快的，分析/写作用强的。

## `CompiledSubAgent`：预编译的图

当子任务本身就是一个完整的工作流，直接嵌一张已经编译好的 LangGraph 图：

```python
from deepagents import CompiledSubAgent, create_deep_agent
from langchain.agents import create_agent

custom_graph = create_agent(
    model="openai:gpt-5.5",
    tools=specialized_tools,
    system_prompt="You are a specialized agent for data analysis...",
)

subagents = [
    CompiledSubAgent(
        name="data-analyst",
        description="Analyzes datasets and produces reports",
        runnable=custom_graph,          # 必须已经 .compile()
    ),
]
```

| | `SubAgent`（字典） | `CompiledSubAgent` |
| - | - | - |
| 定义方式 | 声明式字段 | 一个编译好的 `Runnable` |
| 灵活性 | 中 | 高（你可以画任意图） |
| 继承父级 `state_schema` | ✅ | ❌ |
| 系统提示 | 由字段给出 | 图自带 |
| 适用 | 绝大多数场景 | 复杂/既有工作流 |

!!! warning "自定义 LangGraph 图必须有个 state key 叫 messages"
    官方明确要求：如果你自己画图，**图里必须有名为 `"messages"` 的状态键**。
    subagent 的交接协议建立在消息历史上，没有这个键就无法把结果交回父 agent。

## 结构化输出与状态继承的陷阱

回顾第 17 课的一个结论：

| subagent 类型 | 继承父级 `state_schema` |
| - | - |
| 声明式 `SubAgent` | ✅ |
| `CompiledSubAgent` | ❌ |

所以如果你的父 agent 用了自定义 state，而某个 `CompiledSubAgent` 也需要这些字段，
**你必须用兼容的 schema 自己编译那张图**。这是"灵活性换来的责任"。

```quiz
Q: 关于 subagent 的 tools 字段，正确的理解是？
- 它总是追加在主 agent 的工具之后
- 它默认不继承，需要显式指定
* 它默认继承主 agent，一旦指定就整体覆盖
- 它只控制文件系统工具，不影响自定义工具
E: 官方表格写明：tools 默认从主 agent 继承，但当指定时完全覆盖继承来的工具集，而不是合并。

Q: 哪个字段默认**不**从主 agent 继承？
- interrupt_on 与 permissions
- tools 与 model
* system_prompt、middleware 与 skills
- name 与 description
E: 官方表格中标注"Does not inherit from main agent"的是 system_prompt（isolated 模式下）、middleware 与 skills。tools、model、interrupt_on、permissions 都默认继承。

Q: 自己用 LangGraph 画一个图当作 subagent，官方要求它至少具备什么？
- 一个名为 task 的入口节点
- 一个 CompiledSubAgent 装饰器
* 一个名为 messages 的状态键
- 一个 response_format 定义
E: 官方明确要求自定义 LangGraph 图的 state 里要有名为 "messages" 的键。交接协议建立在消息历史上。

Q: 为什么官方建议 subagent 的工具集要尽量小？
- 因为工具越多启动越慢
- 因为工具越多权限越难配置
* 因为候选工具越多，模型选错的概率越高
- 因为每个工具都会创建一次模型调用
E: 官方在最佳实践中以正反例说明 minimize tool sets，理由是选择正确工具的概率随候选集增大而下降，这是候选集规模问题而不是模型能力问题。
```

## 下一课

`mode` 字段还有一个值没讲：**`"fork"`**。
它把 subagent 从"全新上下文"变成"继承父级对话"——一个看似小的改动，解决了一个具体难题。
