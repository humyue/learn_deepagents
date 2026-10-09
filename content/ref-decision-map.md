---
kind: reference
sort: 4
slug: decision-map
title: 选型决策图
lede: 遇到"我该用哪个"的时候翻这里。每一节都是一个问题 → 一张表。
desc: backend / subagent / 上下文手段 / 栈配置的选型表
---

## 一、选 backend

先回答三个问题：**文件在哪个范围可见？活多久？要执行命令吗？**

| 需求 | 选 |
| - | - |
| 单次会话的临时工作区 | `StateBackend`（默认） |
| agent 要操作我的真实项目目录 | `FilesystemBackend(root_dir="/abs/path")` |
| 需要跑 shell / 装依赖 / 跑测试 | 沙箱 backend |
| 开发机上快速验证执行能力 | `LocalShellBackend`（**无隔离**） |
| 跨会话的记忆与技能库 | `StoreBackend` + namespace |
| 易失工作区 + 持久记忆区并存 | `CompositeBackend` |
| 对象存储 / 内部文件服务 | 自定义 backend（实现协议） |
| 需要比 glob 更复杂的校验 | backend policy hooks |

!!! warning "三条硬约束"
    - `FilesystemBackend` 的 `root_dir` **必须是绝对路径**
    - 权限规则**不适用于** sandbox backend
    - `/**` 这种宽泛规则与 `default` 同时存在时，Composite 路由会失败

## 二、选 subagent 类型

| 场景 | 选 |
| - | - |
| 子任务完全自包含、只需带回结论 | 同步 subagent，`mode: "isolated"` |
| 子任务需要"接着刚才的上下文" | 同步 subagent，`mode: "fork"` |
| 子任务本身就是一张既有的 LangGraph 图 | `CompiledSubAgent` |
| 要遍历 80 个文件 / 批量处理 N 个单元 | dynamic subagent（`task()` + 解释器） |
| 需要多视角、对抗验证、逐轮淘汰 | dynamic subagent |
| 子任务要跑十几分钟，或需要中途操纵/取消 | async subagent |
| 只是想让模型自己记账 | `TodoListMiddleware`（不是 subagent） |

!!! tip "一个快速判据"
    **子任务产生的中间噪音 ÷ 它的结论，比值高才值得委派。**
    20 次搜索 → 1 页结论：值得。1 次查询 → 1 条结果：不值得。

### isolated vs fork

| | isolated | fork |
| - | - | - |
| 子 agent 看到什么 | 只有被派发的任务 | 父级完整对话 + 系统提示 |
| system_prompt | 必须自己写 | 通常省略（仅写附加说明） |
| token 成本 | 低 | 高（背着父级上下文起跑） |
| 适合 | 独立调研、批量处理 | 审查刚才的产出、接着进度干活 |

## 三、选上下文手段

遇到"上下文不够用"，按这个顺序考虑：

<div class="flow col">
  <div class="node hi"><span class="k">① 能不能不产生？</span><span class="v">把重活外包给 subagent（隔离）</span></div>
  <div class="node"><span class="k">② 能不能搬出去？</span><span class="v">offloading（&gt; 20,000 token 自动）</span></div>
  <div class="node"><span class="k">③ 能不能不常驻？</span><span class="v">改成 skill（按需加载）而非 memory</span></div>
  <div class="node"><span class="k">④ 能不能压小？</span><span class="v">summarization（85% 自动）；或按需 compact</span></div>
  <div class="node dim"><span class="k">⑤ 能不能不重复算？</span><span class="v">prompt caching（Anthropic / Bedrock 自动）</span></div>
</div>

| 症状 | 手段 |
| - | - |
| 单个工具结果太大 | offloading（自动） |
| 对话太长 | summarization（自动）或 `compact_conversation` |
| 主窗口被调研过程塞满 | subagent 隔离 |
| 固定指令太多、每轮都在付钱 | 改成 skill |
| 每轮都重算同样的前缀 | prompt caching |
| 外部知识需要按需取 | 检索工具（agentic RAG） |

## 四、选 RAG 架构

| 情况 | 架构 |
| - | - |
| 知识库明确、问题域窄、要低延迟 | **2-Step**（检索总在生成前） |
| 多个知识源、问题类型多变 | **Agentic**（每个源一个工具） |
| 答案质量要求高、可接受额外调用 | **Hybrid**（加校验） |
| 已经有现成知识库 | **不要重建**，接成工具或先查后喂 |

!!! key "Agentic RAG 不需要"启用""
    把一个检索函数当普通工具传给 `tools=`，agent 就自然获得了 agentic RAG 行为。

## 五、选管控手段

| 风险 | 手段 |
| - | - |
| 破坏性操作（删/发/花钱） | `interrupt_on` 严格配置 |
| 敏感路径（.env、credentials） | `permissions` deny + 首匹配 |
| 瞬时网络错误 | `ModelRetryMiddleware` / `ToolRetryMiddleware` |
| 工具返回坏结果、模型可自纠 | `ToolErrorMiddleware` |
| 供应商整体故障 | `ModelFallbackMiddleware` |
| 失控循环烧钱 | `ModelCallLimitMiddleware` / `ToolCallLimitMiddleware` |
| 产出质量不达标 | `RubricMiddleware` |
| 记忆写入需要把关 | 只读 memory + `interrupt_on` |

## 六、选栈配置方式

| 想做的调整 | 放哪里 |
| - | - |
| 与模型无关的全局调整 | `create_deep_agent` 调用处 |
| 取决于所选模型的调整 | harness profile |
| 只影响模型构造（temperature 等） | provider profile |
| 隐藏某个内建工具 | `excluded_tools`（不能用 `excluded_middleware`） |
| 去掉委派能力 | `GeneralPurposeSubagentProfile(enabled=False)` + 不传同步 subagents |
| 覆盖某个默认 middleware 行为 | 传一个 `.name` 相同的实例 |
| 加自己的横切逻辑 | `middleware=`（落在 Patch 之后） |

## 七、选前端投影

| 要展示 | 用什么 |
| - | - |
| 协调者的思路与最终答案 | `stream.messages` |
| 每个工作者的进度与内容 | `stream.subagents` + selector hooks |
| 任务进度条 | `stream.values.todos` |
| 工具调用（读文件、搜索） | 工具调用状态 → 卡片 |
| 待人工批准 | 中断事件 |
| 沙箱里的文件与改动 | 控制平面 API + diff |

!!! tip "共同点"
    **七个里没有一个需要解析自然语言。** 全部是结构化状态或工具事件。

## 八、选错误处理策略

| 错误类型 | 谁来修 | 手段 |
| - | - | - |
| 瞬时（网络、限流） | 系统 | 重试 + 指数退避 |
| 模型可恢复（工具失败、解析错） | 模型 | 转成错误 `ToolMessage` |
| 用户可修复（信息缺失） | 人 | `interrupt()` |
| 供应商故障 | 系统 | 降级到备用模型 |
| 调用过多 | 系统 | 调用限额 |
| **意外错误** | **开发者** | **让它冒泡，不要吞** |

## 九、任务 → 架构三步

面对任何一个新任务，回答三个问题就得到骨架：

<div class="flow col">
  <div class="node"><span class="k">① 要读外部世界吗？</span><span class="v">→ 工具（搜索 / DB / API / MCP）</span></div>
  <div class="node"><span class="k">② 要动手执行吗？</span><span class="v">→ 沙箱（跑代码）或解释器（纯编排）</span></div>
  <div class="node"><span class="k">③ 要领域知识吗？</span><span class="v">→ 文件 + skills（按需）或 memory（常驻）</span></div>
</div>

再加两个收尾问题：

- **长跑吗？** → checkpointer、异步 subagent、TTL 策略
- **有风险动作吗？** → `interrupt_on`、`permissions`、调用限额
