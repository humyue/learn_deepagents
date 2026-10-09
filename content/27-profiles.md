---
num: 27
slug: profiles
title: Profiles：让同一份代码适配不同模型
module: W5
tier: A
minutes: 13
desc: harness profile 与 provider profile、查找顺序、合并语义
lede: 模型之间差异很大：有的不支持某些工具，有的需要不同的提示风格，有的要特殊参数。如果把适配逻辑写进 <code>create_deep_agent</code> 调用处，你的代码会变成一堆 <code>if provider == ...</code>。Profile 是官方给的解法。
source: https://docs.langchain.com/oss/python/deepagents/profiles
source_title: Profiles（官方）
---

## 两种 profile，别搞混

<div class="compare">
<div class="yes">
<h4>Harness profile（关注 harness）</h4>
<ul>
<li>调整系统提示、工具描述</li>
<li>排除工具或 middleware</li>
<li>增加 middleware</li>
<li>配置 general-purpose subagent</li>
<li><b>会改变 agent 的行为</b></li>
</ul>
</div>
<div class="no">
<h4>Provider profile（关注构造）</h4>
<ul>
<li>temperature、timeout 等默认值</li>
<li>共享的凭据检查</li>
<li>运行时计算的设置</li>
<li><b>不影响 harness</b></li>
</ul>
</div>
</div>

官方对 provider profile 的定位很明确：
**大多数调用者不需要它。** 它主要给"打包一个集成"的库作者用。

所以**这一课的重点是 harness profile**。

## 核心价值：把适配从调用处移走

先看它解决的问题：

```python
# 没有 profile 的世界
if model_name.startswith("openai"):
    agent = create_deep_agent(model=model, system_prompt=prompt + "\nRespond in under 100 words.")
    ...
elif "bedrock" in model_name:
    ...
```

有了 harness profile，适配变成**注册式**的：

```python
from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    register_harness_profile,
)

register_harness_profile(
    "openai:gpt-6-astra",
    HarnessProfile(
        system_prompt_suffix="Respond in under 100 words.",
        excluded_tools={"execute"},
        excluded_middleware={"SummarizationMiddleware"},
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    ),
)

# 调用处完全不知道这些差异存在
agent = create_deep_agent(model="openai:gpt-6-astra", ...)
```

!!! key "这是"关注点分离"的教科书案例"
    **调用处表达意图（我要一个研究 agent）；profile 表达适配（这个模型需要这样照顾）。**
    换模型时，不需要改任何调用代码。

    而且 profile 可以**打包成 plugin 分发**——一个供应商的支持者可以把适配逻辑
    做成一个包，用户装上就生效。

## 字段全清单

| 字段 | 作用 |
| - | - |
| `base_system_prompt` | 设置该 profile 的基础指令。对主 agent 来说**跟在调用方指令之后**；对声明式 subagent 来说**替换**它自己写的提示 |
| `system_prompt_suffix` | 追加在最后。对**主 agent、声明式 subagent、自动添加的 general-purpose subagent 都生效** |
| `tool_description_overrides` | 按工具名覆盖工具描述 |
| `excluded_tools` | 移除 harness 级工具（按名字匹配，**后置过滤**） |
| `excluded_middleware` | 从栈里剥掉指定 middleware（类或字符串名都行） |
| `extra_middleware` | 给该 profile 适用的每个栈追加 middleware |
| `general_purpose_subagent` | 禁用、改名、改提示 |

!!! note "prompt 位置的两条铁律"
    官方特意用 Note 框强调：

    1. **调用方提供的 `system_prompt` 永远在拼装结果的最前面。**
    2. **`system_prompt_suffix` 永远在最后。**
    3. 无论最终选中哪个模型，这两条都成立。

    而且 **subagent 会重新跑一遍 profile 解析**——它按自己的模型解析，不是继承父级结果。

## 查找顺序（传模型对象时）

当你传的是一个已经构造好的模型实例，harness 要靠它自报的 provider 与 identifier 去查 profile：

<div class="flow col">
  <div class="node hi"><span class="idx"></span><span class="k">1. 精确匹配</span><span class="v">provider:identifier</span></div>
  <div class="arrow">↓ 没有</div>
  <div class="node"><span class="k">2. 只用 identifier</span><span class="v">仅当 identifier 本身已含冒号</span></div>
  <div class="arrow">↓ 没有</div>
  <div class="node"><span class="k">3. provider 默认</span><span class="v">provider 未知时，退回 identifier 前缀的默认</span></div>
</div>

官方注明：**两个精确候选都优先于 provider 默认。**

## 注册键：两级

```python
# provider 级：对该 provider 的所有模型生效
register_harness_profile(
    "my_provider",
    HarnessProfile(
        excluded_tools=frozenset({"execute"}),
        system_prompt_suffix="Respond in under 500 words.",
    ),
)

# model 级：只对该模型生效，未设字段继承 provider 级
register_harness_profile(
    "my_provider:my-model:tag",
    HarnessProfile(system_prompt_suffix="Respond in under 100 words."),
)
```

!!! warning "只有第一个冒号是分隔符"
    对键 `my_provider:my-model:tag`：
    - provider 是 `my_provider`
    - **完整的 model identifier 是 `my-model:tag`**（后面所有冒号都属于它）

    这个细节在配置 provider 名字里本身带冒号时很关键。

还有一条容易踩的：

!!! trap "没有通配符键"
    官方明确说：**不存在一个匹配所有 provider 的通配键。**
    如果你想让某个调整对所有模型生效，必须在每个用到的 provider 键下各注册一次。

    官方的指导是：**profile 是给"取决于所选模型"的调整用的；
    与模型无关的全局调整应该写在 `create_deep_agent` 调用处。**

## 合并语义

这条很重要，因为**重复注册是"叠加"而不是"替换"**：

| 字段 | 合并行为 |
| - | - |
| `base_system_prompt`、`system_prompt_suffix` | 设了就赢，否则继承 |
| `tool_description_overrides` | 按键合并，同键新值胜 |
| `excluded_tools`、`excluded_middleware` | **集合并集** |
| `extra_middleware` | 按具体类型合并：新实例替换原有位置的实例，新类型追加 |
| `general_purpose_subagent` | 逐字段合并，未设的继承 |
| `init_kwargs`（provider） | 字典按键合并 |
| `pre_init`（provider） | 可调用对象链式执行：先原有，再新的 |
| `init_kwargs_factory`（provider） | 工厂链式执行并在每次构造模型时合并输出 |

**"重复注册会合并不是替换"有一个直接推论**：
你可以**在官方内建 profile 的键上注册**，从而定制它，而不是从零重写。

## `excluded_middleware` 的两种写法

| 写法 | 用途 |
| - | - |
| 类本身，或匹配 `AgentMiddleware.name` 的字符串 | 内建与公开别名，如 `"SummarizationMiddleware"` |
| `module:Class` 导入引用 | 从配置文件里精确指定某个类 |

!!! trap "导入引用会执行 Python 代码"
    官方明确警告：导入引用是**惰性解析**的，只能用在你信任的本地配置上
    ——**加载一个就会 import 一段 Python 代码。**

## 三条必记的硬约束

!!! warning "以下 middleware 不能排除"
    在 `excluded_middleware` 里列出 **`FilesystemMiddleware`、`SubAgentMiddleware`
    或内部权限 middleware**，会直接抛 `ValueError`——它们是必需脚手架。

    想隐藏它们的工具，用 `excluded_tools`；想去掉 subagent 能力，
    用 `general_purpose_subagent.enabled = False`（第 19 课）。

!!! tip "`excluded_tools` 是后置过滤器"
    因为它按名字匹配、并且在**所有 middleware 都注入完工具之后**才执行，
    所以它既能删掉用户传入的工具，也能删掉 harness middleware 加的工具。
    这是它比"在 create_deep_agent 里少传几个工具"更强的地方。

```quiz
Q: 在 provider 级与 model 级 profile 同时存在时，合并规则是？
- model 级的整体替换 provider 级
- provider 级优先，model 级只能追加 middleware
* 未设的 model 级字段继承 provider 级，显式设置的值覆盖
- 两者互不影响，分别独立生效
E: 官方说明：两者在解析时合并。未设置的 model 级字段从 provider 级继承，显式设置的 model 级值覆盖。

Q: 关于注册键 my_provider:my-model:tag，正确的解析是？
- provider 是 my_provider，model 是 my-model
- provider 是 my_provider:my-model，model 是 tag
* provider 是 my_provider，model identifier 是 my-model:tag
- 该键非法，只能有一个冒号
E: 官方明确只有第一个冒号分隔 provider 与模型标识，其余冒号都属于 model identifier。

Q: 想移除 execute 工具，为什么应该用 excluded_tools 而不是 excluded_middleware？
- 因为 excluded_middleware 只能移除 middleware 类
- 因为 excluded_tools 的性能开销更低
* 因为 FilesystemMiddleware 是必需脚手架，移除会报错
- 因为 execute 是由 SubAgentMiddleware 注入的
E: 官方警告在 excluded_middleware 里列 FilesystemMiddleware、SubAgentMiddleware 或内部权限 middleware 会抛 ValueError。隐藏模型可见的工具应该用 excluded_tools。

Q: 重复在同一个键上注册 profile，结果是？
- 新 profile 完全替换旧的
- 只保留最后一次注册的字段
* 新的 profile 合并到旧的之上，并非替换
- 后一次注册会被忽略并告警
E: 官方说明：在已有键上重新注册会把新 profile 合并到之前的之上，而不是替换。这也让定制内建 profile 成为可能。
```

## 模块 E 结束

管控层讲完了：中断、容错、profile。
下一模块换一个视角——**agent 在跑的时候，前端怎么看见它在干什么？**
