---
kind: reference
sort: 2
slug: stack-order
title: 中间件栈速查
lede: 装配顺序、排序理由、以及 subagent 栈的差异。这一页是第 04 课的压缩形态，调试顺序相关问题时直接看这里。
desc: 完整装配顺序与每一层的排序理由
---

## 两条合并规则

1. **同名替换** —— 你传的实例如果 `.name` 与栈中某项相同，**就地替换**，不新增。
2. **否则追加** —— 其余全部插到 `PatchToolCallsMiddleware` **之后**、栈中其余部分之前。

## 完整栈（主 agent）

<div class="stack">
  <div class="layer req"><span class="idx">1</span><span class="nm">FilesystemMiddleware</span><span class="ds">文件读写导航；传了 permissions 时权限执法也在这里（要评估 agent 可能调用的每一个工具）</span></div>
  <div class="layer opt"><span class="idx">2</span><span class="nm">SubAgentMiddleware</span><span class="ds">仅当至少有一个同步 subagent。提供 <code>task</code> 工具</span></div>
  <div class="layer req"><span class="idx">3</span><span class="nm">SummarizationMiddleware</span><span class="ds">压缩消息历史</span></div>
  <div class="layer req"><span class="idx">4</span><span class="nm">PatchToolCallsMiddleware</span><span class="ds">修复悬空 tool call 与畸形参数</span></div>
  <div class="layer opt"><span class="idx">5</span><span class="nm">AsyncSubAgentMiddleware</span><span class="ds">仅当配置了异步 subagent</span></div>
  <div class="layer opt"><span class="idx">6</span><span class="nm">你传入的 middleware</span><span class="ds">同名替换，其余落在此处</span></div>
  <div class="layer opt"><span class="idx">7</span><span class="nm">Harness profile extras</span><span class="ds">来自解析后的模型 profile 的供应商专属 middleware</span></div>
  <div class="layer opt"><span class="idx">8</span><span class="nm">SkillsMiddleware</span><span class="ds">仅当传了 skills；在 prompt caching 之前</span></div>
  <div class="layer req"><span class="idx">9</span><span class="nm">Prompt caching</span><span class="ds">Anthropic + Bedrock 各一个，总是注册，不适用的模型上 no-op</span></div>
  <div class="layer opt"><span class="idx">10</span><span class="nm">MemoryMiddleware</span><span class="ds">仅当传了 memory；刻意排在缓存之后</span></div>
  <div class="layer opt"><span class="idx">11</span><span class="nm">HumanInTheLoopMiddleware</span><span class="ds">仅当传了 interrupt_on</span></div>
  <div class="layer opt"><span class="idx">12</span><span class="nm">Excluded-tool filtering</span><span class="ds">按 profile 的 excluded_tools 摘掉工具（后置过滤）</span></div>
</div>

## 排序理由速查

| 位置事实 | 原因 |
| - | - |
| Patch 排第 4（很早） | 它是"除锈工"。必须让摘要、缓存、记忆读到的历史是干净的 |
| 缓存排在你传入的 middleware **之后** | 你自己加的 prompt 修改也要被纳入缓存前缀 |
| 缓存排在 Skills **之后** | skill 内容在一次运行里稳定，纳入缓存省更多 |
| 缓存排在 Memory **之前** | memory 会被 agent 更新；排后面可避免缓存前缀失效 |
| 文件系统排第 1 | 权限执法要拦住 agent 可能调用的**每一个**工具 |
| Excluded-tool 排最后 | 要等所有 middleware 注入完工具才知道最终集合 |

!!! key "一条可迁移的排序原则"
    **依据不是逻辑先后，而是「变化频率」：稳定 → 靠前 → 进缓存；易变 → 靠后 → 不进缓存。**

## subagent 栈的差异

| middleware | 主 agent | 同步 subagent |
| - | - | - |
| FilesystemMiddleware | 有 | 有 |
| **SubAgentMiddleware（task 工具）** | 有 | **没有** |
| SummarizationMiddleware | 有 | 有 |
| PatchToolCallsMiddleware | 有 | 有 |
| Profile extras | 有 | 有 |
| SkillsMiddleware | 有 | 有 |
| Prompt caching | 有 | 有 |
| Permissions | 有 | 有（声明式 subagent **不继承**父级，需自己配） |

**理由**：只有父 agent 暴露 `task` 工具。若 subagent 也能开 subagent，递归委派会失控。

!!! note "subagent 的 interrupt_on 走另一条路"
    声明式 subagent 设置 `interrupt_on` 时，该值被**转发给 `create_agent`**，由它自己接上 HITL，而不是复用父 agent 的 `HumanInTheLoopMiddleware`。

## 默认不含的项目

| 能力 | 怎么开 |
| - | - |
| `write_todos` | `middleware=[TodoListMiddleware()]`（v0.7 起 opt-in） |
| 长期记忆 | `memory=[...]` |
| 技能 | `skills=[...]` |
| 人工批准 | `interrupt_on={...}` |
| 代码执行 | 换 sandbox backend |
| 结构化输出 | `response_format=` |
| 异步 subagent | 配置 async subagent |

## 不能排除的三项

在 `excluded_middleware` 里列出会抛 `ValueError`：

- `FilesystemMiddleware`
- `SubAgentMiddleware`
- 内部权限 middleware

替代方案：用 `excluded_tools` 隐藏它们的工具；用
`GeneralPurposeSubagentProfile(enabled=False)` 关闭委派能力。

## 自定义 state 的继承

| subagent 类型 | 继承父级 `state_schema` |
| - | - |
| 声明式 `SubAgent`（dict） | 继承 |
| `CompiledSubAgent` | 不继承 |
| 远程 `AsyncSubAgent` | 不继承 |
