---
num: 9
slug: sandboxes
title: 沙箱：让 agent 跑代码而不伤到宿主机
module: W2
tier: B
minutes: 10
desc: 沙箱是一种 backend，加上 execute 与一个真实的隔离边界
lede: 权限能拦住文件操作，拦不住 <code>rm</code>。要让 agent 真的执行代码，你需要把整个环境关进一个盒子里——这就是沙箱。
source: https://docs.langchain.com/oss/python/deepagents/sandboxes
source_title: Sandboxes（官方）
---

## 沙箱首先是 backend

这是最容易读漏的一点：**在 Deep Agents 里，沙箱不是另一个概念，它就是一类 backend。**

| | 普通 backend | Sandbox backend |
| - | - | - |
| 文件系统工具 | ✅ 全部 | ✅ 全部 |
| `execute` 工具 | ❌ | ✅ |
| 隔离边界 | 无（只是存储） | 有（独立环境） |
| 权限规则 | 生效 | **不生效**（见第 08 课） |

官方对动机的表述很直接：

!!! note "官方原话"
    Agents generate code, interact with filesystems, and run shell commands.
    Because you can't predict what an agent might do, it's important that its
    environment is isolated so it can't access credentials, files, or the network.

    关键词是 **you can't predict**。沙箱不是为了防恶意，而是**为了防不可预测**。

## 接上沙箱

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    backend=sandbox,          # 由具体 provider 构造出来的沙箱对象
)
```

提供商（LangSmith、AgentCore、Daytona 等）见官方
[sandbox integrations](https://docs.langchain.com/oss/python/integrations/sandboxes)。
这里要理解的不是某一家的 API，而是**生命周期模型**。

## 生命周期：thread 级还是 assistant 级

这是选型时唯一真正要做的决定：

<div class="compare">
<div class="yes">
<h4>Thread-scoped（默认）</h4>
<ul>
<li>每个会话一个沙箱</li>
<li>首次运行创建，同一 thread 的后续 turn 复用</li>
<li>thread 结束或 TTL 到期后环境消失</li>
<li>适合：一次性任务、代码生成与验证</li>
</ul>
</div>
<div class="no">
<h4>Assistant-scoped</h4>
<ul>
<li>同一 assistant 的所有 thread 共用一个</li>
<li>环境里的状态跨会话保留</li>
<li>适合：需要长期驻留的工作区（比如一个持续维护的仓库）</li>
</ul>
</div>
</div>

!!! trap "沙箱一直开着是要花钱的"
    官方强调得很直白：沙箱在关闭之前持续消耗资源与成本。
    生产上必须配 TTL，让 provider 自动删除或归档空闲环境——
    尤其当用户可能长时间不回来时。

## 两个集成模式

### 模式一：Agent in sandbox

agent 本身跑在沙箱里，文件系统与执行环境都是沙箱的。
适合"agent 的主体工作就是操作这个环境"的场景。

### 模式二：Sandbox as tool

agent 跑在你的进程里，沙箱只是它调用的一个工具。
适合"agent 主体逻辑在你这边，只是偶尔需要跑一段不可信代码"的场景。

## 两个平面：文件访问为什么有两条路

沙箱的一个实现细节值得单独理解——**文件访问有两个平面**：

<div class="flow">
  <div class="node"><span class="k">模型平面</span><span class="v">ls / read_file / write_file → 走 backend 协议</span></div>
  <div class="arrow">＋</div>
  <div class="node hi"><span class="k">控制平面</span><span class="v">你的代码用 provider SDK 直接上传 / 下载文件</span></div>
</div>

区别在于**谁在操作**：agent 通过工具操作（模型平面），
你的宿主程序通过 SDK 操作（控制平面）。所以：

- **播种（seeding）**：任务开始前，你用控制平面把数据文件放进沙箱。
- **取回产物（retrieving artifacts）**：任务结束后，你用控制平面把生成的报告、图表取回来。

这解释了一个常见困惑：**"为什么 agent 说它写了文件，我的程序里读不到？"**
因为它写在沙箱里，你的程序在宿主机上——需要通过控制平面取回来。

## 安全清单

| 项 | 做法 |
| - | - |
| 密钥 | **不要把真实凭据注入沙箱。** 用临时短时凭据或代理 |
| 网络 | 按需限制；不需要网络的沙箱就断网 |
| 生命周期 | 配 TTL，任务结束主动关闭 |
| 数据 | 只播种任务必需的子集，不要整库上传 |
| 产物 | 明确取回路径，并校验内容 |

```quiz
Q: 在 Deep Agents 的架构里，沙箱的正确归类是什么？
- 一种独立于 backend 的执行中间件
- 一种把权限规则强化后的 backend
* 一种额外提供 execute 工具的 backend
- 一种把 agent 持久化的 checkpointer
E: 官方明确说 sandboxes are backends。它们与其他 backend 的差别是：文件操作之外还提供 execute 工具，并在宿主机之间建立隔离边界。

Q: 为什么权限规则在沙箱上不适用？
- 因为沙箱使用另一套 glob 语法
- 因为沙箱默认禁止所有写入
* 因为 execute 能跑任意命令，绕过路径级规则
- 因为沙箱的文件系统是只读挂载的
E: 沙箱提供任意 shell 执行，路径级的读写规则无法约束它。隔离必须由沙箱环境本身承担。

Q: "模型平面"和"控制平面"的文件访问区别在于？
- 一个加密一个不加密
- 一个同步一个异步
* 一个由 agent 通过工具操作，一个由宿主程序通过 SDK 操作
- 一个作用于沙箱内，一个作用于宿主机
E: 模型平面是 agent 通过 ls/read_file/write_file 走 backend 协议；控制平面是你的代码用 provider SDK 直接上传下载。播种与取回产物走控制平面。
```

## 下一课

沙箱是"针对环境"的代码执行。但如果 agent 只是需要**在循环里做点循环、分支、批处理**，
为这个开一个沙箱太重了。下一课：解释器与程序化工具调用。
