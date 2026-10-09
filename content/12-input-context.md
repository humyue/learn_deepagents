---
num: 12
slug: input-context
title: 输入上下文：prompt 是怎么被拼出来的
module: W3
tier: B
minutes: 10
desc: 四个来源拼成一个 system prompt，以及静态与动态的分界
lede: 你只写了一个 <code>system_prompt</code>，但模型收到的 prompt 里还有别的东西。这一课讲清那几样东西从哪来、按什么顺序拼、以及什么时候该换成动态提示。
source: https://docs.langchain.com/oss/python/deepagents/context-engineering#input-context
source_title: Context engineering · Input context（官方）
---

## 四个来源

<div class="stack">
  <div class="layer req"><span class="idx">1</span><span class="nm">System prompt</span><span class="ds">你写的自定义指令 + harness 内建的 agent 指引</span></div>
  <div class="layer opt"><span class="idx">2</span><span class="nm">Memory</span><span class="ds">AGENTS.md 文件，<b>总是加载</b>（传了 memory= 才有）</span></div>
  <div class="layer opt"><span class="idx">3</span><span class="nm">Skills</span><span class="ds">技能内容，<b>按需加载</b>（渐进式披露，传了 skills= 才有）</span></div>
  <div class="layer req"><span class="idx">4</span><span class="nm">Tool prompts</span><span class="ds">内建工具或自定义工具的说明文字</span></div>
</div>

关键区别在第 2 与第 3 条：

| | Memory | Skills |
| - | - | - |
| 加载时机 | **总是**，启动即加载 | 启动只读 frontmatter，**按需**读正文 |
| 适合装什么 | 约定、偏好、必须一直遵守的规则 | 特定领域的工作流程与知识 |
| 代价 | 每轮都占 token | 不激活时几乎不占 |

!!! key "这是同一枚硬币的两面"
    **Memory 用 token 换"永远不会忘"；Skills 用"可能要多一次 read_file"换"不用时不花钱"。**
    判断标准是：这条信息**每个任务都会用到吗**？
    是 → memory；只在特定任务才用到 → skill。

## 你的 prompt 落在哪个位置

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    system_prompt=(
        "You are a research assistant specializing in scientific literature. "
        "Always cite sources. Use subagents for parallel research on different topics."
    ),
)
```

**你的 `system_prompt` 被前置（prepended）**，后面接的是 harness 内建指引——
文件系统工具怎么用、subagent 怎么用等等。

!!! note "profile 可以改这一段"
    按模型/供应商调整 prompt 时用 harness profile（第 27 课）：
    - `base_system_prompt` — **整体替换**基础提示
    - `system_prompt_suffix` — **追加**在最后

    合并的规律是：**调用方提供的 `system_prompt` 永远在最前，`system_prompt_suffix` 永远在最后**，
    无论最终选的是哪个模型。

## 静态 vs 动态

`system_prompt` 是**静态**的：它不会随调用变化。但有些指令天然需要变化：

- "你有管理员权限" vs "你是只读权限"
- "用户偏好简洁回答"（这条偏好存在长期记忆里，每个用户不同）

这时用 `@dynamic_prompt`，从 `request.runtime.context` 或 `request.runtime.store` 里取：

```python
# 概念示意：prompt 依赖运行时上下文
@dynamic_prompt
def per_user_prompt(request) -> str:
    prefs = request.runtime.store.get(("user",), "preferences")
    return f"You are a research assistant. User preferences: {prefs}"
```

!!! tip "先别写 middleware"
    官方特意加了一句提醒：**如果只有工具需要用到 context 或 store，不需要 middleware。**
    工具本身就能拿到 `ToolRuntime`（含 `runtime.context` 与 `runtime.store`）。
    只有当你需要**把工具和一次系统提示更新打包在一起**时，才值得写 middleware。

## 完整系统提示长什么样

官方文档里有一节 "Complete system prompt"，把拼装后的结果完整列了出来。
值得去读一遍原文——你会直观看到：

- harness 注入的指引相当长（有具体的工具使用规范和输出约定）
- 你的业务 prompt 只占其中一小段
- 工具说明本身占据了可观的比例

这解释了一个实践建议：**不要把 harness 已经说清楚的事再写一遍。**
重复指令既浪费 token，又可能和框架的指引产生冲突。

```quiz
Q: 判断一条信息该进 memory 还是该做成 skill，标准是什么？
- 信息是文本还是代码
- 信息来自用户还是来自开发者
* 它是否每个任务都会用到
- 信息长度是否超过一千个字符
E: memory 总是加载、每轮都占 token；skill 只在相关任务时按需读取。因此判断标准是这条信息的使用频率与普适性。

Q: 关于 system_prompt_suffix 的位置，官方是怎么保证的？
- 它排在调用方 system_prompt 之前
- 它插在 memory 与 skills 之间
* 它永远在所有内容之后，无论选了哪个模型
- 它只在未提供 system_prompt 时才生效
E: 官方说明：调用方提供的 system_prompt 永远位于拼装结果的最前，system_prompt_suffix 永远位于最后，与所选的模型无关。

Q: 什么时候需要给工具写 middleware 来传递上下文？
- 只要工具需要用户身份就必须写
- 只要工具需要读取 store 就必须写
* 只有当工具需要连带更新系统提示时
- 只要工具调用次数超过限额就必须写
E: 工具本身可以直接接收 ToolRuntime（包括 runtime.context 与 runtime.store）。middleware 只在"把工具与一次系统提示更新打包"时才有必要。
```

## 下一课

Memory 是"总是加载"，Skills 是"按需加载"。后者是文档里最精巧的机制之一——
**渐进式披露（progressive disclosure）**，值得单独一课。
