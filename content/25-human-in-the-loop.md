---
num: 25
slug: human-in-the-loop
title: Human-in-the-loop：在关键点按下暂停
module: W5
tier: A
minutes: 13
desc: interrupt_on、四种决策、以及为什么 checkpointer 是硬依赖
lede: 一个能自己读写文件、跑代码、发邮件的 agent，需要一个刹车。Deep Agents 的做法是把刹车装在<b>工具调用之前</b>，并且支持四种不同的处理方式——不只是"批准/拒绝"。
source: https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
source_title: Human-in-the-loop（官方）
---

## 一个必须记住的前提

!!! warning "checkpointer 是硬依赖"
    中断意味着"停下来，之后从同一处继续"。这要求状态被保存下来。
    所以：**中断必须有 checkpointer，并且恢复时必须使用同一个 `thread_id`。**

    官方在最佳实践里把这两条列为前两条：
    1. Always use a checkpointer
    2. Use the same thread ID

## 机制：中断发生在工具调用之前

启用方式是一个映射：

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

agent = create_deep_agent(
    model="openai:gpt-5.5",
    interrupt_on={"edit_file": True},     # 每次编辑前暂停
    checkpointer=MemorySaver(),
)
```

传入 `interrupt_on` 时，`HumanInTheLoopMiddleware` 会被加进 middleware 栈（第 04 课的第 11 位）。

<div class="flow">
  <div class="node"><span class="k">agent 决定调用工具</span><span class="v">edit_file(...)</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">中断检查</span><span class="v">这个工具在 interrupt_on 里吗？</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">暂停，交给人</span><span class="v">approve / edit / reject / respond</span></div>
  <div class="arrow">→</div>
  <div class="node dim"><span class="k">继续执行</span><span class="v">或回填一个 ToolMessage</span></div>
</div>

!!! note "PatchToolCallsMiddleware 在这里值班"
    官方提到：如果一次运行在工具返回结果之前被取消或中断，
    同一个栈里的 `PatchToolCallsMiddleware` 会**自动修复消息历史**。

    这解释了第 04 课的一个排序决策：为什么修补工具必须排得很靠前——
    中断在 harness 里是**常态**，不是异常。

## 四种决策（不只是批准）

这是这一课最值得记住的部分。中断之后人有四种选择：

| 决策 | 含义 | 结果 |
| - | - | - |
| **approve** | 批准原样执行 | 工具照常运行 |
| **edit** | 修改工具参数后执行 | 用你改过的参数运行 |
| **reject** | 拒绝执行 | 回一个 `ToolMessage` 说明被拒 |
| **respond** | 直接给出回答，不执行工具 | 回一个 `ToolMessage` 带你的内容 |

<div class="flow">
  <div class="node"><span class="k">approve</span><span class="v">→ 执行</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">edit</span><span class="v">→ 改参数后执行</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">reject</span><span class="v">→ ToolMessage（拒绝）</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">respond</span><span class="v">→ ToolMessage（你的回答）</span></div>
</div>

!!! key "reject 与 respond 的区别值得想清楚"
    - **reject**：告诉模型"这件事没做"。模型需要重新规划。
    - **respond**：告诉模型"答案是这个"。工具没执行，但模型拿到了信息。

    第二种用法很有意思：**当你知道答案、不想让 agent 花代价去查时**，
    直接用 respond 注入答案。这是一条"人作为工具"的通道。

## 配置的三种写法

```python
interrupt_on={
    "edit_file": True,        # 开启，允许全部四种决策
    "write_file": False,      # 显式关闭
    "execute": {              # 自定义：只允许批准或拒绝
        "allowed_decisions": ["approve", "reject"],
    },
}
```

| 值 | 含义 |
| - | - |
| `True` | 启用，默认允许 approve / edit / reject / respond |
| `False` | 关闭该工具的中断 |
| `InterruptOnConfig` | 自定义，可用 `allowed_decisions` 收窄选项 |

Python 里还可以加一个可选的 `when` 谓词，**只对特定调用中断**（条件中断）。
这一点很实用：不是所有 `write_file` 都危险，也许只有写到某个目录才需要批准。

## 处理中断

```python
config = {"configurable": {"thread_id": "1"}}   # 状态持久化必须的 thread_id

result = agent.invoke({"messages": [...]}, config=config)

# 检查是否被中断
if result.get("__interrupt__"):
    ...   # 取出中断内容，做出决策，然后用同一个 config 恢复
```

恢复时**必须用同一个 `thread_id`**，否则状态接不上。

!!! trap "最常见的两个错误"
    1. **忘了 checkpointer** → 中断之后无法恢复（状态没地方存）。
    2. **恢复时用了新的 thread_id** → 看起来像"agent 忘了刚才要做什么"，
       实际上是接到了一个空状态上。

    这两个错误的信息量很少，但排查成本很高。记住它们能省很多时间。

## 流式场景下的中断

官方单独给了一节"Handle interrupts with streaming"。
用流式时，中断会作为一个事件出现在流里，而不是从 `invoke` 的返回值里读。
这决定了你的 UI 怎么呈现"等待批准"状态。

## 多工具调用的情况

模型一轮里可能发出**多个**工具调用，其中若干个都需要批准。
这时中断里会包含一组待决策项，顺序很重要：

!!! warning "决策顺序必须与动作顺序一致"
    官方在最佳实践中明确写了 **"Match decision order to actions"**。
    你给出的决策列表是按位置对应的，顺序接错就会批准错的对象。

## 子 agent 的中断

subagent 也可以中断，官方区分了两种情形：

| 情形 | 说明 |
| - | - |
| **对工具调用的中断** | subagent 的 `interrupt_on` 转发给 `create_agent` 处理 |
| **工具调用内部的中断** | 工具自己触发中断（工具内部调 `interrupt()`） |

!!! note "subagent 的权限范围不同"
    声明式 subagent 的 `interrupt_on` 默认继承主 agent，且它自己的值会覆盖默认。
    这意味着你可以让"写代码的 subagent"需要批准，
    而"只读调研的 subagent"完全不需要打断。

## 文件系统权限也能中断

这是一个容易被忽略的联动：**文件系统权限规则的第三种结果是"暂停问人"**（第 08 课）。
所以你有两套互补的机制：

<div class="flow">
  <div class="node"><span class="k">interrupt_on（按工具）</span><span class="v">"write_file 我要看一眼"</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">permissions（按路径）</span><span class="v">"/workspace/.env 我要看一眼"</span></div>
</div>

## 最佳实践清单

| 实践 | 内容 |
| - | - |
| 总是用 checkpointer | 中断的前提 |
| 恢复时用同一个 thread ID | 否则状态接不上 |
| 决策顺序匹配动作顺序 | 位置对应，不要错位 |
| 按风险分层配置 | 破坏性操作严格，只读操作放开 |

!!! tip "最后一条是最容易被浪费的一条"
    **如果你对所有工具都开中断，人很快就会开始无脑点"批准"。**
    那时的中断不是安全机制，只是噪音。

    正确做法是分层：`execute`、`delete`、花钱的 API 调用严格把关；
    `read_file`、`glob` 完全放开。
