---
num: 13
slug: skills-progressive-disclosure
title: Skills：渐进式披露
module: W3
tier: A
minutes: 13
desc: 启动只读 frontmatter，相关时才读正文 —— 用一次文件读取换一个不膨胀的 prompt
lede: 如果你想理解"上下文工程"这个词到底在工程什么，Skills 是最好的样本。它把"能力"从 <b>必须常驻 prompt</b> 变成了 <b>一个可以被检索的资源</b>。
source: https://docs.langchain.com/oss/python/deepagents/skills
source_title: Skills（官方）
---

## 先看它解决的问题

假设你有 20 项专业技能要交给 agent（怎么写周报、怎么跑发布流程、怎么分析财报、怎么做代码审查……）。
朴素做法是把 20 段说明全部塞进 system prompt：

<div class="flow">
  <div class="node dim"><span class="k">朴素做法</span><span class="v">20 段说明常驻 prompt → 每轮都付 20 倍的固定成本</span></div>
  <div class="arrow">vs</div>
  <div class="node hi"><span class="k">Skills</span><span class="v">常驻只有 20 行 description → 用到才读正文</span></div>
</div>

官方对这种"目录 + 按需加载"的做法有个正式名字：**渐进式披露（progressive disclosure）**。

## 文件结构

一个技能就是一个目录，里面必须有 `SKILL.md`：

```text
skills/
└── langgraph-docs/
    ├── SKILL.md              ← 必需：frontmatter + 指令正文
    ├── scripts/
    │   └── fetch_docs.py     ← 可选：可执行脚本
    ├── references/
    │   ├── api-patterns.md   ← 可选：参考资料
    │   └── style-guide.md
    └── assets/               ← 可选：模板、素材
```

`SKILL.md` 的开头是 YAML frontmatter，只有两项是必需的：

```markdown
---
name: langgraph-docs
description: Fetch relevant LangGraph documentation to provide accurate guidance.
---

# langgraph-docs

Use the fetch_url tool to read https://docs.langchain.com/llms.txt,
then fetch the relevant pages.
```

## 加载分两步

<div class="flow col">
  <div class="node"><span class="k">① 启动时</span><span class="v">只读所有 SKILL.md 的 frontmatter（name + description）→ 进 prompt</span></div>
  <div class="arrow">↓ 任务到来</div>
  <div class="node hi"><span class="k">② 需要时</span><span class="v">agent 判断某个 skill 相关 → 用 read_file 读 SKILL.md 正文</span></div>
  <div class="arrow">↓ 正文里提到别的文件</div>
  <div class="node"><span class="k">③ 更深一层</span><span class="v">再按需读 references/ 或执行 scripts/ 里的东西</span></div>
</div>

!!! key "所以 description 是整个机制的关键"
    启动时唯一进 prompt 的就是 `name` + `description`。
    **agent 完全靠 description 决定要不要激活这个技能。**

    官方给的对照：

    - ✅ Good：具体说明"做什么"和"什么时候用"
    - ❌ Poor：太模糊，无法可靠匹配

    写不好 description 的后果不是"技能不好用"，而是**技能永远不会被激活**。
    这是渐进式披露的全部代价：**匹配质量压在一行文字上。**

## 三类附属资源

| 目录 | 放什么 | agent 怎么用 |
| - | - | - |
| `scripts/` | 可执行脚本 | 直接运行（需要沙箱才能跑） |
| `references/` | 参考文档、API 说明 | 按需 `read_file` |
| `assets/` | 模板、素材、样例 | 读取或复制 |

`SKILL.md` 正文里要**明确写出这些文件的路径**，否则 agent 不知道它们存在。

## 技能可以带工具

这是容易被忽略的一层：技能不仅能带"知识"，还能带"能力"。

```python
# 概念示意：技能里可以声明它需要哪些工具
skills = [{
    "path": "/skills/linear/",
    "tools": ["mcp_linear_list_issues_ab12"],   # 精确列出
}]
```

- **按名精确列出**：最可控，但名字会变（MCP 工具名可能带后缀）。
- **按 MCP server 全量**：方便，但把整个 server 的工具都暴露了。
- **保持可搜索**：让 agent 在需要时自己去找（"keep a tool searchable"）。

!!! tip "技能与工具的最佳配比"
    一个只做"生成周报"的技能，不需要读数据库的工具。
    **技能是把工具收窄的天然载体**——比在主 agent 上挂着所有工具、
    再靠 prompt 提醒"这个话题不要用那个工具"要可靠得多。

## 技能的来源与作用域

技能路径是虚拟文件系统里的路径，所以：

| 场景 | 做法 |
| - | - |
| 本地开发 | 放在 `FilesystemBackend` 的目录里 |
| 生产、跨会话 | 放在 `StoreBackend` 的 `/skills/` 路由里 |
| 每个用户一套技能 | namespace 用 `user.identity` |
| 按上下文筛选 | 用 skill 的选择条件决定这次加载哪些 |
| 隔离技能库 | 不同 subagent 挂不同技能目录 |

!!! warning "subagent 的技能不继承"
    官方说得很清楚：**只有 `general-purpose` subagent 会继承主 agent 的技能。**
    其他声明式 subagent 必须在自己的 `skills` 字段里显式指定。
    而且技能状态是**完全隔离**的——subagent 加载的技能父 agent 看不到，反之亦然。
    每个带技能的 subagent 拥有**独立的 `SkillsMiddleware` 实例**。

## 技能的权限

技能可以是只读的（开发者定义的工作流，通常不该被 agent 改），
也可以是可写的（agent 从经验里学习、更新流程）。
还会遇到"写入需要人工批准"的情形——这走 `interrupt_on`。

## 排障优先看这三件事

| 症状 | 先查什么 |
| - | - |
| 技能没被激活 | `description` 是否具体到能与任务匹配 |
| 启动时技能缺失 | 路径是否正确、backend 里文件是否真的存在 |
| 改了技能没生效 | 是否需要 reload / pin；技能缓存是启动时读的 |

```quiz
Q: 启动时进入 prompt 的技能信息包含哪些？
- 完整的 SKILL.md 正文与附属文件
- 仅 scripts/ 与 references/ 的文件名
* 只有每个 SKILL.md 的 name 与 description
- name、description 与 references 的前 10 行
E: 这是渐进式披露的核心：启动时只读 frontmatter（name + description），正文只在任务需要时通过 read_file 加载。

Q: 一个技能因为 description 写得太模糊而无法被激活，根本原因是什么？
- 模型的上下文窗口不足以容纳技能列表
- 技能的 frontmatter 缺少必填字段
* 匹配决策完全依赖这一行文字
- 技能目录没有放到正确的位置
E: 因为启动时 agent 只看到 name 与 description，它必须靠这行文字判断相关性。官方因此强调 description 要具体说明做什么和什么时候用。

Q: 关于 subagent 的技能，哪个说法正确？
- 所有声明式 subagent 自动继承主 agent 的技能
- subagent 加载的技能对父 agent 可见以便共享
* 只有 general-purpose subagent 继承；技能状态完全隔离
- subagent 不能使用技能，只能用主 agent 的技能
E: 官方明确：只有 general-purpose subagent 继承主 agent 的 skills；声明式 subagent 需要自己配置。技能状态完全隔离，子代理加载的技能父级看不到，反之亦然。
```

## 下一课

Skills 是"按需加载的知识"。而**memory** 是它的反面：总是加载。
下一课看这两者的分工，以及记忆的四种作用域。
