# Deep Agents 教学站

一门**中文课程**，用来拆开 [Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) 这个 **agent harness** 的内部构造。

不追求"跑通一个 demo"，追求回答这类问题：

- 一次 `create_deep_agent()` 调用到底装配了什么？
- 上下文窗口是怎么被管住的？为什么 offloading 和 summarization 要分两道防线？
- 委派为什么能省 token？`isolated` / `fork` / `dynamic` / `async` 四种 subagent 各自解决什么？
- 为什么 `MemoryMiddleware` 被刻意排在 prompt caching **之后**？

规模：**40 课 · 4 份速查手册 · 138 道检索题**，覆盖官方左侧导航全部 35 个页面。
纯静态 HTML，无构建依赖即可浏览，可离线、可打印。

---

## 这门课是什么 / 不是什么

| 是 | 不是 |
| - | - |
| 按 harness **依赖顺序**重排的课程（官方按功能页组织，适合查；教学要按依赖组织，适合懂） | 官方文档的翻译或镜像 |
| 一手来源驱动：每个论断都链到官方原文，`raw/` 存有快照供核对 | 靠记忆写成的二手总结 |
| 没有 API Key 也能学：练习形式是**读代码 + 推演机制 + 离线自测** | 一堆需要跑通才有意义的 demo |
| 刻意区分 Tier A（原理深挖）与 Tier B（集成速览） | 每章平均用力的平铺教程 |

---

## 快速开始

### 直接看（本地）

```bash
# 双击或浏览器打开仓库根的 index.html 即可
# 无需服务器、无需安装任何东西
```

```text
file:///home/huhu/llm_develop/deepagents_tutorials/index.html
```

### 重新构建（改完内容后）

```bash
source .venv/bin/activate
python build.py              # 输出到仓库根（本地浏览用）
python build.py --out docs   # 输出到 docs/（GitHub Pages 发布用）
```

首次搭建环境：

```bash
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install markdown pygments
```

---

## 课程地图

七个模块，每一模块回答一个层次的问题：

| 模块 | 课数 | 回答的问题 |
| - | - | - |
| **A · 心智模型** | 4 | 它到底是什么？站在哪一层？出厂装了什么？装配顺序为什么是这样？ |
| **B · 执行环境** | 6 | agent 的手长什么样：工具、虚拟文件系统、权限、沙箱、解释器 |
| **C · 上下文工程** | 8 | harness 存在的真正理由：四个上下文层如何分工 |
| **D · 委派** | 6 | 把大问题拆小：四种 subagent + 任务规划 |
| **E · 运行时管控** | 3 | 怎么让一个会自己动手的 agent 可被信任：中断、容错、profile |
| **F · 流式与前端** | 6 | 一棵树怎么变成几条流，以及三种前端模式 |
| **G · 应用与生产** | 7 | 四个成品模式 + 上线要补的课 |

**分层**：18 课 Tier A（原理深挖：动机 → 机制 → 代码 → 坑 → 自测）、22 课 Tier B（集成速览）。
**总时长**约 7 小时 31 分。

### 建议顺序

```text
第 01–04 课   地基。这四课决定你读后面每一节时，脑子里有没有"它插在哪儿"的地图
第 05–10 课   执行环境。重点不是 API 怎么写，而是为什么"虚拟文件系统"是地基
第 11–18 课   上下文工程。harness 存在的理由，值得反复读
第 19–24 课   委派。理解 context quarantine 与三种 subagent 的分工
第 25–27 课   管控
第 28–33 课   流式与前端
第 34–40 课   成品模式与生产。可以跳读，按需回看
```

> **第 04 课（middleware 装配顺序）建议读两遍。** 它是全课程的枢纽：
> 解释了为什么 `PatchToolCallsMiddleware` 必须很早、`MemoryMiddleware` 必须很晚。

### 速查手册

课程会被遗忘，手册不会。四份手册是把课程压缩到最小后的可检索形态：

| 手册 | 内容 |
| - | - |
| **术语表** | 全站统一术语，每条附出处 |
| **中间件栈速查** | 完整装配顺序 + 每一层的排序理由 + subagent 栈差异 |
| **API 速查** | `create_deep_agent` 签名、各层关键 API、内建工具清单 |
| **选型决策图** | backend / subagent / 上下文手段 / 栈配置的九张选型表 |

---

## 目录结构

```text
├── index.html              ← 课程地图（入口）
├── lessons/*.html          ← 40 课
├── reference/*.html        ← 4 份速查手册
├── assets/                 ← 共享组件
│   ├── styles.css          ← 排版与组件样式（含打印样式）
│   └── course.js           ← 进度持久化、自测判定
│
├── content/*.md            ← 【内容源】课程正文，改内容改这里
├── build.py                ← 【生成器】content/ → HTML
│
├── docs/                   ← 【发布产物】GitHub Pages 读取此处
├── raw/*.md                ← 官方文档原文快照（核对事实用，不参与构建）
│
├── MISSION.md              ← 为什么学这个（教学的锚点）
├── RESOURCES.md            ← 资源清单，按信任度分级
├── NOTES.md                ← 教学偏好与工程约定
├── learning-records/       ← 学习记录与关键决策
├── README.md               ← 本文件
└── .gitignore
```

**核心约定**：`content/*.md` 是唯一的真相来源。
`lessons/*.html` 与 `docs/` 都是生成物，**不要手改**（下次构建会被覆盖）。

---

## 版权与致谢

课程内容是基于 [LangChain 官方 Deep Agents 文档](https://docs.langchain.com/oss/python/deepagents/overview)
的独立教学再创作，所有概念、API 名称与设计决策均归 LangChain, Inc. 所有。
引用处均标注了原文链接；`raw/` 中的快照仅为本地核对事实使用。

第三方概念引用：

- *context quarantine* — [Drew Breunig, "How to fix your context"](https://www.dbreunig.com/2025/06/26/how-to-fix-your-context.html)
- *Recursive Language Models* — [arXiv:2512.24601](https://arxiv.org/abs/2512.24601)
- *Agent Skills 标准* — [agentskills.io](https://agentskills.io/)
- *AGENTS.md* — [agents.md](https://agents.md/)
- *MCP* — [modelcontextprotocol.io](https://modelcontextprotocol.io/)
