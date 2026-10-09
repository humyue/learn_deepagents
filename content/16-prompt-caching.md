---
num: 16
slug: prompt-caching
title: Prompt Caching：为什么它决定了栈的顺序
module: W3
tier: B
minutes: 8
desc: 静态前缀缓存如何把第 04 课的排序决策串起来
lede: 这一课很短，但它是理解第 04 课那条古怪排序规则的钥匙：为什么 MemoryMiddleware 被"发配"到缓存之后，而 SkillsMiddleware 被放在缓存之前。
source: https://docs.langchain.com/oss/python/deepagents/overview#prompt-caching
source_title: Overview · Prompt caching（官方）
---

## 机制

Prompt caching 的原理一句话：**把每次都一样的前缀缓存起来，下次跳过重复计算。**

对长跑的 agent 来说，这个前缀非常可观——它包含：

- 基础 agent 指令
- memory 内容
- skill 内容

官方原文：**对 Anthropic 与 Amazon Bedrock 模型，`create_deep_agent` 会自动对系统提示里的静态片段应用 prompt caching。**
"这避免在调用之间重复处理相同的 token，降低长跑 agent 的延迟与成本。"

## 默认行为

| 情况 | 行为 |
| - | - |
| Anthropic 模型 | 自动开启，无需配置 |
| Bedrock（Claude 或 Nova） | 自动开启，无需配置 |
| 其他供应商 | 两个缓存中间件都注册但 no-op；看 [Middleware integrations](https://docs.langchain.com/oss/python/integrations/middleware) 找provider 专属方案 |

!!! note "为什么两个中间件都"总是注册""
    官方说 Anthropic 与 Bedrock 两个 prompt caching middleware **都总是被注册**，
    但每个在不支持的模型上会 no-op（`unsupported_model_behavior="ignore"`）。

    这样设计的好处：**装配逻辑不需要根据模型分支。**
    你换模型时，缓存该开就开、该关就关，代码一行不改。
    ——这是"用 no-op 代替条件判断"的经典解耦手法，值得在自己的 middleware 里借鉴。

## 它如何解释第 04 课的排序

回到那条看起来不讲道理的规则：`MemoryMiddleware` 排在 caching **之后**。

现在你能自己推导出来了：

<div class="flow col">
  <div class="node"><span class="k">缓存的本质要求</span><span class="v">前缀必须逐字节稳定</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">memory 的本质</span><span class="v">agent 会写它 → 内容会变</span></div>
  <div class="arrow">↓</div>
  <div class="node hi"><span class="k">结论</span><span class="v">memory 必须排在缓存之后，否则每次写记忆都让缓存前缀失效</span></div>
</div>

反过来说，`SkillsMiddleware` 排在缓存**之前**也是同理：
技能内容在一次运行里是稳定的，把它纳入缓存前缀能省更多。

!!! key "可迁移的原则"
    **排序的依据不是"逻辑顺序"，而是"变化频率"。**
    稳定 → 靠前 → 进缓存；易变 → 靠后 → 不进缓存。

    你自己加 middleware 时，同样要问：我注入的内容会不会变？
    会变的话，我应该排在缓存中间件的后面。

```quiz
Q: 官方对 prompt caching 的默认行为描述是？
- 需要手动传入 PromptCachingMiddleware 才生效
- 对所有供应商的模型都自动生效
* 对 Anthropic 与 Bedrock 模型自动生效，无需配置
- 只在开启 write_todos 之后才生效
E: 官方说明：使用 Anthropic 模型，或支持缓存的 Bedrock 模型（Claude 或 Nova）时，prompt caching 默认开启，无需配置。其他供应商需另找方案。

Q: MemoryMiddleware 被排在 prompt caching 之后，是为了避免什么？
- 避免记忆内容覆盖技能内容
- 避免在缓存之前触发摘要
* 避免记忆更新导致缓存前缀失效
- 避免记忆内容被 excluded_tools 过滤
E: 官方在正文与代码注释中都点明：把记忆注入放在缓存之后，可以让记忆的更新尽量不使缓存前缀失效，因为 agent 会写记忆，内容会变。
```

## 下一课

上下文层还剩两块：一块是**你能自己加的状态**（`state_schema` 与 runtime context），
另一块是**非文本内容**（多模态）。先看前者——它是写自定义 middleware 的前提。
