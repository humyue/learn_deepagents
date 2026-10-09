---
num: 10
slug: interpreters-programmatic-tool-calling
title: 解释器与程序化工具调用
module: W2
tier: A
minutes: 13
desc: 把编排从模型上下文里搬进代码，顺便省掉几十次模型调用
lede: 这是整份文档里最能体现"harness 思维"的一个机制。它解决的是一个几乎所有 agent 都会撞上的结构性问题：<b>模型一发就是一批工具调用，而这一批在发出的那一刻就冻结了。</b>
source: https://docs.langchain.com/oss/python/deepagents/interpreters
source_title: Interpreters（官方）
---

## 先看问题

一个 agent 处理"给 200 个条目各查一次"的任务，会发生什么：

<div class="flow col">
  <div class="node"><span class="k">模型发出 N 个并行工具调用</span><span class="v">这一批在 emit 的瞬间就固定了</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">N 个结果全部回到上下文</span><span class="v">每一个都占 token</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">需要循环 / 分支 / 重试？</span><span class="v">只能再要一次模型 turn</span></div>
  <div class="arrow">↓</div>
  <div class="node dim"><span class="k">模型自己决定发几次</span><span class="v">于是它通常只采样一部分，而不是覆盖全部</span></div>
</div>

官方对这一段的描述非常精确，值得逐句读：

!!! note "官方原话"
    A model can fire several tool calls in one turn, but that batch is fixed the moment
    it is emitted. Nothing can loop, branch on a result, retry a failure, or feed one call's
    output into the next without another model turn, and every result returns to the model's context.
    The model also decides how many calls to issue, so asking it to dispatch work across hundreds of items
    is unreliable, and it tends to cover a sample rather than every item.

    两个问题被点名了：
    1. **控制流不存在**——批内不能循环、不能分支、不能重试。
    2. **覆盖不可靠**——模型倾向于采样，而不是穷举。

## 解释器做的事

**把编排搬进代码。**

```python
from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware

agent = create_deep_agent(
    model="openai:gpt-5.5",
    middleware=[CodeInterpreterMiddleware()],
)
```

```bash
pip install -U "deepagents[quickjs]"
```

它给 agent 加了一个 `eval` 工具，在一个**作用域受限的 QuickJS 运行时**里执行 JavaScript。
关键性质：

| 性质 | 含义 |
| - | - |
| **在内存里** | 不落盘、不需要环境准备，和沙箱完全不同量级 |
| **中间结果不回流** | 只有你显式返回的值进入上下文 |
| **有状态** | 中间变量在运行状态里保留，不需要靠对话传递 |
| **无 shell / 无包安装 / 无文件系统 / 无网络** | 这是安全边界，也是能力边界 |

!!! key "一句话区分解释器与沙箱"
    官方给了一句很好记的对照：

    **沙箱是"对环境的代码优先"方式**（跑命令、装依赖、改文件、OS 级执行）；
    **解释器是"对组合的代码优先"方式**（组合工具、保留状态、决定什么信息回到模型）。

<div class="compare">
<div class="yes">
<h4>用解释器</h4>
<ul>
<li>纯内存的循环、分支、重试</li>
<li>结构化数据的排序、分组、校验、聚合</li>
<li>把多个工具调用串起来，中间值不回流</li>
<li>从代码里派发 subagent（下一项）</li>
</ul>
</div>
<div class="no">
<h4>用沙箱</h4>
<ul>
<li>需要 shell 命令</li>
<li>需要安装依赖包</li>
<li>需要跑测试、编译</li>
<li>需要完整的 OS 文件系统访问</li>
</ul>
</div>
</div>

## 程序化工具调用（PTC）

解释器本身只是"能算"。真正改变能力的是 **PTC**：允许解释器里的代码去调用**选定的工具**。

于是控制流回到了代码手里：

```javascript
// 概念示意：模型写一次代码，代码自己循环
const results = [];
for (const item of items) {          // ← 循环
  const r = await tool("search", { q: item });   // ← 工具调用
  if (r.ok) results.push(r.title);   // ← 分支
  else await tool("search", { q: item });        // ← 重试
}
return results.length;               // ← 只有这个值回到上下文
```

对比一下 token 消耗：

<div class="flow">
  <div class="node dim"><span class="k">普通循环</span><span class="v">200 次工具调用 → 200 个结果进上下文</span></div>
  <div class="arrow">vs</div>
  <div class="node hi"><span class="k">PTC</span><span class="v">200 次工具调用 → 只有返回值进上下文</span></div>
</div>

!!! warning "这是 beta"
    官方在页面上标了 beta，并注明需要 `langchain-quickjs>=0.2.0` 与 Python 3.11+。
    API 与生命周期行为可能在版本之间变化。学机制可以放心，上生产要有心理准备。

## 它和 dynamic subagents 的关系

解释器让 agent 能从代码里**派发 subagent**——这就是下一大块内容。
官方把它放在"为什么用解释器"的四个卡片里的第二张：
Programmatic tool calling 之外就是 Dynamic subagents。

<div class="flow">
  <div class="node"><span class="k">解释器</span><span class="v">在内存里跑 JS</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">+ PTC</span><span class="v">代码里能调工具</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">+ Dynamic subagents</span><span class="v">代码里能开子代理（第 22 课）</span></div>
</div>

## 能力对照表

官方给了一张"我该用哪个"的决策表，值得整段记住：

| 需求 | 用什么 |
| - | - |
| 一两次简单的外部调用 | 普通工具调用 |
| 纯内存 JS：循环、分支、重试、数据变换 | 解释器 |
| 大量外部工具调用，且要由代码编排 | 解释器 + PTC |
| 大量独立工作单元 / 多视角 / 对超大输入的递归分析 | 解释器 + dynamic subagents |
| shell 命令、装包、跑测试、完整 OS 文件访问 | 沙箱 |

```quiz
Q: 官方指出普通 tool-calling 循环最根本的结构性限制是什么？
- 工具返回结果没有类型标注
- 模型无法并行发出多个工具调用
* 一批工具调用在发出的瞬间就固定了，无法循环或分支
- 工具调用不能携带超过一个参数
E: 官方原文强调 "that batch is fixed the moment it is emitted"。循环、分支、重试、把一次输出喂给下一次，都需要额外的模型 turn，而每个结果都要回到上下文。

Q: 解释器与沙箱最核心的分工差异是？
- 解释器更快，沙箱更安全
- 解释器支持 Python，沙箱只支持 JS
* 解释器用于组合与状态管理，沙箱用于作用于环境
- 解释器能联网，沙箱不能联网
E: 官方的划分是：沙箱是 code-first 地作用于环境（命令、依赖、文件、OS）；解释器是 code-first 地组合工具、保留状态、控制返回给模型的信息。

Q: PTC 节省 token 的机制是什么？
- 它把工具结果压缩后再返回
- 它把工具结果缓存在沙箱磁盘里
* 中间结果留在解释器内存，只有显式返回值进入上下文
- 它把多次工具调用合并成一次请求
E: 关键性质是"中间结果不成为模型上下文的一部分"。200 次调用的产物可以只以一个数字或一个短数组的形式回到模型。

Q: 下面哪项任务最应该用沙箱而不是解释器？
- 把 500 条记录按分数排序并取前十
- 在代码里循环重试一个不稳定的 API
- 把多个工具的返回值合并成一个对象
* 安装依赖并运行项目测试套件
E: 涉及 shell、依赖安装、测试运行、完整 OS 文件系统访问时用沙箱。其余三项都是纯内存编排，属于解释器的领域。
```

## 模块 B 结束

到这里，agent 的"手"已经讲完了：工具、文件系统、权限、沙箱、解释器。
下一模块进入 harness 存在的**真正理由**——上下文。
