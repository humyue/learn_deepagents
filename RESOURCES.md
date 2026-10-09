# RESOURCES

高质量、高信任度的知识来源。所有课程的断言都应能追溯到这里的某一项。

## 一手来源（Primary — 官方）

### Deep Agents 本体

| 资源 | 链接 | 用途 | 信任度 |
| - | - | - | - |
| Deep Agents Overview | <https://docs.langchain.com/oss/python/deepagents/overview> | harness 能力全景、四层执行环境、四层上下文 | 最高（官方） |
| Deep Agents 全部章节 | <https://docs.langchain.com/oss/python/deepagents/quickstart> … | 课程事实来源；本地快照见 `raw/*.md` | 最高 |
| `deepagents` PyPI | <https://pypi.org/project/deepagents/> | 版本号、依赖、变更 | 最高 |
| Deep Agents 源码 | <https://github.com/langchain-ai/deepagents> | 中间件实现、prompt 原文、栈顺序的第一手证据 | 最高 |
| Deep Agents 示例集 | <https://github.com/langchain-ai/deepagents/tree/main/examples> | 应用级模式（research / data analysis / content） | 高 |
| API Reference（deepagents） | <https://reference.langchain.com/python/deepagents/> | 精确类名、函数签名、字段类型 | 最高 |

### 底层平台（理解 harness 必需）

| 资源 | 链接 | 用途 |
| - | - | - |
| LangChain Middleware 总览 | <https://docs.langchain.com/oss/python/langchain/middleware/overview> | middleware 钩子模型（`before_model` / `wrap_tool_call` …） |
| LangChain Middleware 内置清单 | <https://docs.langchain.com/oss/python/langchain/middleware/built-in> | Summarization / HITL / TodoList / Retry 等语义 |
| LangChain `create_agent` | <https://docs.langchain.com/oss/python/langchain/agents> | Deep Agents 之下的那一层"普通 agent" |
| LangGraph 运行时 | <https://docs.langchain.com/oss/python/langgraph/overview> | durable execution、checkpointer、interrupt |
| LangGraph Checkpointers | <https://docs.langchain.com/oss/python/langgraph/checkpointers> | thread 状态持久化 = 短期记忆的底座 |
| LangGraph Store | <https://docs.langchain.com/oss/python/langgraph/stores> | 跨 thread 长期存储 = 长期记忆的底座 |
| LangChain Event Streaming | <https://docs.langchain.com/oss/python/langchain/event-streaming> | 流式投影（messages / tool_calls / values） |
| LangChain MCP | <https://docs.langchain.com/oss/python/langchain/mcp> | MCP 接入细节 |
| Concepts: Frameworks, runtimes, harnesses | <https://docs.langchain.com/oss/python/concepts/products> | 三层概念的正本清源 |

### 协议与标准

| 资源 | 链接 | 用途 |
| - | - | - |
| MCP 规范 | <https://modelcontextprotocol.io/> | 工具接入的开放标准 |
| Agent Skills 标准 | <https://agentskills.io/> | `SKILL.md` 的结构与语义 |
| AGENTS.md | <https://agents.md/> | memory 文件约定 |
| Agent Client Protocol | <https://agentclientprotocol.com/> | 编辑器（Zed 等）接 agent 的协议 |
| AG-UI | <https://docs.ag-ui.com/> | agent ↔ 前端 UI 的事件协议 |

## 二手来源（Secondary — 评论、对比、工程博客）

| 资源 | 链接 | 用途 | 注意 |
| - | - | - | - |
| "How to fix your context"（Drew Breunig） | <https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html> | context quarantine / offloading 的问题定义 | 官方文档亲自引用，可信 |
| Deep Agents vs Claude Agent SDK | <https://docs.langchain.com/oss/python/deepagents/comparison> | 与 Anthropic harness 的取舍对比 | 官方立场，需交叉验证 |
| Anthropic: Building effective agents | <https://www.anthropic.com/engineering/building-effective-agents> | harness 设计的业界共识 | 高 |

## 社区（Wisdom — 拿技能去真实世界检验）

| 社区 | 链接 | 适合问什么 |
| - | - | - |
| LangChain Forum | <https://forum.langchain.com/> | 官方维护，harness 行为/版本问题 |
| r/LangChain | <https://www.reddit.com/r/LangChain/> | 踩坑经验、生产实践 |
| LangChain GitHub Issues | <https://github.com/langchain-ai/deepagents/issues> | 疑似 bug、源码级追问 |
| MCP Discord | <https://modelcontextprotocol.io/community> | 工具接入协议问题 |

## 快照说明

`raw/*.md` 为 2026-10-08 通过文档站 `.md` 端点抓取的官方页面原文快照。
若与线上冲突，**以线上为准**，并更新快照。
