---
num: 36
slug: data-analysis-agent
title: 成品模式二：Data Analysis Agent
module: W7
tier: B
minutes: 11
desc: 沙箱 + 数据上传 + 自定义工具 —— 当 agent 需要真的跑代码
lede: 调研 agent 只读世界，分析 agent 要动手算。这个模式引入了两个新部件：一个能跑 Python 的沙箱，和一条把数据送进去的通道。它也是"两个平面"（第 09 课）最直观的演示。
source: https://docs.langchain.com/oss/python/deepagents/data-analysis
source_title: Build a data analysis agent（官方）
---

## 架构上的关键变化

<div class="compare">
<div class="yes">
<h4>Research agent</h4>
<ul>
<li>工具：搜索</li>
<li>默认 backend 够用</li>
<li>产出：文本报告</li>
<li>不需要执行</li>
</ul>
</div>
<div class="no">
<h4>Data analysis agent</h4>
<ul>
<li>工具：搜索 + 自定义工具</li>
<li><b>需要沙箱 backend</b></li>
<li>产出：图表 + 分析</li>
<li>必须能跑 Python</li>
</ul>
</div>
</div>

**"要跑代码"这一个需求，把 backend 从 StateBackend 推到了 Sandbox。**
这是第 07 课那张对照表的一个具体应用。

## 三个必须搭的部件

### 部件一：沙箱 backend

因为要做：
- 用 pandas 读数据
- 做聚合计算
- 用 matplotlib 画图

这些都需要一个能执行 Python 的环境，而且需要隔离——因为你还想让 agent
自己检查它画的图对不对。

!!! note "回到第 09 课：为什么必须隔离"
    官方对沙箱动机的表述是 "you can't predict what an agent might do"。
    一个生成代码的 agent 可能写出任何东西。
    **沙箱不是为了防恶意，是为了防不可预测。**

### 部件二：数据上传通道（控制平面）

官方有一节 "Upload sample data"，演示的是：

```python
# 概念流程：造样本数据 → 转成字节 → 上传到 backend
# 1. 创建样本销售数据
# 2. 转成 CSV bytes
# 3. 上传到 backend
```

这就是第 09 课的**控制平面**：agent 用工具操作文件（模型平面），
你的程序用 SDK 上传下载（控制平面）。

!!! key "为什么必须教模型"看到"数据"
    这个模式里数据是**种子（seeded）**进沙箱的，不是 agent 生成的。
    agent 需要知道"有哪些文件、字段是什么"才能写对代码。

    所以播种之后通常还要让 agent 先 `ls` + `read_file` 看一下数据结构
    ——**这正是虚拟文件系统把"数据"和"工具"统一起来的好处**：
    探查数据用的是它已经会的文件工具。

### 部件三：自定义工具

官方有一节 "Implement custom tools"。这个模式里自定义工具的典型职责是：

| 工具类型 | 例子 |
| - | - |
| 数据获取 | 从数据库/API 拉一批数据写进沙箱 |
| 领域计算 | 封装业务口径的指标计算 |
| 结果取回 | 把产物打包或转存 |

!!! tip "领域计算为什么值得做成工具"
    因为**业务口径不该由模型临场发挥**。
    "活跃用户"怎么定义、"毛利率"用哪个公式——这些应该写死在代码里，
    让 agent 调用，而不是让它在每次分析里自己写一遍并可能写错。

    这和第 26 课的分类法同源：**能确定性解决的，不要交给模型。**

## 开启任务规划

官方在这个模式里**显式开启了任务规划**（"Enable task planning"）。

理由很自然：数据分析是天然多阶段的：

<div class="flow col">
  <div class="node"><span class="k">① 探查数据</span><span class="v">有哪些列、什么类型、缺不缺</span></div>
  <div class="node"><span class="k">② 计算分析</span><span class="v">聚合、分组、对比</span></div>
  <div class="node"><span class="k">③ 可视化</span><span class="v">多张图，每张一个角度</span></div>
  <div class="node hi"><span class="k">④ 结论</span><span class="v">解释图表说明了什么</span></div>
</div>

用 `write_todos` 把这四步写下来的好处是：**用户能看到进度**（第 31 课），
而且模型不容易漏掉某一步。

## agent 实际会写什么代码

官方给的运行记录里，agent 生成的代码很有代表性：

```python
# Set style for beautiful plots
# Read the data
# Analysis
# Create visualizations
#   1. Revenue by Date
#   2. Units Sold by Date
#   3. Revenue by Product (Pie Chart)
#   4. Total Revenue by Product (Bar Chart)
#   ...
```

注意两件事：

1. **它会设置绘图样式**（"Set style for beautiful plots"）——说明它在意产出的质量。
2. **它一次生成多张图，每张回答一个角度**——这是"多视图分析"的自然做法。

!!! note "这也解释了为什么 read_file 要支持图片"
    第 18 课讲过 `read_file` 能返回图像内容块。
    在这个模式里这不是锦上添花：**agent 需要看图来判断自己画得对不对**
    （坐标轴乱了、标签重叠、数据全是 0）。

    **这是"agent 能检查自己的产出"的一个具体实例。**

## 与前端模式的配合

这个模式几乎必然要配前端沙箱界面（第 33 课）：

| 需要展示 | 对应组件 |
| - | - |
| 有哪些数据文件 | 文件浏览器 |
| agent 写的分析脚本 | 代码查看器 |
| 脚本怎么改的 | diff 面板 |
| 生成的图表 | 产物取回 + 渲染 |

**这也是三个前端模式里最复杂那个的现实需求来源。**

## 一个实践提醒

!!! warning "数据别整库上传"
    官方在沙箱安全清单里明确建议：**只播种任务必需的子集**。
    这既是为了安全（少暴露），也是为了成本（沙箱存储与传输）。

    分析类的任务尤其容易踩这个坑——"把生产库导一份进去"是很自然的冲动，
    但你需要的是**这次分析需要的那几列**。

```quiz
Q: 数据分析 agent 相对研究 agent 在架构上必须增加什么？
- 一个向量数据库用于检索数据
- 一个额外的模型用于代码生成
* 一个能执行 Python 的沙箱 backend
- 一个长期记忆的 StoreBackend
E: 要用 pandas 计算、用 matplotlib 绘图，就必须有可执行环境，且因为 agent 生成的代码不可预测，需要沙箱提供隔离。

Q: 把数据文件"播种"进沙箱，走的是哪个平面？
- 模型平面，由 agent 调用 write_file 完成
- 两个平面都不需要，沙箱可直连外部数据源
* 控制平面，由宿主程序用 provider SDK 完成
- 沙箱的自动挂载机制
E: 播种是宿主程序通过 provider SDK 直接操作沙箱，属于控制平面；agent 通过 ls、read_file 等工具操作文件属于模型平面。

Q: 把领域指标计算做成自定义工具的主要理由是什么？
- 减少 agent 的 token 消耗
- 让 agent 可以并行执行多个计算
* 业务口径应由代码确定，而不是让模型每次临场发挥
- 因为沙箱不支持 pandas 的某些函数
E: 活跃用户、毛利率这类口径需要固定定义。把它写成工具让 agent 调用，避免模型每次重新实现并可能实现错，属于"能确定性解决的不要交给模型"。

Q: agent 生成多张图表后，为什么需要 read_file 支持返回图像？
- 为了把图片存进向量数据库
- 为了自动生成 PPT
* 为了让 agent 能检查自己画的图是否正确
- 为了降低绘图库的版本依赖
E: read_file 返回多模态内容块让 agent 能"看到"自己生成的图表，从而发现坐标轴错乱、标签重叠、数据全为零等问题，这是 Agent 自我校验产出的实例。
```

## 下一课

第三个成品模式把重心从"计算"移到了"内容生产"：
**一个内容构建 agent，以及它为什么要一堆配置文件。**
