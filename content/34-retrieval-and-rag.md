---
num: 34
slug: retrieval-and-rag
title: 检索与 RAG：三种架构
module: W7
tier: B
minutes: 11
desc: 2-step、agentic、hybrid —— 以及为什么"已经有知识库"时不需要重建
lede: RAG 在 Deep Agents 里不是一个功能，而是三种<b>架构选择</b>。选错的代价很具体：要么牺牲延迟可预测性，要么牺牲灵活性。这一课给这三种选择一个清晰的坐标系。
source: https://docs.langchain.com/oss/python/deepagents/retrieval
source_title: Retrieval · RAG architectures（官方）
---

## 从检索到 RAG

官方把两个概念分得很清楚：

| | 做什么 |
| - | - |
| **Retrieval（检索）** | 让 LLM 在运行时访问相关上下文 |
| **RAG** | 把**检索与生成整合**起来，产生有依据的、上下文感知的回答 |

**检索是能力，RAG 是一个架构。**

## 一个重要的前置判断

!!! key "已有知识库？不要重建"
    官方明确说明：如果你已经有知识库（SQL 数据库、文档数据库、CRM、内部文档系统），
    **你不需要重建它**。两种接法：

    1. **作为工具接进 Agentic RAG** —— 让 agent 自己决定何时查
    2. **先查好再喂给 LLM（2-Step RAG）** —— 检索结果作为上下文

    这条判断省掉了大量无谓工作。**RAG 的核心不是向量库，是"把外部知识送到模型面前"这个动作。**

## 三种架构

| 架构 | 控制 | 灵活性 | 延迟 | 典型场景 |
| - | - | - | - | - |
| **2-Step RAG** | 高 | 低 | 快 | FAQ、文档机器人 |
| **Agentic RAG** | 低 | 高 | 可变 | 有多个工具的研究助手 |
| **Hybrid** | 中 | 中 | 可变 | 需要质量校验的领域问答 |

官方定义是：

- **2-Step**：检索**总是**发生在生成之前。简单、可预测。
- **Agentic**：一个 LLM 驱动的 agent 在推理过程中决定**何时**与**如何**检索。
- **Hybrid**：结合两者特征，并带有**验证步骤**。

<div class="flow col">
  <div class="node"><span class="k">2-Step</span><span class="v">问题 → 检索 → 生成 → 回答</span></div>
  <div class="node hi"><span class="k">Agentic</span><span class="v">问题 → agent 推理（决定查不查、查几次）→ 回答</span></div>
  <div class="node"><span class="k">Hybrid</span><span class="v">两者 + 校验环节</span></div>
</div>

## 一个容易被忽略的性质：延迟可预测性

官方特意用 Info 框强调：

> Latency is generally **more predictable** in **2-Step RAG**, as the **maximum number
> of LLM calls is known and capped**.

这是 2-Step 唯一但极其重要的优势：**你能给出 SLA**。

Agentic RAG 的模型调用次数是模型自己决定的——可能 1 次，也可能 15 次。
对一个需要"3 秒内响应"的产品，这不可接受。

!!! note "但延迟的瓶颈不总是模型"
    官方也补了一句：这个可预测性分析**假设 LLM 推理时间是主导因素**。
    真实世界的延迟还受检索步骤影响——API 响应时间、网络延迟、数据库查询。
    所以"2-Step 一定快"也不是绝对的，**要看你自己的瓶颈在哪。**

## 一个关键洞察：Agentic RAG 只需要工具

这是本课最实用的一句话：

!!! note "官方原话"
    The only thing an agent needs to enable RAG behavior is access to
    **one or more tools that can fetch external knowledge**, such as documentation loaders,
    web APIs, or database queries.

    也就是说：**你不需要"启用 RAG 模式"。**

    在 Deep Agents 里，把一个检索函数当作普通工具传给 `tools=`，
    agent 就自然获得了 agentic RAG 的行为。

<div class="flow">
  <div class="node"><span class="k">你的检索函数</span><span class="v">search_docs / query_db / fetch_url</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">作为 tool 传入</span><span class="v">tools=[search_docs]</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">Agentic RAG</span><span class="v">agent 自己决定何时查、查几次</span></div>
</div>

## 检索流水线

官方的 "Retrieval pipeline" 一节列了构建块。典型组成：

| 阶段 | 组件 |
| - | - |
| 加载 | document loaders |
| 切分 | splitters（决定 chunk 粒度） |
| 向量化 | embeddings 模型 |
| 存储 | vector store |
| 检索 | 相似度搜索 / 混合搜索 |
| 生成 | LLM + 检索到的上下文 |

!!! tip "在 harness 语境下，这一段最值得关注的是"切分""
    因为 chunk 粒度决定了**每次检索往上下文里塞多少 token**。

    chunk 太大 → 检索一次就吃掉大量窗口
    chunk 太小 → 检索多次，同样累加

    这与第 15 课的 offloading 是同一个问题的两种形态：
    **都是"如何把外部知识以可控粒度送进上下文"。**

## 官方给的完整教程

官方指向一个可跑通的教程，它演示了两件事：

1. 用 LangChain 的 loaders + embeddings + vector store 建一个可搜索的知识库
2. 在它之上实现一个最小 RAG 工作流

而 `rag` 页面的完整示例更进一步：**索引 LangChain 自己的文档**，
再建一个能查这份文档的 deep agent。
这基本上就是"给 agent 一本手册"的标准做法。

## 选型建议

| 你的情况 | 建议 |
| - | - |
| 有明确的知识库、问题域窄、要低延迟 | **2-Step** |
| 有多个知识源、问题类型多变 | **Agentic**（把每个源做成一个工具） |
| 答案质量要求高、能接受额外调用 | **Hybrid**（加校验环节） |
| 已经有现成知识库 | **不要重建**，接成工具或先查后喂 |

```quiz
Q: Agentic RAG 在 Deep Agents 里开启需要什么？
- 一个专用的 RAG middleware
- 一个 VectorStoreBackend 配置
* 只需要把一个能获取外部知识的函数作为工具传入
- 一个 response_format 定义的引用 schema
E: 官方明确说：让 agent 具备 RAG 行为唯一需要的就是访问一个或多个能获取外部知识的工具（文档加载器、Web API、数据库查询）。

Q: 2-Step RAG 相对 Agentic RAG 的核心优势是什么？
- 答案质量更高
- 可以访问更多知识源
* 最大模型调用次数已知且有上界，因此延迟更可预测
- 不需要任何向量存储
E: 官方在对比表中标注 2-Step 控制力高、延迟快，并在说明里指出其延迟更可预测，因为 LLM 调用次数上限是已知的。

Q: 已经有内部文档系统时，官方的建议是？
- 先用它重建一个向量库以保证一致性
- 必须迁移到 LangChain 的 vector store 才能使用
* 不需要重建，把它接成工具或先查好再作为上下文
- 只能用 2-Step RAG 架构
E: 官方明确指出：如果已经有知识库（SQL、文档库、CRM、内部文档系统），不需要重建，可以接成工具用于 Agentic RAG，或查询后把内容作为上下文提供给 LLM。

Q: 在 harness 语境下，检索流水线里"切分粒度"为什么特别重要？
- 它决定了嵌入模型的维度
- 它决定了向量库的索引类型
* 它决定了每次检索会往上下文里塞多少 token
- 它决定了文档加载器能否解析 PDF
E: chunk 粒度直接控制单次检索注入上下文的 token 量，这与 offloading 要解决的是同一类问题：以可控粒度把外部信息送进有限窗口。
```

## 下一课

三个成品模式里的第一个：**deep research agent**。
它基本上是本课程前面所有机制的一次综合演练。
