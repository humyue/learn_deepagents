---
num: 38
slug: grading-rubrics
title: 评分量表：让 agent 自己迭代到达标
module: W7
tier: B
minutes: 11
desc: RubricMiddleware、评判循环、以及"把验收标准变成可执行的检查"
lede: 前面所有机制都在解决"agent 能不能做完"。这一课解决另一个问题：<b>怎么让它知道"做好了"是什么意思。</b>
source: https://docs.langchain.com/oss/python/deepagents/rubric
source_title: Grading rubrics（官方）
---

## 问题：模型不知道自己合格了没有

一个 agent 写完一段代码，它凭什么认为写完了？

- 没有任何检查 → 它觉得"差不多"，直接返回
- 只有人检查 → 迭代周期变成小时级
- **有一个自动的评判标准** → 它可以自己循环到达标

**Rubric（评分量表）就是那个标准。**

## 启用方式

```python
from deepagents import RubricMiddleware, create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

agent = create_deep_agent(
    model="openai:gpt-5.5",
    middleware=[
        RubricMiddleware(
            model="anthropic:claude-haiku-4-5",   # 评判用的模型
            max_iterations=3,                      # 最多迭代几轮
        ),
    ],
    checkpointer=InMemorySaver(),
)
```

!!! key "两个参数透露了全部设计"
    - **`model=`**：评判用**单独的模型**。这意味着评判者可以和生产者不同
      ——常见做法是用更便宜/更快的模型做评判（这里的例子用了一个较小的模型）。
    - **`max_iterations=`**：循环有上界。**必须有上界**，否则一个永远不达标的
      agent 会无限迭代下去，烧掉大量 token。

    这和 fault tolerance 里的调用限额（第 26 课）是同一个思路：
    **任何自动循环都需要一个成本上界。**

!!! note "需要 checkpointer"
    官方示例里带了 `checkpointer=InMemorySaver()`。
    因为多轮迭代意味着状态要在轮次之间保持——这和中断需要 checkpointer
    是同一个原因（第 25 课）。

## 评判循环

<div class="flow col">
  <div class="node"><span class="k">① 生成</span><span class="v">主 agent 产出内容（代码、文本…）</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">② 评分</span><span class="v">按 rubric 判定：达标了吗？</span></div>
  <div class="arrow">↓ 未达标</div>
  <div class="node"><span class="k">③ 带着反馈重做</span><span class="v">把"哪里不达标"传回给主 agent</span></div>
  <div class="arrow">↓ 最多 max_iterations 轮</div>
  <div class="node dim"><span class="k">④ 交出结果</span><span class="v">达标，或达到迭代上限</span></div>
</div>

## 在调用时传 rubric

官方有一节 "Pass rubric on invocation"。这说明一个重要事实：

!!! key "rubric 不一定要写死在 middleware 里"
    它是**按调用传入**的。这意味着：

    - 同一个 agent 可以应对不同任务的验收标准
    - 标准可以由上游系统决定（比如工单系统里带的质量要求）
    - 你不需要为每种任务各建一个 agent

    这是"配置与调用分离"的又一个实例——和第 27 课的 profile 思路一致。

## Rubric 的判定结果

官方有 "Rubric verdicts" 一节。概念上会有几种判定结果，而不同的判定对应不同的后续动作：

| 判定 | 后续 |
| - | - |
| 达标 | 结束循环，交出产出 |
| 不达标（可改进） | 带着反馈再迭代一轮 |
| 达到迭代上限 | 停止，交出当前最好结果 |

!!! warning "达到上限时也要有产出"
    这一点容易被忽略：**迭代到上限却还没达标时，不能什么都不返回。**
    你应该拿到"当前最好的版本 + 为什么没达标"，
    这样人才能接着处理。

    `max_iterations` 的语义是**"最多试几次"**，不是"必须达标"。

## 观察迭代过程

官方有一节 "Observe iteration progress"，还有 "Grader pass events"。

这说明评判过程是**可观测的**：

<div class="flow">
  <div class="node"><span class="k">迭代进度</span><span class="v">第几轮、当前判定</span></div>
  <div class="arrow">·</div>
  <div class="node"><span class="k">grader pass 事件</span><span class="v">评判这一步在流里是可见的</span></div>
</div>

**为什么这很重要？** 因为评判模型本身也会有误差。
如果用户看到"agent 来回改了三次"，他们需要能查清是**产出真的不合格**，
还是**评判标准过严**。

!!! tip "把 grader 当作需要调试的组件"
    不要在第一次使用 rubric 时就期待它准确。
    像调试任何分类器一样调试它：看它的判定理由、找误判的案例、
    修正 rubric 的措辞。

    官方给出 grader pass 事件，本质上就是把评判这一步**放到可观测表面上**。

## 跨调用持久化

官方有一节 "Persist rubrics across invocations"。

这解决了多轮交互的现实问题：用户说"再改改"，你需要让**同一个标准**继续生效，
而不是每一轮都重新声明。

## 官方示例：生成经过审查的 Python 代码

官方的完整示例是 "generate vetted Python code"——这个名字很精确：

| 词 | 含义 |
| - | - |
| **vetted** | 经过审查的，不是"生成完就交" |
| **Python code** | 代码是最适合用 rubric 的领域 |

**为什么代码特别适合？** 因为检查标准是**可机械化的**：

- 能跑通吗？
- 有类型问题吗？
- 覆盖了边界情况吗？
- 有安全漏洞吗？

!!! key "这解释了 rubric 的适用边界"
    **Rubric 适合"验收标准可以被明确陈述"的产出。**

    - 代码 → 很适合（可执行、可检查）
    - 结构化数据 → 很适合（schema 可验证）
    - 研究报告 → 中等（有部分可查：引用是否存在）
    - 创意写作 → 较难（"好不好"很难写清）

    如果一个任务的验收标准你自己都说不清楚，rubric 不会帮上忙。
    **这不是技术限制，是问题性质。**

## 与其它质量机制的对比

| 机制 | 作用 | 时机 |
| - | - | - |
| **Rubric** | 迭代到达标 | 产出后、交付前 |
| **Human-in-the-loop** | 人做最终判断 | 关键动作前 |
| **Adversarial verification**（第 22 课） | 专门找问题 | 产出后 |
| **LangSmith 评估** | 离线批量测量 | 开发期 |

!!! note "最后一行值得注意"
    官方在 quickstart 的 next steps 里建议用
    [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluation-quickstart)
    跑自动化测试、用数据集衡量 agent 表现。

    **Rubric 是运行时的质量循环；evaluation 是开发期的质量度量。**
    前者让单次任务达标，后者让你知道改动有没有让整体变好。

```quiz
Q: RubricMiddleware 的 max_iterations 参数为什么是必需的？
- 因为评判模型只支持有限次调用
- 因为超过三轮后质量不再提升
* 因为任何自动循环都需要成本上界，否则可能无限迭代
- 因为 checkpointer 无法保存更多轮次的状态
E: 自动评判循环若永远不达标会持续消耗 token，必须有上界。这与调用限额中间件给成本设上界是同一思路。

Q: 评判使用单独的 model 参数，这带来的主要灵活性是什么？
- 评判模型可以访问主模型看不到的工具
- 评判模型可以绕过 checkpointer
* 评判者与生产者可以是不同模型，例如用更便宜的模型做评判
- 评判模型可以并行运行多个实例
E: RubricMiddleware 接受独立的 model，官方示例用了一个较小的模型（claude-haiku）来评分，使生产者与评判者解耦。

Q: 达到 max_iterations 但内容仍未达标时，正确的预期是？
- 抛出异常并终止整个运行
- 自动放宽标准使其通过
* 停止迭代并交出当前最好结果与未达标原因
- 无限继续迭代直到达标
E: max_iterations 的语义是"最多试几次"。到上限时仍应产出当前版本并保留未达标的信息，交给人继续处理。

Q: 为什么官方的完整示例选择"生成经过审查的 Python 代码"？
- 因为 Python 是 Deep Agents 唯一支持的沙箱语言
- 因为代码生成的 token 成本最低
* 因为代码的验收标准可以被明确陈述与机械检查
- 因为代码不需要人类审批
E: Rubric 的适用边界是"验收标准能否被明确陈述"。代码可执行、可做类型检查、可查安全漏洞，因此最适合作为 rubric 示例；而创意写作这类"好不好"难以表述的任务则不适用。
```

## 下一课

还剩最后两块：**怎么把它送进生产**，以及**怎么让外部工具/编辑器接进来**。
先讲生产。
