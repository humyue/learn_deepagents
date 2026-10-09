---
num: 5
slug: tools-and-mcp
title: 工具与 MCP：agent 的手
module: W2
tier: B
minutes: 10
desc: 三种工具来源、schema 推导、以及 MCP 到底省掉了什么
lede: 工具是 agent 唯一能改变世界的方式。这一课讲清工具从哪里来、schema 怎么生成、以及 MCP 真正解决的问题是什么。
source: https://docs.langchain.com/oss/python/deepagents/tools
source_title: Tools（官方）
---

## 工具的三种来源

`tools=` 参数接受任何可调用对象，混着传也行：

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="openai:gpt-5.5",
    tools=[search, fetch_url, run_query],   # 1. 普通函数
)
```

| 来源 | 形态 | 什么时候用 |
| - | - | - |
| **普通 callable** | 任何 Python 函数 | 快速原型；函数签名清晰时 |
| **LangChain `@tool`** | 装饰过的函数 | 需要自定义 schema、错误处理、或 `ToolRuntime` 时 |
| **工具 dict** | `{"name":..., "description":..., "parameters":...}` | 动态生成工具、从外部配置反序列化 |
| **MCP server** | 通过 `MCPAdapter` 列出 | 对接已有生态（数据库、API、浏览器…） |

官方强调：**不需要手写 schema**。Deep Agents 会从函数签名与 docstring 推导。

!!! tip "docstring 是你的工具描述"
    模型选择工具时，唯一依据是**工具名 + 描述 + 参数 schema**。
    所以 docstring 不是给人看的注释，它是 prompt 的一部分。
    写得含糊（"Do the thing"）等于没给模型信息。

## 工具能看到运行时

工具不需要 middleware 就能拿到运行时信息——它直接接收 `ToolRuntime`：

```python
from langchain.tools import tool, ToolRuntime

@tool
def who_am_i(runtime: ToolRuntime) -> str:
    """Return the current user ID."""
    return runtime.server_info.user.identity
```

`runtime.context` 和 `runtime.store` 都可以在这里读到。
**只有当"工具要连带改写系统提示"时，才需要 middleware。**
这是一个常见的过度设计：为了给工具传上下文而写一堆 middleware，其实完全不需要。

## MCP：省掉的到底是什么

Model Context Protocol 是一个开放标准。用 `MCPAdapter` 接一个 server：

```python
import asyncio
from deepagents import create_deep_agent
from langchain.mcp import MCPAdapter

async def main():
    config = {"mcpServers": {"my_server": {"url": "http://localhost:8000/mcp"}}}
    async with MCPAdapter(config) as adapter:
        tools = await adapter.list_tools()
        agent = create_deep_agent(model="openai:gpt-5.5", tools=tools)
        await agent.ainvoke(
            {"messages": [{"role": "user", "content": "Use the MCP server to help me."}]},
            config={"configurable": {"thread_id": "1"}},
        )

asyncio.run(main())
```

安装依赖：

```bash
pip install "langchain[mcp]"
```

!!! key "MCP 真正解决的是 N×M 问题"
    没有 MCP：M 个 agent 框架 × N 个服务 = M×N 份集成代码。
    有 MCP：M + N 份（每个框架一个 client，每个服务一个 server）。

    它**不**解决：工具描述质量、权限、上下文成本。
    一个 MCP server 暴露 40 个工具，你接上之后，这 40 个工具的 schema
    每次调用都会进入你的 prompt。这时候该做的是**工具过滤**，
    而不是全量接入。MCP 详情见 [LangChain MCP 指南](https://docs.langchain.com/oss/python/langchain/mcp)。

## 内建工具 vs 你的工具

两者在 `tools=` 里合并，然后一起进模型：

<div class="flow">
  <div class="node dim"><span class="k">harness 内建</span><span class="v">ls · read_file · write_file · edit_file · glob · grep（+ delete · execute）</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">你的 tools=</span><span class="v">internet_search · fetch_url · …</span></div>
  <div class="arrow">＋</div>
  <div class="node"><span class="k">MCP 工具</span><span class="v">adapter.list_tools()</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">模型可见的工具集合</span><span class="v">再经 excluded_tools 过滤</span></div>
</div>

!!! warning "工具太多会让模型变笨"
    官方在 subagent 最佳实践里明确写了 "Minimize tool sets"：
    给一个代码审查 subagent 挂 30 个工具，它选择正确工具的概率会显著下降。
    这不是模型能力问题，是**候选集规模**问题。

```quiz
Q: 什么时候才真正需要写 middleware 来给工具传上下文？
- 只要工具需要读取用户身份就必须写
- 工具需要访问 store 时就必须写
* 只有当工具需要连带修改系统提示时
- 工具需要返回多模态内容时必须写
E: 官方明确说：工具本身就能收到 ToolRuntime（含 context 与 store），不需要 middleware。只有"把工具与一次系统提示更新打包在一起"时才需要 middleware。

Q: MCP 最主要解决的是哪一类问题？
- 让模型的工具调用更准确
- 让工具调用的 token 开销更低
* 把 M 个框架与 N 个服务的集成从 M×N 降到 M+N
- 为工具调用提供人类审批能力
E: MCP 是接口标准化，减少集成组合数。它不改善工具描述质量，不降低 token 成本，也不提供审批——那分别是 prompt 工程、excluded_tools、interrupt_on 的职责。

Q: 模型决定调用哪个工具时，唯一依据是什么？
- 工具的 Python 类型注解与返回值
- 工具在 tools 列表里的先后顺序
* 工具名、描述文本与参数 schema
- 工具的导入路径与所属模块
E: 模型看不到实现，只能看到名字、描述和参数 schema。因此 docstring 是 prompt 的一部分，而不是普通注释。
```

## 下一课

工具让 agent 能"动手"，但真正让 harness 成立的是另一件东西：
**一个虚拟文件系统。** 下一课解释为什么它是整个架构的地基。
