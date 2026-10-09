# Mission

## 一句话

**看穿 Deep Agents 这个 agent harness 的内部构造：知道每一步"框架替你做的事"到底是怎么做的、为什么这么做、代价是什么。**

## 为什么要学（用户的原始动机）

用户的目标不是"快速做出一个 agent 应用"，而是**理解 agent harness 的原理**。
参考物是官方文档 <https://docs.langchain.com/oss/python/deepagents/overview>，
左侧导航的每一个章节都要覆盖到。

因此本教学工作区的一切产出，都以"解释机制"为第一优先级，而不是"复制粘贴能跑的 demo"。

## 具体要能达到的能力（Success Criteria）

学完之后，用户应当能够：

1. **画出调用链**：给定一次 `create_deep_agent(...).invoke(...)`，能说出消息经过了哪些 middleware、在哪一步被改写、下一站去哪。
2. **解释四个上下文层**：input context / compression / isolation / long-term memory 各自解决什么问题，边界在哪。
3. **解释委派三兄弟的差异**：同步 subagent、dynamic subagent、async subagent 分别是什么时候的正确答案。
4. **解释"虚拟文件系统"为什么是整个 harness 的地基**：offloading、skills、memory、code execution 如何都建在它上面。
5. **判断取舍**：什么情况下该用 Deep Agents，什么情况下 LangChain `create_agent` 或裸 LangGraph 更合适。
6. **看懂故障与管控面**：interrupt、permissions、retry/fallback、profile 各自在栈里的位置。

## 约束（Constraints）

- **语言**：中文讲解为主，API 名 / 概念名 / 代码保留英文原文（便于检索官方文档）。
- **环境**：用户暂时没有 LLM API Key → 课程以**阅读代码、理解机制、离线自测**为主，
  不要求真实运行。所有代码块都是"读懂"的对象，而非"跑通"的对象。
- **覆盖范围**：官方左侧导航全部 35 个页面，一个不漏。
- **深度分层**：原理相关的核心章节做深（Tier A），集成/教程类章节做精炼但完整（Tier B）。

## 不在范围内（Non-goals）

- 不教 LangGraph 基础语法（只在需要解释 harness 机制时点到）。
- 不做前端 UI 的逐行实现教学（frontend 章节讲清架构与数据流即可）。
- 不追求"最少代码跑通 demo"，那是 quickstart 的职责，本课程只借用它作为解剖对象。

## 什么时候该回来改这份 MISSION

- 用户拿到 API Key，开始真实动手 → 需要把 Tier A 的部分章节从"读"改成"练"。
- 用户开始做一个具体产品 → 需要增加一条"从 harness 到产品"的支线。
- 用户发现某个模块才是真正的兴趣所在（例如只关心 context engineering）→ 收缩范围，加深该模块。

*创建于会话 1（2026-10-08）。*
