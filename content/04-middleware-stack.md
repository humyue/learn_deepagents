---
num: 4
slug: middleware-stack
title: Middleware 栈：harness 的骨架
module: W1
tier: A
minutes: 14
desc: 完整装配顺序，以及每一步为什么排在那里
lede: 这是整个模块 A 最重要的一课。<code>create_deep_agent</code> 的装配顺序不是随手写的——它决定了缓存命中率、摘要看到什么、权限能拦住谁。读完这一课，你就能对任何一次调用画出准确的调用链。
source: https://docs.langchain.com/oss/python/deepagents/customization#deep-agents-stack
source_title: Customize Deep Agents · Deep Agents stack（官方）
---

## 先记住两条合并规则

在你传入的 middleware 和默认栈之间，只有两条规则：

1. **同名替换**：你传的实例如果 `.name` 与栈中某个内建项相同，就**就地替换**它，不会重复添加。
2. **否则追加**：名字不匹配的，全部插到 `PatchToolCallsMiddleware` **之后**、栈中其余部分之前。

理解这两条，你就知道为什么"传一个叫 `FilesystemMiddleware` 的实例"能覆盖默认的文件系统行为。

## 完整栈，从第一到最末

<div class="stack">
  <div class="layer req"><span class="idx">1</span><span class="nm">FilesystemMiddleware</span><span class="ds">文件读写导航。<b>传了 permissions 时，权限执法也在这里</b>——因为它要评估 agent 可能调用的每一个工具</span></div>
  <div class="layer opt"><span class="idx">2</span><span class="nm">SubAgentMiddleware</span><span class="ds">仅当至少有一个同步 subagent 时存在。负责派生与协调 subagent</span></div>
  <div class="layer req"><span class="idx">3</span><span class="nm">SummarizationMiddleware</span><span class="ds">会话变长时压缩消息历史（由 create_summarization_middleware 构造）</span></div>
  <div class="layer req"><span class="idx">4</span><span class="nm">PatchToolCallsMiddleware</span><span class="ds">修复恢复运行时残留的悬空 tool call；也处理畸形的 tool-call 参数</span></div>
  <div class="layer opt"><span class="idx">5</span><span class="nm">AsyncSubAgentMiddleware</span><span class="ds">仅当你配置了异步 subagent 时存在</span></div>
  <div class="layer opt"><span class="idx">6</span><span class="nm">你传入的 middleware</span><span class="ds">同名替换，其余落在这里（Patch 之后、后续所有项之前）</span></div>
  <div class="layer opt"><span class="idx">7</span><span class="nm">Harness profile extras</span><span class="ds">来自解析后的模型 profile 的供应商专属 middleware</span></div>
  <div class="layer opt"><span class="idx">8</span><span class="nm">SkillsMiddleware</span><span class="ds">仅当你传了 skills。位置很讲究：在 prompt caching 之前</span></div>
  <div class="layer req"><span class="idx">9</span><span class="nm">Prompt caching</span><span class="ds">Anthropic 与 Bedrock 各一个，总是注册，跑在 Patch 与你传入的 middleware 之后</span></div>
  <div class="layer opt"><span class="idx">10</span><span class="nm">MemoryMiddleware</span><span class="ds">仅当你传了 memory。被刻意排在缓存之后</span></div>
  <div class="layer opt"><span class="idx">11</span><span class="nm">HumanInTheLoopMiddleware</span><span class="ds">仅当你传了 interrupt_on</span></div>
  <div class="layer opt"><span class="idx">12</span><span class="nm">Excluded-tool filtering</span><span class="ds">profile 里列出的 excluded_tools 在最后被摘掉</span></div>
</div>

## 为什么是这个顺序：四条推理

### 推理一：Patch 必须很早，因为它是"除锈工"

`PatchToolCallsMiddleware` 处理的是**历史里的垃圾**：
一次运行被 interrupt 打断、或者模型生成了畸形的工具调用参数，消息历史里就会留下
"有 `tool_call` 但没有对应 `ToolMessage`"的悬空记录。下一次调用模型时，
这种历史会直接导致 API 报错。

它排在第 4 位，意味着：**在摘要、缓存、记忆这些"读历史"的环节之前，历史已经被修干净了。**
否则摘要会把垃圾一起摘要进去，缓存会把垃圾一起缓存起来。

### 推理二：缓存必须晚于一切会改 prompt 的东西

Prompt caching 的原理是把**不变的前缀**缓存起来，下次跳过重复计算。
只要前缀里有一个字节变了，缓存就整段失效。

所以：

- 它排在你传入的 middleware **之后** → 你自己加的 prompt 修改也被纳入缓存前缀
- 它排在 `SkillsMiddleware` **之后** → skill 内容先注入，再一起缓存
- 它排在 `MemoryMiddleware` **之前** → **这是刻意设计的**

官方在注释里写了原因：`MemoryMiddleware` 注入的记忆内容**会更新**（agent 可以写记忆文件）。
如果它在缓存之前，那么每次记忆更新都会让缓存前缀失效。
把它放在缓存**之后**，记忆更新就只影响尾部，不污染可缓存的前缀。

!!! key "一条可迁移的设计原则"
    **排序的依据不是"逻辑上谁先谁后"，而是"谁变化、谁稳定"。**
    稳定的排前面（进缓存），易变的排后面（不进缓存）。
    这条原则在你自己写 middleware 时会反复用到。

### 推理三：权限必须在工具之前

`FilesystemMiddleware` 之所以同时承担权限执法，是因为**权限要能拦住 agent 可能调用的每一个工具**，
而不是只拦文件系统工具。放在第 1 位意味着它是链条上最外层的关卡。

### 推理四：Excluded-tool 过滤在最后

因为它是**后置过滤器**（post-injection filter）：
要等所有 middleware 都把自己的工具注入完了，才知道最终工具集合长什么样，
这时再按名字摘掉 `excluded_tools` 里列出的那些。
这也解释了为什么 `excluded_tools` 能同时删掉"用户传入的工具"和"harness middleware 注入的工具"。

## subagent 用的是另一套栈

一个重要的不对称：**subagent 图里没有 `SubAgentMiddleware`。**

| | 主 agent | 同步 subagent |
| - | - | - |
| FilesystemMiddleware | ✅ | ✅ |
| SubAgentMiddleware（`task` 工具） | ✅ | ❌ **没有** |
| SummarizationMiddleware | ✅ | ✅ |
| PatchToolCallsMiddleware | ✅ | ✅ |
| Profile extras | ✅ | ✅ |
| SkillsMiddleware | ✅ | ✅ |
| Prompt caching | ✅ | ✅ |
| Permissions | ✅ | ✅（声明式 subagent 不继承父级，需要自己配） |

理由很直白：**只有父 agent 暴露 `task` 工具**。如果 subagent 也能开 subagent，
递归委派很快就会失控，而且没有任何一层能保证收敛。

!!! note "subagent 的 interrupt_on 走另一条路"
    声明式 subagent 如果设置了 `interrupt_on`，这个值会被**转发给 `create_agent`**，
    由它自己接上 human-in-the-loop，而不是复用父 agent 的 `HumanInTheLoopMiddleware`。

## 怎么自己验证这个顺序

最可靠的办法是读源码——装配顺序写在 `create_deep_agent` 的实现里，
官方文档也特意提示"同样的排序考虑在 `create_deep_agent` 实现注释里被点出来"。

第二条路是观测：开启 `debug=True` 或用 `stream_mode="debug"`，
你会看到按节点名发出的内部步骤。文档里也给了过滤噪音的写法：

```python
# 只显示有意义的节点名，跳过内部 middleware 步骤
for chunk in agent.stream(input, stream_mode="debug"):
    if chunk["name"] in {"model", "tools"}:   # 视你的栈而定
        ...
```

```quiz
Q: MemoryMiddleware 被排在 prompt caching 之后的根本原因是？
- 它需要先读取 skills 才能决定注入什么
- 它必须在 HumanInTheLoop 之前执行
* 记忆内容会被 agent 更新，排后面可避免缓存前缀失效
- 它依赖 PatchToolCalls 已经修复过的历史
E: 官方在正文与实现注释里都点明了：把记忆注入放在缓存之后，可以让记忆的更新尽量不使缓存前缀失效。这是一个"谁稳定谁靠前"的排序决策。

Q: 你自己传入的 middleware，如果名字和内建项都不相同，会被放在哪里？
- 栈的最前面，优先于文件系统
- 栈的最后面，晚于 excluded-tool 过滤
* PatchToolCallsMiddleware 之后、其余项之前
- SubAgentMiddleware 与 SummarizationMiddleware 之间
E: 官方表述是 "inserted after PatchToolCallsMiddleware"。同名实例则就地替换，不会新增一层。

Q: 关于 subagent 的 middleware 栈，哪个说法正确？
- 它与父 agent 栈完全相同，包括 SubAgentMiddleware
- 它只有 FilesystemMiddleware 与 SummarizationMiddleware
* 它与父栈形态相近，但没有 SubAgentMiddleware，即没有 task 工具
- 它完全不使用 middleware，只用裸模型调用
E: 只有父 agent 暴露 task 工具。subagent 图保留文件系统、摘要、Patch、profile extras、skills、缓存与可选权限，但没有 SubAgentMiddleware。

Q: FilesystemMiddleware 同时承担权限执法的原因是什么？
- 因为权限规则只适用于文件路径
- 因为它是栈里唯一能访问 backend 的一层
* 因为它需要评估 agent 可能调用的每一个工具
- 因为权限检查必须晚于工具实际执行
E: 官方解释是：传入 permissions 时，文件系统权限执法被包含在 FilesystemMiddleware 里，以便它能评估 agent 可能调用的每一个工具——而不只是文件系统工具。
```

## 下一课

模块 A 结束。从这里开始进入**执行环境**——
agent 的"手"到底长什么样。第一个要拆的，是工具本身。
