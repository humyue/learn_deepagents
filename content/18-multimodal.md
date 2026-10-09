---
num: 18
slug: multimodal
title: 多模态输入与输出
module: W3
tier: B
minutes: 8
desc: 图片、视频、音频、文档如何在文本循环里进出
lede: agent 的循环是文本的，但世界不是。<code>read_file</code> 把非文本文件变成多模态内容块，这条通道比你想的更自然地融入了虚拟文件系统。
source: https://docs.langchain.com/oss/python/deepagents/multimodal
source_title: Multimodal（官方）
---

## 支持的扩展名

`read_file` 在**所有 backend 上**都原生支持把这些文件当作多模态内容块返回：

| 类型 | 扩展名 |
| - | - |
| **图片** | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.heic` `.heif` |
| **视频** | `.mp4` `.mpeg` `.mov` `.avi` `.flv` `.mpg` `.webm` `.wmv` `.3gpp` |
| **音频** | `.wav` `.mp3` `.aiff` `.aac` `.ogg` `.flac` |
| **文件** | `.pdf` `.ppt` `.pptx` |

!!! key "这条设计的优雅之处"
    **多模态不需要一套新工具，只需要 `read_file` 认识新扩展名。**

    `ls` → `read_file` 的路径依然成立：
    agent 先列目录看到 `chart.png`，再读它，就得到了图像内容。
    它不需要知道"我现在用的是图像工具"——**同一个工具，不同的返回类型**。
    这就是统一抽象（第 06 课）的复利。

## 用户的输入

用户消息里也可以带多模态内容块——这是 LangChain messages 层面的能力，
Deep Agents 只是不做任何阻碍地透传。写法见
[LangChain messages · multimodal](https://docs.langchain.com/oss/python/langchain/messages#multimodal)。

## 自定义工具输出

你的工具也可以返回多模态内容块。这打开了一类很有用的模式：

<div class="flow">
  <div class="node"><span class="k">工具生成图表</span><span class="v">matplotlib → PNG bytes</span></div>
  <div class="arrow">→</div>
  <div class="node hi"><span class="k">返回多模态块</span><span class="v">而不是 base64 字符串</span></div>
  <div class="arrow">→</div>
  <div class="node"><span class="k">模型直接"看"到图</span><span class="v">可以判断趋势、发现异常</span></div>
</div>

这也正是数据分析 agent（第 36 课）能自己检查图表质量的原因。

## 与压缩的交互

这是本课唯一需要警惕的地方：

!!! trap "内建压缩不会处理图像"
    官方明确说明：内建上下文压缩**不会**缩放图片、**不会**降低分辨率、
    **不会**生成视觉 embedding。

    后果是：**一张大图会一直占用它的全部 token 成本**，
    不管对话已经进行了多久。文本可以被 offload 和摘要，图像不会。

    实践含义：**图不是免费的文本。**
    让 agent 反复读取同一张大图，是最容易悄悄烧掉上下文预算的方式之一。
    如果场景里图像占比很高，你应该**主动**控制读图次数（用 prompt 引导，
    或者干脆在读图前先把它压缩/缩放好）。

## 检查清单

| 项 | 建议 |
| - | - |
| 图片存放 | 放在虚拟文件系统里，让 agent 按需读 |
| 图片大小 | 提前缩放，不要靠 harness 帮你省 |
| 反复读同一张图 | 用 prompt 或状态位避免 |
| 工具返回图 | 优先返回多模态块而不是 base64 字符串 |
| 视频/音频 | 成本更高，只在确实需要时暴露 |

```quiz
Q: 关于内建上下文压缩与图像的关系，官方说法是？
- 压缩会把图像缩放到低分辨率后缓存
- 压缩会为大图生成视觉 embedding 替代原图
* 压缩不会缩放、降分辨率或生成视觉 embedding
- 压缩会直接丢弃较早的图像块
E: 官方明确列出这三项"不会"。因此大图会持续占用其完整 token 成本，需要应用层主动控制读图行为。

Q: 多模态能力在 harness 里的接入方式是什么？
- 一组新增的 image_read / audio_read 工具
- 一个独立的 multimodal middleware
* read_file 按扩展名返回多模态内容块
- backend 协议里的 multimodal() 方法
E: read_file 在所有 backend 上原生支持列出的扩展名，返回多模态内容块。不需要新工具，也不改变 ls → read_file 这条路径。
```

## 模块 C 结束

到现在为止，harness 的"知道什么"讲完了。下一模块是最能体现 harness 价值的一块：
**委派**——把大问题拆成小的、可以并行、可以隔离的工作单元。
