---
num: 22
slug: dynamic-subagents
title: Dynamic Subagents：让代码决定开多少个子任务
module: W4
tier: A
minutes: 14
desc: task() 全局函数与六种编排模式 —— 把"采样"变成"穷举"
lede: 上一课的 subagent 由模型逐个决定。这一课换一个控制者：<b>代码</b>。加上一个 <code>task()</code> 全局函数之后，"审查这个目录下全部 80 个文件"从一句不可靠的祈使句，变成了一段确定性的循环。
source: https://docs.langchain.com/oss/python/deepagents/dynamic-subagents
source_title: Dynamic subagents（官方）
---

## 机制：一个内建的 `task()` 全局函数

当一个 agent **同时**具备 subagent 与解释器 middleware 时，解释器会暴露一个内建的
`task()` 全局函数——**从代码里派发 subagent**。

```python
from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware

agent = create_deep_agent(
    model="openai:gpt-5.5",
    subagents=[{
        "name": "reviewer",
        "description": "Reviews code for security issues, citing lines and severity",
        "system_prompt": "You are a security-focused code reviewer.",
    }],
    middleware=[CodeInterpreterMiddleware()],
)
```

!!! key "为什么这一步很关键"
    官方原文：一个横跨大量独立单元的任务（审查目录里每一个文件、triage 一批工单）
    **"become a loop that fans the work out, so it runs deterministically
    instead of one model-chosen tool call at a time."**

    - 模型逐个决定 → **不可靠**（会采样、会漏）
    - 代码循环 → **确定性**（覆盖全部）

    这正是第 10 课那个"覆盖不可靠"问题的彻底解法。

## `task()` 的三个参数

| 参数 | 作用 |
| - | - |
| `description` | 给 subagent 的提示词 |
| `subagentType` | 运行哪个已配置的 subagent |
| `responseSchema` | 可选，结构化输出 |

一次 `task()` 会跑完**一个完整的 agentic 循环**，并解析为 subagent 的结果：

```javascript
const review = await task({
  description: "Review src/auth/login.ts for auth issues. Cite line numbers.",
  subagentType: "reviewer",
  responseSchema: {
    type: "object",
    properties: {
      issues: { type: "array", items: { type: "object", properties: {
        file: { type: "string" }, line: { type: "number" },
        severity: { type: "string" }, description: { type: "string" },
      }}},
    },
  },
});

// 有了 responseSchema，结果已经是定型对象，不需要 JSON.parse
const critical = review.issues.filter((issue) => issue.severity === "high");
```

!!! tip "responseSchema 是这里最关键的一个细节"
    没有它，subagent 返回的是自然语言，代码里没法直接过滤/排序/聚合。
    有了它，**代码可以立刻对结果做判断**：

    ```javascript
    const critical = review.issues.filter((i) => i.severity === "high");
    ```

    这一步把"subagent 是个黑盒"变成"subagent 是个函数"。
    ——函数是可以组合的，黑盒不行。

    官方还标注：只有 subagent 有意返回 JSON 字符串时才需要 `JSON.parse`。

## 与 PTC 的组合

大多数编排工作流会把 dynamic subagents 与 **PTC** 一起用：

<div class="flow">
  <div class="node"><span class="k">PTC（tools.*）</span><span class="v">发现或筛选输入</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">task()</span><span class="v">把工作派发出去</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">代码里合成</span><span class="v">过滤 / 排序 / 聚合 / 判断</span></div>
</div>

!!! warning "PTC 默认是关的"
    官方注明：PTC 默认关闭，需要在解释器 middleware 上显式给一个允许列表才能开启。
    这条设计是对的——**能调工具的代码，等于把工具的全部权限交给了模型生成的代码。**

## 递归语言模型（RLM）

官方还点出了一个更前沿的用法：subagent 编排支持
**recursive language model (RLM)** 工作流，来自
[Recursive Language Models 论文](https://arxiv.org/abs/2512.24601)。

它的形态是：

1. 把工作集保留在解释器变量里
2. 选择切片
3. 用 `task()` 调用 subagent
4. 在代码里合成结果

!!! note "为什么这个方向值得注意"
    如果工作集只存在于**解释器变量**里，那么"读一个 100MB 的日志"这件事
    就不需要把日志塞进任何上下文窗口——它可以被切片、逐段分析、结果汇总。
    **上下文窗口从"必须装下所有输入"变成了"只需要装下切片与结论"。**

    这是 harness 思维的又一次进阶：不是压缩上下文，而是**让输入根本不进上下文**。

## 六种编排模式

官方列出的模式，都遵循同一个编排方式：**把工作放在 JS 变量里、用 `task()` 派发、在代码里合成**。
而且——官方特别强调——这些模式是**模型自己根据任务形状写出来的**，
**不是靠配置开关**。你提供的 subagent 决定了它能做什么。

| 模式 | 形状 | 典型任务 |
| - | - | - |
| **Classify and act** | 先分类，再按类别走不同分支 | 工单分流、按类型选不同处理流程 |
| **Fan-out and synthesize** | 一次性铺开 N 个子任务，汇总结果 | 审查目录下每个文件、多主题调研 |
| **Adversarial verification** | 一个 subagent 产出，另一个专门反驳 | 事实核查、方案挑战 |
| **Generate and filter** | 生成多个候选，用代码筛掉不合格的 | 候选方案生成、代码补全筛选 |
| **Tournament** | 两两比较，选出更好的 | 择优、A/B 对比 |
| **Loop until done** | 循环直到满足条件或穷尽 | 迭代修订、直到测试全绿 |

<div class="flow col">
  <div class="node"><span class="k">Classify and act</span><span class="v">分支：不同类别 → 不同 subagent</span></div>
  <div class="node"><span class="k">Fan-out and synthesize</span><span class="v">并行：N 个单元 → N 个结果 → 汇总</span></div>
  <div class="node"><span class="k">Adversarial verification</span><span class="v">对抗：产出者 vs 反驳者</span></div>
  <div class="node"><span class="k">Generate and filter</span><span class="v">漏斗：多候选 → 代码筛选</span></div>
  <div class="node"><span class="k">Tournament</span><span class="v">淘汰：两两比较，逐轮收敛</span></div>
  <div class="node"><span class="k">Loop until done</span><span class="v">迭代：条件满足才停</span></div>
</div>

!!! key "这些模式的共同价值：把"质量"变成可编程的"
    以 **Adversarial verification** 为例：让 A 写、让 B 专门找问题。
    这不是提示词技巧，而是**在代码里显式构造了一个对抗结构**。
    同样，**Tournament** 是显式构造了一个选择过程。

    一旦编排变成代码，**任何你能写出来的控制流，都可以用来提升结果质量。**

## 持久化：跨 turn 保留变量

官方提到一个实用性质：多轮编排在 `mode="thread"`（默认）下，
**解释器变量可以跨 agent turn 保留**。

意思是：这一轮建立的变量（比如"待审查的文件列表"、"已完成的索引"），
下一轮还能用。这把解释器从"一次性的计算器"变成了**有记忆的工作台**。

## 关掉它

如果你希望 subagent **只能**通过常规的 `task` 工具路径使用（不要从代码里派发）：

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    subagents=[{"name": "reviewer", "description": "Reviews code", "system_prompt": "Review code."}],
    middleware=[CodeInterpreterMiddleware(subagents=False)],
)
```

## 安全边界

`task()` 是"通往 subagent 执行的能力桥"，和 PTC 对工具的关系一样。
所以隔离默认值、审批边界、middleware 选项这些安全问题，
官方都指向解释器页面的 [Security](https://docs.langchain.com/oss/python/deepagents/interpreters#security)
与 [Configuration](https://docs.langchain.com/oss/python/deepagents/interpreters#configuration)。

!!! trap "别把 PTC 和 subagents 当纯性能优化"
    两者都是**权限放大器**：模型写的代码因此能触达工具与子代理。
    开之前先问：**这段代码能碰到的最坏的东西是什么？**

```quiz
Q: 动态 subagent 相对常规 subagent 的核心优势是什么？
- 它可以使用更强的模型
- 它可以跳过上下文隔离以节省时间
* 编排由代码完成，因此覆盖是确定性的而不是采样
- 它不需要为 subagent 编写 description
E: 官方原文说这类任务 "become a loop that fans the work out, so it runs deterministically instead of one model-chosen tool call at a time"。模型逐个决定时容易只覆盖样本。

Q: task() 的 responseSchema 参数带来的关键能力是？
- 让 subagent 运行得更快
- 让 subagent 可以跳过系统提示
* 让代码能直接对结果做过滤、排序与聚合
- 让 subagent 之间可以互相通消息
E: 有了 responseSchema，解析出的值已经是定型对象（无需 JSON.parse），代码可以立即 filter/map/reduce，使 subagent 从黑盒变成可组合的函数。

Q: 六个编排模式（fan-out、tournament 等）是怎么被启用的？
- 通过配置参数显式选择某一个模式
- 通过为每个模式定义一个专用 subagent
* 它们由模型根据任务形状自行写出代码，不靠配置开关
- 通过为每个模式安装一个独立的 middleware
E: 官方强调这些模式 "emerge from how it writes interpreter code, not from configuration"，而你提供的 subagent 决定了它能做什么。

Q: 关于 PTC 与动态 subagent 的正确理解是？
- 两者都默认开启，无需额外配置
- 两者都是纯性能优化，不影响安全边界
* 两者都是能力桥，会放大模型生成代码可触达的权限
- 两者都只能访问文件系统，不能访问外部工具
E: task() 被官方描述为通往 subagent 执行的能力桥，与 PTC 对工具的关系相同。PTC 默认关闭并需显式允许列表，两者都需要考虑隔离与审批边界。
```

## 下一课

同步、fork、dynamic 三种都讲完了。它们有一个共同点：**父 agent 要等。**
如果子任务要跑十分钟呢？下一课：异步 subagent。
