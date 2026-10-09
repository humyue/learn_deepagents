---
num: 14
slug: memory-long-term
title: Memory：长期记忆的四个维度
module: W3
tier: A
minutes: 13
desc: 时长、类型、作用域、更新策略 —— 记忆不是"存个文件"那么简单
lede: 上下文工程的后半段是"跨会话留下什么"。这一课把记忆拆成可独立决策的四个维度，你会发现"作用域"这个产品问题，在 Deep Agents 里被翻译成了一个 namespace 元组。
source: https://docs.langchain.com/oss/python/deepagents/memory
source_title: Memory（官方）
---

## 记忆就是文件

Deep Agents 对记忆的设计选择很干脆：**记忆是文件系统里的文件，agent 用 `edit_file` 更新它。**

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    memory=["/memories/AGENTS.md"],
    skills=["/skills/"],
    backend=CompositeBackend(
        default=StateBackend(),
        routes={
            "/memories/": StoreBackend(namespace=lambda rt: ("my-agent",)),
            "/skills/":   StoreBackend(namespace=lambda rt: ("my-agent",)),
        },
    ),
)
```

三个步骤（官方原文）：

1. **指向记忆文件** —— 传 `memory=`；`skills=` 是过程性记忆；`backend` 决定存哪里、谁能访问。
2. **agent 读取记忆** —— 启动时载入系统提示（memory），或按需读取（skills）。
3. **agent 更新记忆（可选）** —— 学到新东西时用内建 `edit_file` 更新；改动持久化，下个会话可见。

!!! key "为什么"记忆是文件"是个聪明的设计"
    因为它让 agent **用已经会的能力来管理自己的记忆**。
    不需要记忆 API、不需要专门的工具、不需要新的心智模型——
    读写文件的 7 个工具，既是操作代码的手段，也是维护记忆的手段。
    这是"一个地基支撑多个能力"的又一例（第 06 课）。

## 短期 vs 长期

| | 短期记忆 | 长期记忆 |
| - | - | - |
| 载体 | 对话历史 + 会话内草稿文件 | 跨会话的文件 |
| 机制 | LangGraph **checkpointer**（按 thread） | LangGraph **store** |
| 作用域 | 单个 thread | 跨 thread |
| 何时消失 | 换 `thread_id` 就没了 | 除非显式删除 |

<div class="flow">
  <div class="node"><span class="k">thread A</span><span class="v">checkpoint A（自己的历史）</span></div>
  <div class="arrow">·</div>
  <div class="node hi"><span class="k">store</span><span class="v">跨 thread 共享的记忆与技能</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">thread B</span><span class="v">checkpoint B（自己的历史）</span></div>
</div>

## 维度一：作用域（谁和谁共享）

这是最重要的一个维度，也是产品需求最常变化的一个：

```python
# Agent-scoped：所有用户共享一份，agent 有自己的"人格"
namespace=lambda rt: (rt.server_info.assistant_id,)

# User-scoped：每个用户一份，偏好严格隔离
namespace=lambda rt: (rt.server_info.user.identity,)

# Thread-scoped：退化成短期记忆
namespace=lambda rt: (rt.server_info.thread_id,)
```

官方对 agent-scoped 的描述值得读一遍：
"给 agent 一个自己的持久身份，随时间演化。它在所有用户之间共享，
所以 agent 通过每一次对话建立起自己的人格、积累知识与学到的偏好。"

!!! note "版本提示"
    读 `rt.server_info` 需要 `deepagents>=0.5.0`。
    更早的版本要从 `get_config()["metadata"]["assistant_id"]` 里取。

## 维度二：信息的类型

官方的划分：

| 类型 | 是什么 | 存在哪 |
| - | - | - |
| **Semantic** | 事实与偏好（"用户喜欢简洁回答"） | `AGENTS.md` 之类的文件 |
| **Procedural** | 怎么做某件事的指令与流程 | **skills** |
| **Episodic** | 过去发生过什么、顺序如何、结果怎样 | checkpointed threads |

**Episodic memory 是这里最容易被忽略的一种。** 官方指出：
Deep Agents 已经在用 checkpointer，而 checkpointer **就是**支持情景记忆的机制——
每一次对话都已经作为 checkpointed thread 持久化了。

要让这些历史可被检索，需要把它包成一个工具：

```python
@tool
async def search_past_conversations(query: str, runtime: ToolRuntime) -> str:
    """Search past conversations for relevant context."""
    user_id = runtime.server_info.user.identity
    threads = await client.threads.search(metadata={"user_id": user_id}, limit=5)
    ...
```

!!! tip "关键细节：user_id 从 runtime 取，不作为参数"
    这样模型**无法伪造**它——作用域由运行时决定，不由模型决定。
    这是把安全边界放在代码层而不是提示层的典型手法。

## 维度三：更新策略（什么时候写）

| 策略 | 优点 | 代价 |
| - | - | - |
| **Hot path**（对话中直接写） | 记忆立即可用，对用户透明 | 增加延迟，agent 要"一心二用" |
| **Background**（对话之间整合） | 无用户可见延迟，可跨多次对话综合 | 记忆下次对话才可用，需要第二个 agent |

背景整合（官方也叫作 **sleep time compute**）的推荐做法是：
再部署一个**整合 agent**，读最近的对话历史，抽取关键事实并合并进记忆 store，
由 cron 定时触发。

!!! warning "整合频率不是越高越好"
    官方给了一条很实用的建议：**整合频率不该远高于用户的对话频率。**
    聊天类产品可以每几小时一次；每周用几次的工具，每晚或每周一次就够。
    "Consolidating much more often than users converse just burns tokens on no-op runs."

## 维度四：可写性

不是所有记忆都该让 agent 改：

| 记忆 | 建议 |
| - | - |
| 用户偏好、学到的经验 | 可写 |
| 开发者定义的技能与工作流 | **只读** |
| 组织级政策 | **只读** |

只读可以通过文件系统权限表达（第 08 课）。

!!! trap "并发写是个真实的坑"
    多个线程（甚至多个 agent）同时编辑同一个记忆文件会互相覆盖。
    官方把它和"同一部署里的多个 agent"放在一起讨论——
    设计记忆布局时要把"谁可能同时写同一份文件"想清楚。

## 一张决策表

| 问题 | 选项 |
| - | - |
| 存多久？ | 单次对话 / 跨对话 |
| 存什么？ | 情景（经历）/ 过程（技能）/ 语义（事实） |
| 谁能看？ | 用户 / agent / 组织 |
| 何时写？ | 对话中 / 对话之间 |
| 怎么读？ | 载入 prompt / 按需读取 |
| agent 能写吗？ | 可写 / 只读 |

```quiz
Q: 在 Deep Agents 里，agent 更新记忆用的工具是什么？
- 一个专门的 memory_write 工具
- 通过 LangGraph store API 直接写
* 内建的 edit_file 工具
- 通过 skills 的 scripts/ 目录执行脚本
E: 官方三步里的第三步写明：agent 学到新信息时可以用内建 edit_file 工具更新记忆文件。这就是"记忆即文件"设计的直接好处。

Q: 情景记忆（episodic memory）在 Deep Agents 里由什么机制支撑？
- 由 store 里的 AGENTS.md 文件
- 由 skills 目录下的 references/
* 由 checkpointer 持久化的 thread 历史
- 由 backend 的 policy hooks 记录审计日志
E: 官方指出 Deep Agents 已经在使用 checkpointer，而它就是支持情景记忆的机制——每次对话都作为 checkpointed thread 持久化。要检索历史需要把它包成工具。

Q: 关于后台记忆整合（sleep time compute），官方给出的实用建议是？
- 每次对话结束后都应立即整合
- 整合频率越高记忆质量越好
* 整合频率不应远高于用户的对话频率
- 只在用户显式请求时才需要整合
E: 官方明确说，整合得比用户对话还频繁只是在 no-op 运行上烧 token。建议按真实使用节奏选定 cadence，例如每天几小时或每晚一次。

Q: 检索历史对话的工具里，为什么 user_id 从 runtime 取而不是作为函数参数？
- 因为模型无法可靠地生成 UUID
- 因为工具参数会占用更多 token
* 因为作用域由运行时决定，模型无法伪造
- 因为 ToolRuntime 只在异步工具里可用
E: 从 runtime.server_info.user.identity 取得身份，使作用域成为运行时决定的事实而非模型可填的参数。这是把边界放在代码层而非提示层的标准做法。
```

## 下一课

输入上下文讲完了。现在进入运行中最硬核的一层：
**当窗口真的要满了，harness 到底做了什么？**
