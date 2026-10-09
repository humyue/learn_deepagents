---
num: 8
slug: filesystem-permissions
title: 声明式权限：像防火墙一样配文件访问
module: W2
tier: B
minutes: 9
desc: 规则表、首匹配胜出、以及它为什么管不住沙箱
lede: 权限不是"给 agent 一个提示让它别乱写"，而是一张<b>声明式规则表</b>，在工具执行前强制生效。这一课讲清规则结构与它管不到的地方。
source: https://docs.langchain.com/oss/python/deepagents/permissions
source_title: Permissions（官方）
---

## 基本形态

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    permissions=[
        {"operations": ["write"], "paths": ["/**"], "mode": "deny"},   # 只读 agent
    ],
)
```

每条规则三个字段：

| 字段 | 取值 | 含义 |
| - | - | - |
| `operations` | `"read"` / `"write"`（可同时给） | 管哪类操作 |
| `paths` | glob 模式 | 管哪些路径 |
| `mode` | `"allow"` / `"deny"` | 允许还是拒绝 |

## 两条必须记住的求值规则

!!! key "第一匹配胜出 + 无匹配则允许"
    规则**从上往下**求值，**第一条匹配的规则决定结果**（first-match-wins）。
    如果**没有任何规则匹配**，操作**被允许**。

    第二点是安全上最容易被忽略的：**权限系统默认是开放式的**。
    想做到"除了 X 都能用"，你必须在最后补一条兜底的 deny。

<div class="flow">
  <div class="node"><span class="k">工具请求</span><span class="v">write /workspace/a.md</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">逐条匹配</span><span class="v">从上往下，第一条命中即判定</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">结果</span><span class="v">allow / deny</span></div>
  <div class="arrow">→</div>
  <div class="node dim"><span class="k">未命中任何规则</span><span class="v">默认 allow</span></div>
</div>

## 顺序错误的经典 bug

官方文档专门用了一组对比来强调这件事：

```python
# ✅ 正确顺序：先精确 deny，再放开目录，最后兜底 deny
permissions=[
    {"operations": ["read", "write"], "paths": ["/workspace/.env"], "mode": "deny"},
    {"operations": ["read", "write"], "paths": ["/workspace/**"],   "mode": "allow"},
    {"operations": ["read", "write"], "paths": ["/**"],             "mode": "deny"},
]

# ❌ 有 bug：/workspace/** 先命中了 .env，那条 deny 永远不会生效
permissions=[
    {"operations": ["read", "write"], "paths": ["/workspace/**"],   "mode": "allow"},
    {"operations": ["read", "write"], "paths": ["/workspace/.env"], "mode": "deny"},
    {"operations": ["read", "write"], "paths": ["/**"],             "mode": "deny"},
]
```

规律是：**精确的规则写前面，宽泛的规则写后面。**
这和 iptables、和 nginx location 是同一套心智模型。

## 常见配方

| 目标 | 做法 |
| - | - |
| 把 agent 圈在某个目录 | 允许 `/workspace/**`，其余 `/**` deny |
| 保护敏感文件 | 最前面加 `/workspace/.env`、`credentials` 的 deny |
| 记忆只读 | 允许读 `/memories/**`，禁止写 |
| 完全禁止访问 | 单条 `/**` deny |
| 暂停等待人工批准 | 见下面的 interrupt 用法 |

## 暂停而不是拒绝

权限的第三种结果是"停下来问人"——这时会触发 human-in-the-loop 中断，
批准后才继续。这条路径与 `interrupt_on` 是同一套机制的两端（第 25 课展开）。

## 它管不到的地方

!!! trap "权限不适用于 sandbox backend"
    官方明确写着：**Permissions do not apply to sandbox backends**，
    因为沙箱支持通过 `execute` 工具执行任意命令。

    推理一下就很清楚：一个能跑 `rm -rf /workspace` 的 shell，
    再严格的"路径级读写规则"都拦不住它——它绕过的是工具层，不是文件层。
    **沙箱的正确隔离手段是沙箱本身**（单独的环境、单独的文件系统、单独的网络策略）。

!!! warning "声明式不够用时用 policy hooks"
    需要比 glob 匹配更复杂的判断（比如按文件内容、按时间、按调用次数），
    就走 backend 的 policy hooks，把逻辑写进代码。

## 作用域

- **主 agent**：`permissions=` 直接配置。
- **声明式 subagent**：**不继承**父级权限。要让 subagent 更窄，
  必须在它自己的 `permissions` 字段里单独配。（注意：一旦设置就是**整体替换**，不是叠加。）
- **默认 subagent**：继承主 agent 的权限。

```quiz
Q: 权限规则中没有任何一条匹配时，默认结果是什么？
- 拒绝，并记录一次审计事件
- 拒绝，并中断等待人工批准
* 允许
- 取决于 backend 的实现
E: 官方规则是 first-match-wins，且没有规则匹配时操作被允许。这就是为什么"圈定目录"的配方必须补一条 /** deny 兜底。

Q: 为什么权限对 sandbox backend 不生效？
- 因为沙箱里的路径与主文件系统不同名
- 因为沙箱使用了独立的权限规则文件
* 因为沙箱能通过 execute 执行任意命令，绕过工具层
- 因为沙箱的 backend 协议不包含 permissions 字段
E: 沙箱提供 execute 工具，可以运行任意 shell 命令。路径级读写规则拦不住一个能直接操作文件系统的 shell，所以隔离必须由沙箱环境本身提供。

Q: 声明式 subagent 与父 agent 的权限关系是？
- 完全继承父级规则并做交集
- 完全继承父级规则并做并集
* 默认继承；一旦设置就是整体替换而非叠加
- 默认不继承，必须显式配置
E: 声明式 subagent 的 permissions 默认继承主 agent；一旦在 subagent 上设置，就整体替换父级的权限集合，而不是两者求交或求并。
```

## 下一课

权限在文件层加了边界。但如果 agent 要**真的跑代码**，文件层边界就不够了。
下一课：沙箱——把整个执行环境关起来。
