---
num: 7
slug: backend-family
title: 六个内建 Backend 的取舍
module: W2
tier: A
minutes: 14
desc: 作用域、持久性、可执行性 —— 三个维度决定你该选谁
lede: 选 backend 时真正要回答的只有三个问题：文件在哪个范围可见？活多久？能不能执行命令？把这三个维度想清楚，六个选项会各自归位。
source: https://docs.langchain.com/oss/python/deepagents/backends
source_title: Backends（官方）
---

## 三个维度

<div class="flow">
  <div class="node"><span class="k">作用域</span><span class="v">thread / assistant / user / 全局</span></div>
  <div class="arrow">×</div>
  <div class="node"><span class="k">持久性</span><span class="v">随会话消失 / 跨会话保留</span></div>
  <div class="arrow">×</div>
  <div class="node"><span class="k">可执行性</span><span class="v">只能读写 / 还能跑命令</span></div>
</div>

## 六个选项对照

| Backend | 存在哪 | 作用域 | 跨 thread | `execute` |
| - | - | - | - | - |
| `StateBackend` | 图状态 | thread | ❌ | ❌ |
| `FilesystemBackend` | 本机磁盘 | 你给的 `root_dir` | ✅（就是个真实目录） | ❌ |
| `LocalShellBackend` | 本机磁盘 | 你给的 `root_dir` | ✅ | ✅ |
| `StoreBackend` | LangGraph store | 由 `namespace` 决定 | ✅ | ❌ |
| `ContextHubBackend` | LangSmith Hub 仓库 | 仓库 | ✅ | ❌ |
| `CompositeBackend` | 按路径路由 | 每个路由各自决定 | 视路由 | ❌ |
| Sandbox | 隔离环境 | thread / assistant | 视配置 | ✅ |

## StateBackend：默认的那个

```python
agent = create_deep_agent(model="openai:gpt-5.5")
# 等价于
agent = create_deep_agent(model="openai:gpt-5.5", backend=StateBackend())
```

适合：**单次会话里的临时工作区**。agent 写草稿、记笔记、暂存搜索结果的天然场所。
不适合：任何需要跨会话保留的东西。

## FilesystemBackend：把 agent 接到你的真实目录

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=FilesystemBackend(root_dir="/Users/nh/Desktop/"),
)
```

!!! trap "两个必踩的坑"
    1. **`root_dir` 必须是绝对路径**，相对路径不行。
    2. **它意味着 agent 能改你的真实文件。** 官方建议：
       通常应该用 `CompositeBackend` 把"agent 内部数据"（offload 的工具结果、对话历史）
       与"你的项目文件"**分开**。否则 agent 的临时垃圾会直接落进你的工作目录。

## LocalShellBackend：加上执行能力

```python
agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=LocalShellBackend(root_dir=".", env={"PATH": "/usr/bin:/bin"}),
)
```

多了一个 `execute` 工具，**并且没有隔离**。官方措辞很直白：
"No isolation—use only in controlled development environments."

## StoreBackend：跨会话的家

```python
from deepagents.backends import StoreBackend

agent = create_deep_agent(model="openai:gpt-5.5", backend=StoreBackend())
```

它建在 LangGraph store 上，**跨 thread 持久化**。官方把它定位为
"存长期记忆或跨多次执行的指令"的地方。

真正有意思的是 **namespace 决定"谁和谁共享"**：

```python
# 每个用户独立一份（用户级隔离）
namespace=lambda rt: (rt.server_info.user.identity,)

# 同一个 assistant 的所有用户共享一份（agent 级身份）
namespace=lambda rt: (rt.server_info.assistant_id,)

# 单个会话内（thread 级）
namespace=lambda rt: (rt.server_info.thread_id,)
```

!!! key "这是一个非常干净的抽象"
    **"记忆的作用域"这个产品问题，被翻译成了"namespace 元组里放什么"。**
    - 放 `user_id` → 每个用户有自己的偏好
    - 放 `assistant_id` → agent 有自己的人格，所有用户共享
    - 放 `thread_id` → 退化成短期记忆

    没换类，没换 API，只换了一个 lambda。第 14 课会在这个抽象上展开。

## CompositeBackend：按路径路由

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

backend = CompositeBackend(
    default=StateBackend(),                 # 默认落在这里（临时工作区）
    routes={
        "/memories/": StoreBackend(namespace=lambda rt: ("my-agent",)),
        "/skills/":   StoreBackend(namespace=lambda rt: ("my-agent",)),
    },
)
```

读法是：**路径前缀就是路由规则。**

<div class="flow">
  <div class="node dim"><span class="k">/workspace/draft.md</span><span class="v">→ 落到 default</span></div>
  <div class="arrow">·</div>
  <div class="node hi"><span class="k">/memories/AGENTS.md</span><span class="v">→ 路由到 StoreBackend</span></div>
  <div class="arrow">·</div>
  <div class="node hi"><span class="k">/skills/x/SKILL.md</span><span class="v">→ 路由到 StoreBackend</span></div>
</div>

这基本上就是生产环境的默认形态：**易失的工作区 + 持久的记忆区**。

!!! warning "Composite 不是简单的"哪个前缀长用哪个""
    当 `/**` 这类宽泛规则与 `default` 同时存在时，路由会失败（抛 `NotImplementedError`）。
    官方给的可行形态是：用一个更具体的 deny 规则配合明确的路径模式。
    细节见 [Permissions · Composite backends](https://docs.langchain.com/oss/python/deepagents/permissions#composite-backends)。

## 自定义 backend

当一个都不合适时，实现 backend 协议就行。官方列出的可定制点：

- **实现协议**——自定义存储（对象存储、数据库、内部文件服务）
- **Policy hooks**——比声明式权限更复杂的校验逻辑

```python
# 迁移提示：backend 工厂（factory）已废弃
# Before（deprecated）
backend=lambda rt: StateBackend(rt)
# After
backend=StateBackend()
```

!!! note "0.7 的破坏性变更"
    早期版本里 backend 是一个接收 runtime 的**工厂函数**；
    现在直接传**实例**，需要 runtime 的地方（比如 StoreBackend 的 namespace）用 lambda 表达。
    读旧代码时看到 `backend=lambda rt: ...`，要意识到它来自旧版本。

```quiz
Q: 你希望"同一份 AGENTS.md 对所有使用该 agent 的用户生效"，namespace 应该放什么？
- 每个请求的 thread_id
- 当前用户的 user identity
* 当前 assistant 的 assistant_id
- 一个固定的字符串常量 + thread_id
E: agent 级记忆（agent 有自己的身份、跨所有用户累积）对应 namespace=(assistant_id,)。用户级隔离才用 user identity。

Q: 关于 FilesystemBackend，官方给出的两个注意点是什么？
- 只能读不能写，且必须配合沙箱
- root_dir 可以是相对路径，且自动隔离
* root_dir 必须是绝对路径，且建议用 Composite 分离内部数据与项目文件
- 它不支持 glob 与 grep，只支持读写
E: 官方明确说 root_dir 必须是绝对路径，并建议通常用 CompositeBackend 把 offload 的工具结果、对话历史等内部数据与项目文件分开存放。

Q: 哪个 backend 组合既能跑 shell 又有隔离边界？
- StateBackend 加 permissions
- FilesystemBackend 加 root_dir 限制
* Sandbox 类 backend
- StoreBackend 加 namespace 隔离
E: 隔离与执行同时成立只有沙箱这一条路。LocalShellBackend 有 execute 但没有隔离，官方限定它只能在受控开发环境使用。
```

## 下一课

虚拟文件系统可以路由到任何地方——那么**谁能读、谁能写**由谁决定？
下一课：声明式权限。它比你想的更像网络防火墙的规则表。
