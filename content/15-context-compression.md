---
num: 15
slug: context-compression
title: 压缩：Offloading 与 Summarization
module: W3
tier: A
minutes: 14
desc: 20,000 token 阈值、85% 触发线、10% 保留量 —— 装满时到底发生了什么
lede: 这一课是全课程里数字最密的一课，也是最有价值的一课。harness 在窗口将满时做了两件不同的事：把东西<b>搬出去</b>，和把东西<b>压小</b>。知道两者的触发条件与恢复路径，你就能预测 agent 在长任务里的行为。
source: https://docs.langchain.com/oss/python/deepagents/context-engineering#context-compression
source_title: Context engineering · Context compression（官方）
---

## 两种机制，两个不同的病

<div class="compare">
<div class="yes">
<h4>Offloading（卸载）</h4>
<ul>
<li>治的是：<b>单个</b>工具调用太大</li>
<li>手段：写到文件系统，上下文里换成引用</li>
<li>信息有没有丢：<b>没丢</b>，可以读回来</li>
<li>触发：20,000 token 阈值</li>
</ul>
</div>
<div class="no">
<h4>Summarization（摘要）</h4>
<ul>
<li>治的是：<b>整体</b>历史太长</li>
<li>手段：用 LLM 生成结构化摘要替换历史</li>
<li>信息有没有丢：<b>原始文本进文件系统</b>，摘要进上下文</li>
<li>触发：接近模型窗口上限（约 85%）</li>
</ul>
</div>
</div>

## Offloading 的两种触发方式

官方给了两个**方向相反**的卸载：

### 方向一：工具调用的**输入**太大

> 文件写入与编辑操作，会在对话历史里留下包含**完整文件内容**的 tool call。
> 而这些内容**已经**持久化到文件系统了，通常是冗余的。
> 当会话上下文越过模型可用窗口的 **85%** 时，deep agent 会截断较早的 tool call，
> 用"指向磁盘上文件的指针"替换它们。

**这是一个非常聪明的洞察：模型自己写的文件内容，在历史里出现了两次。**
一次在文件系统，一次在 tool call 参数里。后者是纯冗余，可以放心丢掉。

### 方向二：工具调用的**结果**太大

> 当工具结果超过 20,000 token 时，deep agent 把响应卸载到配置的 backend，
> 用**文件路径引用 + 前 10 行的预览**替代它。agent 之后可以重新读取或搜索这段内容。

<div class="flow">
  <div class="node"><span class="k">工具返回</span><span class="v">&gt; 20,000 token</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">写入 backend</span><span class="v">完整内容落盘</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">上下文里变成</span><span class="v">路径 + 前 10 行预览</span></div>
  <div class="arrow">→</div>
  <div class="node dim"><span class="k">可按需取回</span><span class="v">grep 定位 → read_file 分段读</span></div>
</div>

!!! key "为什么"前 10 行预览"这个细节很重要"
    如果只留路径，模型无法判断这个文件是否相关，它会**倾向于不管三七二十一先读一遍**——
    于是刚省下的 token 又被读回来了。
    留 10 行预览，模型就能做出"要不要读"的判断。**这是一个用极小成本换取决策质量的设计。**

!!! warning "只有工具调用被卸载，图片不会被重新编码"
    官方特别注明：内建压缩**不会**缩放图片、降低分辨率或生成视觉 embedding。
    多模态内容与压缩的交互见第 18 课。

## Summarization 的完整参数

这是需要精确记住的一组数字：

<div class="stack">
  <div class="layer req"><span class="idx">触发</span><span class="nm">模型的 85%</span><span class="ds">按模型 profile 里的 max_input_tokens 计算</span></div>
  <div class="layer req"><span class="idx">保留</span><span class="nm">10% token</span><span class="ds">作为"最近上下文"原样保留</span></div>
  <div class="layer opt"><span class="idx">兜底</span><span class="nm">170,000 token / 6 条消息</span><span class="ds">当拿不到模型 profile 时使用</span></div>
  <div class="layer opt"><span class="idx">异常</span><span class="nm">ContextOverflowError</span><span class="ds">任何模型调用抛此异常 → 立刻回退到摘要 + 保留最近消息并重试</span></div>
</div>

触发条件是**组合**的：当上下文越过窗口上限，**并且**已经没有更多可卸载的内容时，才会摘要。

!!! note "顺序：先卸载，后摘要"
    官方原文是 "and there is no more context eligible for offloading"。
    这说明 offloading 是**第一道防线**（无损、便宜），summarization 是**第二道**（有损、要调模型）。
    能用卸载解决的，绝不摘要。

## 摘要做了两件事

这是本课最值得记住的设计：

| 动作 | 产出 | 作用 |
| - | - | - |
| **In-context summary** | 一段结构化摘要：session 意图、创建的产物、下一步 | 替换完整历史，成为工作记忆 |
| **Filesystem preservation** | 原始对话消息的文本渲染 | 写进文件系统，作为**权威记录** |

> 这个双重做法保证 agent 通过摘要保持对目标与进度的感知，
> 同时保留在需要时（通过文件系统搜索）恢复文本细节的能力。

!!! key "一句话概括"
    **摘要保住"我要干什么"，文件系统保住"我具体说过什么"。**
    前者是方位感，后者是证据。

## 一个实用细节：怎么过滤掉摘要产生的 token

摘要本身也是一次模型调用，它的输出 token 会混进流式输出里：

```python
for token, metadata in agent.stream({"messages": [...]}, stream_mode="messages"):
    if metadata.get("lc_source") == "summarization":
        continue        # 跳过摘要步骤生成的 token
    ...
```

这个元数据标签在写 UI 时很有用——你不想让用户看到"正在生成摘要"的字。

## 按需压缩：`compact_conversation`

除了自动触发，还能给 agent 一个主动压缩的工具：

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from deepagents.middleware.summarization import create_summarization_tool_middleware

backend = StateBackend
model = "openai:gpt-5.5"

agent = create_deep_agent(
    model=model,
    middleware=[
        create_summarization_tool_middleware(model, backend),
    ],
)
```

它给 agent 一个 `compact_conversation` 工具。适用场景是官方的原话：
"**在合适的时机**触发压缩，比如任务之间，而不是在固定的 token 间隔。"

<div class="flow">
  <div class="node dim"><span class="k">自动压缩</span><span class="v">等到 85%，被动、可能发生在关键时刻</span></div>
  <div class="arrow">vs</div>
  <div class="node hi"><span class="k">按需压缩</span><span class="v">任务交界处主动清空，语义上更干净的切点</span></div>
</div>

!!! tip "压缩本身也是一笔开销"
    摘要要调用模型、要花 token、要花时间。所以"更早压缩"不等于"更省"。
    理想时机是**语义上的任务边界**——一个子任务刚结束，它的中间过程可以安全丢弃。
    这又一次说明：harness 的很多决策不是纯技术最优，而是**语义最优**。

## 与 subagent 的分工

压缩是"在同一个窗口里省"；隔离是"换一个窗口"。两者的取舍：

| | 压缩 | 隔离（subagent） |
| - | - | - |
| 成本 | 一次摘要模型调用 | 一次完整的子 agent 运行 |
| 信息损失 | 有（摘要是有损的） | 无（但只带回最终结果） |
| 适用范围 | 主线程自己的历史 | 可以外派的重活 |
| 何时用 | 无法外派、必须自己做完的事 | 可以"交出去拿结果"的事 |

```quiz
Q: 工具结果的 offloading 触发阈值是多少？
- 5,000 token
- 20,000 token
* 刚好是 20,000 token
- 170,000 token
E: 官方给出两个阈值：工具调用的输入与结果都以 20,000 token 为卸载阈值。170,000 是拿不到模型 profile 时 summarization 的兜底触发值。

Q: offloading 与 summarization 的触发优先级关系是？
- 两者同时触发，由模型决定用哪个
- 先摘要，摘要不够再卸载
* 先卸载，没有可卸载的内容时才摘要
- 由 backend 类型决定顺序
E: 官方原文是当上下文越过窗口上限 "and there is no more context eligible for offloading" 时才摘要。卸载是无损的第一道防线，摘要是有损的第二道。

Q: summarization 同时产出两样东西，它们是？
- 一段摘要与一份 token 统计
* 进入上下文的摘要，和写入文件系统的原始消息文本
- 一份摘要与一份新的 system prompt
- 一份摘要与一份 LangSmith trace
E: 官方描述为 in-context summary（结构化摘要，替换历史）与 filesystem preservation（原始消息的文本渲染，作为权威记录）。

Q: 工具调用**输入**被 offload 时，为什么可以安全截断？
- 因为输入内容已经不再被模型需要
- 因为输入内容被压缩成摘要保存了
* 因为完整内容已经持久化到文件系统，历史里是冗余的
- 因为模型可以从缓存里重新计算输入
E: 文件写入与编辑操作会在历史里留下包含完整文件内容的 tool call，而这份内容已经写进文件系统。截断后用指向磁盘文件的指针替代即可。
```

## 下一课

压缩讲完了，但还有一个更省钱的手段没提：**别重复计算**。
Prompt caching 是个纯粹的工程优化，但它直接决定了 middleware 的排序（第 04 课）。
