---
num: 26
slug: fault-tolerance
title: 容错：不是所有错误都该被同样对待
module: W5
tier: B
minutes: 10
desc: 六类错误、五种中间件、以及"哪个错误该由谁修"的分类法
lede: 这一课的核心不是 API，而是一张<b>分类表</b>。Deep Agents 的容错设计有一个很清晰的判断标准：<em>这个错误该由谁修？</em>系统、模型，还是人？
source: https://docs.langchain.com/oss/python/deepagents/fault-tolerance
source_title: Fault tolerance（官方）
---

## 分类法：谁该修这个错

官方给的第一张表就是全课最有价值的内容：

| 错误类型 | 谁来修 | 策略 | 对应机制 |
| - | - | - | - |
| **瞬时错误**（网络问题、限流） | 系统（自动） | 指数退避重试 | `ModelRetryMiddleware`、`ToolRetryMiddleware` |
| **LLM 可恢复的错误**（工具失败、解析问题） | 模型 | 转成错误 `ToolMessage`，让模型自己调整 | `ToolErrorMiddleware` |
| **用户可修复的错误**（信息缺失、指令不清） | 人 | 用 `interrupt()` 暂停 | Human-in-the-loop（第 25 课） |
| **供应商故障** | 系统（自动） | 降级到备用模型 | `ModelFallbackMiddleware` |
| **调用过多**（失控循环） | 系统（自动） | 限制每次运行的模型/工具调用次数 | `ModelCallLimitMiddleware`、`ToolCallLimitMiddleware` |
| **意外错误** | 开发者 | 让它抛出来 | 不用中间件，让异常冒泡 |

!!! key "这张表的思维方式才是要学的"
    大多数人的第一反应是"出错就重试"。但官方这张表里，
    **只有第一行和第四行是重试**。

    - 工具返回了一个坏结果 → 重试没有意义，**模型需要看到错误才能改**
    - 用户没说清楚 → 重试一百次也不会有答案，**必须问人**
    - 代码里有个 `KeyError` → 重试只会掩盖 bug，**应该让它炸出来**

    **"错误处理"的第一步永远是分类，不是加 try/except。**

## 瞬时错误：两种重试中间件

模型调用与工具调用各有自己的重试中间件，都支持指数退避：

```python
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware

middleware=[
    ModelRetryMiddleware(max_retries=3, backoff_factor=2.0, initial_delay=1.0),
    ToolRetryMiddleware(
        max_retries=2,
        tools=["search", "fetch_url"],                  # 只对指定工具重试
        retry_on=(TimeoutError, ConnectionError),       # 只对指定异常重试
    ),
]
```

值得注意的是**为什么要分开**：

<div class="flow">
  <div class="node"><span class="k">模型调用</span><span class="v">贵、慢、限流多 → 重试要更保守</span></div>
  <div class="arrow">vs</div>
  <div class="node"><span class="k">工具调用</span><span class="v">便宜、快、幂等性不定 → 可按工具配置</span></div>
</div>

`ToolRetryMiddleware` 的 `tools=` 与 `retry_on=` 两个参数是安全阀：
**只对你确认为幂等的工具、只对可恢复的异常重试。**

!!! trap "对非幂等操作重试是危险的"
    "发邮件"、"下单"、"删除文件"这类工具重试可能产生重复副作用。
    这不是框架能替你判断的，**是你要判断的**。
    这也是 `tools=` 参数存在的理由。

## LLM 可恢复的错误：把异常变成消息

这一条设计得非常漂亮：

```python
from langchain.agents.middleware import ToolErrorMiddleware
```

它捕获工具抛出的异常，**转成一条错误 `ToolMessage`**，
于是模型能看到"这个工具失败了，原因是 X"，然后自己换个参数或换条路。

<div class="flow">
  <div class="node"><span class="k">工具抛异常</span><span class="v">ValueError: bad param</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">转成 ToolMessage</span><span class="v">"Error: bad param"</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">模型自己修正</span><span class="v">换个参数再试</span></div>
</div>

!!! note "版本要求"
    官方注明 `ToolErrorMiddleware` 需要 `langchain>=1.3.14`。

## 供应商故障：降级

```python
from langchain.agents.middleware import ModelFallbackMiddleware
```

当主模型供应商挂掉时，自动切到备用模型。
这和"重试"解决的是不同的问题：**重试处理瞬时抖动，降级处理持续不可用。**

## 失控循环：调用限额

| 中间件 | 限制什么 |
| - | - |
| `ModelCallLimitMiddleware` | 每次运行的模型调用次数 |
| `ToolCallLimitMiddleware` | 每次运行的工具调用次数 |

!!! tip "这类中间件在生产上几乎是必需的"
    一个陷入循环的 agent 能在几分钟内烧掉大量 token。
    限额的作用不是"优化"，而是**给成本一个上界**。

    注意它和"中断"是互补的：中断处理"这一次调用危险"，
    限额处理"整体次数失控"。

## 一个反面提示

官方表格最后一行很有意思：**意外错误 → 不用中间件，让它冒泡。**

这提醒我们：容错不是"把所有异常都吞掉"。
**把不该处理的错误处理掉，等于把 bug 藏起来。**
一个 `null` 被静默替换成空字符串，可能让你在两周后才发现问题。

```quiz
Q: 工具因为参数格式错误而失败，官方推荐的策略是什么？
- 用 ToolRetryMiddleware 指数退避重试
* 用 ToolErrorMiddleware 转成错误消息交给模型
- 用 ModelFallbackMiddleware 切换到备用模型
- 让它冒泡到上层由开发者处理
E: 这属于"LLM 可恢复的错误"：模型看到错误消息后可以自己修正参数。重试同样的错误参数不会带来不同结果。

Q: ToolRetryMiddleware 的 tools 参数存在的主要理由是什么？
- 减少配置文件的体积
- 让重试只对模型调用生效
* 避免对非幂等工具重试而重复产生副作用
- 让重试支持并行执行多个工具
E: 对发邮件、下单、删除这类非幂等操作重试可能造成重复副作用。官方设计允许按工具白名单配置重试，安全判断留给开发者。

Q: "意外错误让它冒泡"这条官方建议说明了什么？
- 框架无法捕获未定义的异常类型
- 冒泡比中间件处理性能更好
* 不该处理的错误被吞掉会掩盖真正的 bug
- 只有 LangGraph 运行时才需要处理这类错误
E: 官方表格把"意外错误"归给开发者，策略是"不用中间件，让异常传播"。静默吞掉异常会把 bug 藏起来，延后暴露时间。

Q: 调用限额中间件与 human-in-the-loop 中断的关系是？
- 两者解决同一个问题，选一个即可
- 限额是中断的实现基础
* 中断管"单次调用危险"，限额管"整体次数失控"
- 限额只在沙箱 backend 下生效
E: 中断针对某一次具体调用的审批，调用限额针对整个运行的模型与工具调用总量，用于给成本设上界。两者是互补的两层防护。
```

## 下一课

容错处理的是"运行时出问题"。还剩最后一个横切面：
**同一份代码怎么在不同模型上表现一致？** 答案是 profile。
