---
num: 21
slug: forked-subagents
title: Forked Subagents：继承父级上下文
module: W4
tier: B
minutes: 9
desc: 当子任务需要"知道我们刚才聊了什么"，isolated 模式就不够用了
lede: 隔离模式的 subagent 只看到被派发的那一条任务。但有些子任务天然需要父级的完整上下文。这一课讲 <code>mode: "fork"</code> 解决了什么、代价是什么、什么时候该用。
source: https://docs.langchain.com/oss/python/deepagents/subagents#forked-subagents
source_title: Subagents · Forked subagents（官方）
---

## 两种上下文模式

<div class="compare">
<div class="yes">
<h4>mode: "isolated"（默认）</h4>
<ul>
<li>subagent <b>只看到</b>被派发的那一条任务</li>
<li>有自己独立的 system prompt（必须自己写）</li>
<li>最大的上下文节省</li>
<li>适合：完全独立、自包含的子任务</li>
</ul>
</div>
<div class="no">
<h4>mode: "fork"</h4>
<ul>
<li>subagent <b>继承父级的对话与系统提示</b></li>
<li>不需要自己写 system_prompt</li>
<li>上下文开销接近父级</li>
<li>适合：需要"接着刚才的上下文"干活</li>
</ul>
</div>
</div>

```python
forked = {
    "name": "reviewer",
    "description": "Reviews the current work in context",
    "mode": "fork",          # 继承父级对话与系统提示
    # system_prompt 可以省略；需要时写"仅用于 fork 的补充说明"
}
```

## 它长什么样

官方给了一组很直观的对比，说明"父 agent 有什么"和"fork 实际看到什么"：

```python
# 派发前，父 agent 拥有的东西
#   完整对话历史
#   系统提示（你的 + harness 的）
#   到目前为止所有工具调用与结果
#   memory / skills 等注入内容

# fork 实际看到的
#      ↑ 以上全部（是一份拷贝）
#   + 被派发的这一条任务
```

!!! key "fork = 复制当前上下文，然后换个角色继续"
    它不是"共享"上下文——是**复制一份**给子 agent。
    父 agent 的状态不会被 subagent 改动（subagent 无状态、单次交接）。
    所以它更准确的描述是：**在当前的对话语境里，用另一套指令做一件事。**

## 为什么需要它

isolated 模式有一个具体的天花板：

<div class="flow col">
  <div class="node"><span class="k">父 agent 刚做完一堆工作</span><span class="v">读了文件、跑了测试、讨论了方案</span></div>
  <div class="arrow">↓</div>
  <div class="node"><span class="k">想派一个子任务</span><span class="v">"审查刚才那三个文件"</span></div>
  <div class="arrow">↓ isolated</div>
  <div class="node dim"><span class="k">问题</span><span class="v">subagent 不知道"刚才那三个文件"是哪三个</span></div>
</div>

用 isolated 模式，你必须在 `task` 的说明里**把上下文重新写一遍**——
文件路径、需求、约束，全都得复述。
而且复述本身就有信息损失。

**fork 模式把"复述上下文"这一步消掉了。**

## 什么时候该用 fork

| 场景 | 模式 | 理由 |
| - | - | - |
| 独立调研一个外部主题 | isolated | 子任务不需要父级历史 |
| 审查刚才写出来的代码 | **fork** | 需要看到"刚才那个版本" |
| 对当前方案做对抗性反驳 | **fork** | 需要知道方案是什么 |
| 批量处理一批独立的输入 | isolated | 每个输入自包含 |
| 接着当前进度做验证 | **fork** | 需要知道进度 |

!!! warning "fork 的代价：隔离带来的收益会缩水"
    隔离模式省 token 的全部理由是"子任务只带回结论、中间噪音不进主窗口"。
    **fork 模式放弃了这一点的一半**：subagent 一开始就已经背着父级的完整上下文在跑。

    更准确地说：**fork 省掉的是"父 agent 后续要处理的噪音"，
    但省不掉"subagent 起跑时已经有的上下文成本"。**

    所以在长对话里频繁 fork，token 账单会很难看。
    经验判据：**子任务需要的历史越长，fork 越划算（因为复述成本高）；越短，isolated 越划算。**

## 一个实用细节

官方对 `system_prompt` 的说明很细：

> 对 `mode: "fork"`，**省略这个字段**，除非你需要一段"仅供 fork 使用"的补充说明。

也就是说 fork 模式下的 `system_prompt` 不是"替换"，而是"追加在父级提示之后"。
所以如果你在这里写"你是一个代码审查者"，它是在父级提示（"你是一个研究员…"）之后追加的，
两者会叠加。写的时候要意识到这一点。

## CompiledSubAgent 也支持 fork

```python
CompiledSubAgent(
    name="verifier",
    description="Verifies the current work",
    runnable=compiled_graph,
    mode="fork",     # 继承父级的消息历史
)
```

!!! note "但图自己的系统提示不会被替换"
    官方注明：compiled graph **无论哪种模式都保留自己的系统提示**。
    fork 给它的只是消息历史，不是提示词。

```quiz
Q: fork 模式与 isolated 模式最本质的区别是？
- fork 模式会共享父 agent 的可变状态
- fork 模式不需要 description 字段
* fork 模式让 subagent 继承父级的对话与系统提示
- fork 模式只对 CompiledSubAgent 生效
E: isolated（默认）下 subagent 只看到被派发的任务、必须自带 system_prompt；fork 下它继承父级的对话历史与系统提示。注意仍是复制而非共享，父级状态不会被改动。

Q: 对 fork 模式下的 system_prompt 字段，官方的说明是？
- 它是必填的，用于替换父级提示
- 它是禁用的，写了会报错
* 通常应省略，除非需要一段 fork 专用的补充说明
- 它会被自动改写为父级提示的副本
E: 官方说明：对 mode: "fork"，除非需要一段"仅用于 fork 的补充说明"，否则省略此字段。它是追加而非替换。

Q: 频繁在长对话里使用 fork 模式，主要风险是什么？
- 子 agent 会篡改父 agent 的状态
- 子 agent 无法访问文件系统工具
* 每个 fork 都背着父级完整上下文起跑，token 成本很高
- 父 agent 无法再使用 isolated 模式
E: fork 放弃了隔离带来的上下文节省：subagent 从起跑时就带有父级上下文。子任务所需历史越长，fork 越划算；越短则 isolated 越划算。
```

## 下一课

到这里讲的 subagent 都是"模型自己决定要不要开"。下一课换一个思路：
**让代码来决定开多少个、怎么并行** —— 这就是 dynamic subagents。
