---
num: 37
slug: content-builder-agent
title: 成品模式三：Content Builder Agent
module: W7
tier: B
minutes: 10
desc: 配置文件、脚本、以及"把领域知识放进文件而不是提示词"
lede: 第三个成品模式的看点不在代码，而在<b>它的目录结构</b>。这个模式里最重的一节是"Add configuration files"——这本身就是"把知识放进文件系统"这个设计哲学的实操演示。
source: https://docs.langchain.com/oss/python/deepagents/content-builder
source_title: Build a content builder agent（官方）
---

## 任务形状

"生成内容"听起来比"分析数据"轻，但它的难点在别处：**领域知识**。

一个能写高质量内容的 agent，需要知道：

| 需要知道什么 | 传统做法 | 这个模式的做法 |
| - | - | - |
| 语气与风格 | 写进 system prompt | **配置文件** |
| 结构与模板 | 写进 system prompt | **配置文件 / 模板文件** |
| 事实与素材 | 写进 system prompt | **数据文件 / 参考文件** |
| 校验规则 | 写进 system prompt | **脚本** |

!!! key "这就是 skills 模式的实战形态"
    官方给出的目录结构里，最重的一部分是配置与素材文件。

    这和第 13 课讲的 **渐进式披露** 是同一件事：
    - **常驻的**：一行 `description` 说"这个能力是干什么的"
    - **按需读的**：风格指南、模板、参考素材

    如果把风格指南整篇塞进 system prompt，那么每一次模型调用都要为它付费，
    哪怕这次任务根本不涉及那种内容。

## 结构

官方步骤的骨架是：

<div class="flow col">
  <div class="node"><span class="k">① Setup</span><span class="v">依赖与基础配置</span></div>
  <div class="node hi"><span class="k">② Add configuration files</span><span class="v">整个模式里最长的一节</span></div>
  <div class="node"><span class="k">③ Build the script</span><span class="v">把 agent 装配起来</span></div>
  <div class="node"><span class="k">④ Run the agent</span><span class="v">看产出</span></div>
</div>

**注意第 ② 步的长度**——它比第 ③ 步长得多。这个比例本身就是一个教学信号：

!!! note "内容类 agent 的工作量在"知识"，不在"代码""
    装配 agent 只需要那么几行（`create_deep_agent` + 工具 + 提示）。
    真正决定质量的，是你给它准备了什么知识、以什么粒度组织。

    这在一个"harness 已经帮你解决工程问题"的世界里是必然的结果：
    **工程难度下降后，瓶颈转移到内容与领域知识的质量上。**

## 关键概念

官方列的 "Key concepts" 里，值得单独点出的是：

| 概念 | 对应课程 |
| - | - |
| 用文件组织领域知识 | 第 06 课（虚拟文件系统）、第 13 课（skills） |
| 按需加载而不是全量注入 | 第 13 课（渐进式披露） |
| 用脚本承担确定性工作 | 第 10 课（解释器）/ 第 09 课（沙箱） |

!!! tip "什么该写进脚本"
    内容生产里有一批"确定性的脏活"很适合做成脚本：

    - 检查字数、标题层级、链接是否有效
    - 按模板填充变量
    - 从素材文件里抽取引用
    - 格式转换

    这些交给脚本，模型就不用"一边写作一边数标点"。
    **把确定性从模型手里拿走，是提高内容质量最便宜的一招。**

## 三个成品模式的横向对比

到这里三个模式都过了一遍，可以横向看一次：

| | Research | Data analysis | Content builder |
| - | - | - | - |
| 核心工具 | 搜索 | 沙箱执行 | 文件 + 模板 |
| 关键 backend | 默认即可 | **沙箱** | 文件系统 |
| 主要难点 | 上下文与综合 | 隔离与数据通道 | **领域知识组织** |
| 是否需任务规划 | 建议 | 建议（官方显式开启） | 视内容长度 |
| 典型前端模式 | Subagent 卡片 | 沙箱 IDE | Todo / 消息流 |

!!! key "这张表是可以外推的"
    面对你自己的任务，先问三个问题：

    1. **它需要读外部世界吗？**（→ 工具）
    2. **它需要动手执行吗？**（→ 沙箱/解释器）
    3. **它需要领域知识吗？**（→ 文件 + skills）

    三个答案决定你的架构骨架。

## 关于产出

官方有 "Output" 与 "Full code" 两节。值得注意的实践是：
**完整代码放在最后**。

这是一个很好的文档组织方式，也提示了学习路径：
**先理解概念与配置（为什么），再看完整代码（是什么）。**
反过来读，你会淹没在细节里而不知道每个文件为什么存在。

```quiz
Q: content builder agent 模式里最长的一节是什么，说明了什么？
- Build the script，说明装配代码最复杂
- Prerequisites，说明环境依赖最难配
* Add configuration files，说明工作量在领域知识组织而非装配代码
- Run the agent，说明调试占大部分时间
E: 官方在该模式中把 Add configuration files 写成最长的一节，而 Build the script 相对简短。这反映工程难度由 harness 承担后，瓶颈转移到知识与内容质量。

Q: 把风格指南放进配置文件而不是 system prompt，主要收益是什么？
- 让模型更容易理解风格
- 减少配置文件的维护成本
* 不必在每次模型调用中为它付费，只在相关任务时才读取
- 让风格指南可以跨语言复用
E: 这与渐进式披露是同一机制：常驻的只有描述，正文按需读取。塞进 system prompt 会让每轮调用都为它支付 token。

Q: 内容生产里把字数校验、格式转换这类工作做成脚本的理由是？
- 脚本比模型更了解文风
- 脚本可以并行处理多个文档
* 把确定性的工作从模型手里拿走，提高质量并降低成本
- 沙箱不允许模型执行这类操作
E: 模型不必一边写作一边做机械校验。确定性工作交给脚本后，模型可专注于需要判断力的部分，这是提升产出质量最直接的做法。
```

## 下一课

三个成品模式讲完了。剩下两个"更软"的章节，
但它们解决的是很硬的问题：**怎么让 agent 的输出质量可被自动评判**。
