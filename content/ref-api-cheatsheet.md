---
kind: reference
sort: 3
slug: api-cheatsheet
title: API 速查
lede: 关键签名、参数归类、内建工具清单。不需要背，写代码时对照用。
desc: create_deep_agent 签名与各层关键 API
---

## create_deep_agent

```python
create_deep_agent(
    model,                       # str "provider:model" 或 BaseChatModel 实例
    tools,                       # Sequence[BaseTool | Callable | dict]
    *,
    system_prompt,               # 静态；永远拼在最前面
    middleware,                  # 同名替换，其余插在 Patch 之后
    subagents,                   # Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent]
    skills,                      # list[str]，虚拟文件系统里的技能目录
    memory,                      # list[str]，AGENTS.md 路径，总是加载
    permissions,                 # list[FilesystemPermission]
    backend,                     # BackendProtocol 实例（不是工厂函数）
    interrupt_on,                # dict[str, bool | InterruptOnConfig]
    response_format,             # Pydantic / ToolStrategy / ProviderStrategy / 裸 schema
    state_schema,                # 必须继承 DeepAgentState
    context_schema,              # dataclass 或 TypedDict；会传播到 subagent
    checkpointer,                # 中断与 thread 状态的硬依赖
    store,                       # 跨 thread 存储
    debug, name, cache,
)
# 返回 CompiledStateGraph（已编译，可直接 invoke / stream）
```

**参数归类**：执行环境 = `tools` / `backend` / `permissions`；
上下文 = `system_prompt` / `memory` / `skills`；
委派 = `subagents`；管控 = `interrupt_on` / `middleware`。

## 内建工具

| 工具 | 依赖 |
| - | - |
| `ls` `read_file` `write_file` `edit_file` `glob` `grep` | 任意 backend |
| `delete` | backend 支持才行 |
| `execute` | **仅** sandbox 类 backend |
| `task` | 存在至少一个同步 subagent |
| `write_todos` | 传了 `TodoListMiddleware` |
| `compact_conversation` | 传了 `create_summarization_tool_middleware` |
| `eval` | 传了 `CodeInterpreterMiddleware` |

`read_file` 支持多模态：图片 `.png .jpg .jpeg .gif .webp .heic .heif`；
视频 `.mp4 .mpeg .mov .avi .flv .mpg .webm .wmv .3gpp`；
音频 `.wav .mp3 .aiff .aac .ogg .flac`；文件 `.pdf .ppt .pptx`。

## Backends

```python
from deepagents.backends import (
    StateBackend,          # 默认；图状态；thread 作用域；无 execute
    FilesystemBackend,     # 本地磁盘；root_dir 必须绝对路径
    LocalShellBackend,     # 本地磁盘 + execute；无隔离
    StoreBackend,          # 跨 thread；namespace 决定作用域
    ContextHubBackend,     # LangSmith Hub 仓库
    CompositeBackend,      # 按路径前缀路由
)
```

```python
# namespace 决定"谁和谁共享"
StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))     # 用户级
StoreBackend(namespace=lambda rt: (rt.server_info.assistant_id,))      # agent 级
StoreBackend(namespace=lambda rt: (rt.server_info.thread_id,))         # thread 级
```

```python
# 组合：易失工作区 + 持久记忆区
CompositeBackend(
    default=StateBackend(),
    routes={
        "/memories/": StoreBackend(namespace=lambda rt: ("my-agent",)),
        "/skills/":   StoreBackend(namespace=lambda rt: ("my-agent",)),
    },
)
```

!!! warning "0.7 变更"
    `backend=lambda rt: StateBackend(rt)`（工厂函数）已废弃，改为直接传实例。

## 权限

```python
permissions=[
    {"operations": ["read", "write"], "paths": ["/workspace/.env"], "mode": "deny"},
    {"operations": ["read", "write"], "paths": ["/workspace/**"],   "mode": "allow"},
    {"operations": ["read", "write"], "paths": ["/**"],             "mode": "deny"},
]
```

**首匹配胜出；无匹配则允许。** 精确规则在前，宽泛规则在后。
不适用于 sandbox backend。

## Subagent 字段

```python
{
    "name":            str,                      # 必填；也是流式路由键
    "description":     str,                      # 必填；决定何时委派
    "system_prompt":   str,                      # isolated 模式必填；不继承
    "mode":            "isolated" | "fork",      # 默认 isolated
    "tools":           list,                     # 默认继承；指定即整体覆盖
    "model":           str | BaseChatModel,      # 默认继承
    "middleware":      list,                     # 不继承
    "interrupt_on":    dict,                     # 默认继承
    "skills":          list[str],                # 不继承（仅 general-purpose 继承）
    "response_format": ResponseFormat,           # 结构化输出
    "permissions":     list[FilesystemPermission],  # 默认继承；指定即整体替换
}
```

```python
CompiledSubAgent(name=..., description=..., runnable=compiled_graph, mode=...)
# 自定义 LangGraph 图的 state 必须有 "messages" 键
```

## Human-in-the-loop

```python
interrupt_on={
    "edit_file":  True,                                  # 四种决策全开
    "write_file": False,                                 # 关闭
    "execute":    {"allowed_decisions": ["approve", "reject"]},
}
```

四种决策：`approve` / `edit` / `reject` / `respond`。
**必须有 checkpointer；恢复时 thread_id 必须一致。**

## 上下文工程

```python
from deepagents.middleware.summarization import create_summarization_tool_middleware
middleware=[create_summarization_tool_middleware(model, backend)]   # 按需压缩
```

| 阈值 | 值 |
| - | - |
| offloading 触发 | 20,000 token（工具输入与结果各自） |
| summarization 触发 | 模型 `max_input_tokens` 的 85% |
| summarization 保留 | 10% token 作为最近上下文 |
| 兜底 | 170,000 token 触发 / 保留 6 条消息 |
| 输入截断触发 | 上下文越过 85% 时截断较早的 tool call |

## 自定义 state / context

```python
from deepagents import DeepAgentState

class MyState(DeepAgentState):     # 必须继承
    counter: int
    urls: list[str]

@tool
def read_it(runtime: ToolRuntime) -> str:
    """..."""
    return runtime.state["counter"]        # state：可变、被 checkpoint

@tool
def use_ctx(q: str, runtime: ToolRuntime[Context]) -> str:
    """..."""
    return call(runtime.context.user_id)   # context：不可变、传播到 subagent
```

## Profiles

```python
from deepagents import HarnessProfile, GeneralPurposeSubagentProfile, register_harness_profile

register_harness_profile("openai:gpt-6-astra", HarnessProfile(
    base_system_prompt=...,
    system_prompt_suffix=...,
    tool_description_overrides={...},
    excluded_tools=frozenset({"execute"}),
    excluded_middleware=frozenset({"SummarizationMiddleware"}),
    extra_middleware=[...],
    general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
))
```

**键**：`"openai"`（provider 级）或 `"openai:gpt-6-astra"`（model 级，只有第一个冒号是分隔符）。
**无通配键。** 重复注册是**合并**（`excluded_*` 取并集）。

## 其他中间件

```python
from langchain.agents.middleware import (
    TodoListMiddleware,          # write_todos（v0.7 起 opt-in）
    ModelRetryMiddleware,        # 模型调用重试（指数退避）
    ToolRetryMiddleware,         # 工具重试（可按工具名与异常类型限定）
    ToolErrorMiddleware,         # 把异常转成错误 ToolMessage 交给模型
    ModelFallbackMiddleware,     # 供应商故障时降级
    ModelCallLimitMiddleware,    # 模型调用次数上限
    ToolCallLimitMiddleware,     # 工具调用次数上限
)
from deepagents import RubricMiddleware    # 评分量表迭代
from langchain_quickjs import CodeInterpreterMiddleware   # 解释器 / 动态 subagent
```

## 流式

```python
# 通用流式（看 namespace 用 subgraphs=True）
for chunk in agent.stream(input, stream_mode="updates", subgraphs=True):
    namespace, update = chunk

# 子代理投影（注意版参数）
stream = agent.stream_events(input, version="v3")
for sub in stream.subagents:
    print(sub.name, sub.path, sub.status)
    for m in sub.messages: ...
```

句柄字段：`name` `messages` `subagents` `output` `path` `status` `tool_calls`。
状态：`started` / `completed` / `failed` / `interrupted`。
**惰性打开**：只读 `status` 不会打开消息流。

## 解释器与动态 subagent

```python
agent = create_deep_agent(
    model=...,
    subagents=[{"name": "reviewer", "description": ..., "system_prompt": ...}],
    middleware=[CodeInterpreterMiddleware()],       # subagents=False 可关闭代码派发
)
```

```javascript
const r = await task({
  description: "...",
  subagentType: "reviewer",
  responseSchema: { type: "object", properties: { ... } },
});
// 有 responseSchema 时结果已是定型对象，无需 JSON.parse
```

关掉：`CodeInterpreterMiddleware(subagents=False)`。
装依赖：`pip install -U "deepagents[quickjs]"`（需 Python 3.11+，`langchain-quickjs>=0.2.0`）。

## MCP

```python
from langchain.mcp import MCPAdapter

async with MCPAdapter({"mcpServers": {"my_server": {"url": "http://localhost:8000/mcp"}}}) as adapter:
    tools = await adapter.list_tools()
    agent = create_deep_agent(model=..., tools=tools)
```

装依赖：`pip install "langchain[mcp]"`。
