#!/usr/bin/env python3
"""
Deep Agents 教学站 — 静态站点生成器

用法:
    source .venv/bin/activate
    python build.py

输入:  content/*.md          (frontmatter + markdown 正文)
       assets/styles.css     (共享样式)
       assets/course.js      (共享交互)
输出:  index.html
       lessons/<slug>.html
       reference/<slug>.html

内容里支持的自定义语法:
  1. 代码围栏      ```python ... ```           → pygments 高亮 + 语言标签
  2. 测验围栏      ```quiz ... ```             → 交互式自测组件
  3. 提示框        !!! note "标题" ...         → .callout
  4. 裸 HTML       <div class="flow">…</div>   → 流程图 / 栈图 / 对比图
"""

import html
import json
import re
import shutil
from pathlib import Path

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).parent.resolve()
CONTENT = ROOT / "content"

# 以下两个路径由 main() 根据 --out 覆盖。
# 默认（--out .）直接在仓库根生成，保持 file:// 本地浏览的工作流不变。
LESSONS = ROOT / "lessons"
REFERENCE = ROOT / "reference"
OUT = ROOT

# ---------------------------------------------------------------- 课程结构

MODULES = [
    ("W1", "模块 A · 心智模型", "Agent Harness 是什么",
     "先建立正确的心理表征：Deep Agents 不是「又一个 agent 框架」，而是在一个普通 tool-calling 循环外面，"
     "套上了一层由 middleware 组成的自适应外壳。这个模块回答『它到底是什么』。"),
    ("W2", "模块 B · 执行环境", "Agent 在哪里动手",
     "工具、虚拟文件系统、权限、沙箱、解释器——harness 的四层执行环境。"
     "其中『虚拟文件系统 + 可插拔 backend』是整个 harness 的地基，后面几乎所有能力都建在它上面。"),
    ("W3", "模块 C · 上下文工程", "Agent 知道什么",
     "harness 真正解决的问题不是『能不能调用工具』，而是『上下文窗口怎么不爆』。"
     "这个模块拆开四个上下文层：输入、压缩、隔离、长期记忆。"),
    ("W4", "模块 D · 委派", "把大问题拆小",
     "context quarantine 的实现方式：同步 subagent 隔离上下文，dynamic subagent 用代码编排，"
     "async subagent 跨请求长跑，todo 列表给模型一个可问责的进度载体。"),
    ("W5", "模块 E · 运行时管控", "人在回路与韧性",
     "让一个会自己动手的 agent 可被安全地放进生产：中断、重试、降级、按模型/供应商打补丁的 profile。"),
    ("W6", "模块 F · 流式与前端", "让过程可见",
     "agent 跑起来是一棵会分叉的树，流式接口就是把这棵树投影成前端能渲染的若干条流。"),
    ("W7", "模块 G · 应用与生产", "从模式到上线",
     "官方给出的四个成品 agent 模式，以及把它们送进生产要补的课。"),
]

# ---------------------------------------------------------------- frontmatter

def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    head = text[3:end].strip("\n")
    body = text[end + 4:]
    if body.startswith("\n"):
        body = body[1:]
    meta = {}
    for line in head.splitlines():
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, body


# ---------------------------------------------------------------- 测验解析

QUIZ_BLOCK_RE = re.compile(r"```quiz[ \t]*\n(.*?)```", re.S)


def extract_quiz(src: str):
    """抽出所有 quiz 围栏，返回 (去掉 quiz 的正文, [题目, ...])"""
    questions = []

    def _grab(m):
        raw = m.group(1)
        cur = None
        for line in raw.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("Q:"):
                cur = {"q": s[2:].strip(), "opts": [], "answer": -1, "explain": ""}
                questions.append(cur)
            elif s.startswith("E:"):
                if cur is not None:
                    cur["explain"] = s[2:].strip()
            elif s.startswith("* "):
                if cur is not None:
                    cur["answer"] = len(cur["opts"])
                    cur["opts"].append(s[2:].strip())
            elif s.startswith("- "):
                if cur is not None:
                    cur["opts"].append(s[2:].strip())
        return ""

    body = QUIZ_BLOCK_RE.sub(_grab, src)
    for q in questions:
        if q["answer"] < 0:
            raise ValueError("测验题缺少正确项（用 `* ` 标记）: " + q["q"][:40])
    return body, questions


def render_quiz(slug: str, questions) -> str:
    if not questions:
        return ""
    out = [
        f'<section class="quiz" data-slug="{html.escape(slug)}">',
        '<div class="quiz-head"><span>检索练习 · 不要回看上文，先试着回忆</span>'
        f'<span class="score">0 / {len(questions)} 正确</span></div>',
        '<div class="quiz-body">',
    ]
    letters = "ABCDEFGH"
    for i, q in enumerate(questions):
        out.append(f'<div class="q" data-answer="{q["answer"]}">')
        out.append(f'<div class="q-text"><span class="qno">{i + 1:02d}</span>{q["q"]}</div>')
        out.append('<ul class="opts">')
        for j, o in enumerate(q["opts"]):
            out.append(f'<li><span class="mk">{letters[j]}</span><span>{o}</span></li>')
        out.append("</ul>")
        if q["explain"]:
            out.append(f'<div class="explain"><b>解析 · </b>{q["explain"]}</div>')
        out.append("</div>")
    out.append("</div>")
    out.append('<div class="quiz-foot"><span class="result"></span><br>'
               '<button class="reset">重做</button>'
               '<button class="reveal">显示全部解析</button></div>')
    out.append("</section>")
    return "\n".join(out)


# ---------------------------------------------------------------- markdown

MD = markdown.Markdown(extensions=[
    "tables",
    "fenced_code",
    "admonition",
    "md_in_html",
    "attr_list",
    "toc",
    CodeHiliteExtension(css_class="highlight", guess_lang=False, linenums=False, pygments_style="material"),
], extension_configs={})


def convert_md(src: str):
    MD.reset()
    out = MD.convert(src)
    # admonition → callout
    repl = {
        '<div class="admonition note">': '<div class="callout key">',
        '<div class="admonition info">': '<div class="callout key">',
        '<div class="admonition tip">': '<div class="callout">',
        '<div class="admonition hint">': '<div class="callout">',
        '<div class="admonition success">': '<div class="callout">',
        '<div class="admonition warning">': '<div class="callout warn">',
        '<div class="admonition caution">': '<div class="callout warn">',
        '<div class="admonition danger">': '<div class="callout trap">',
        '<div class="admonition error">': '<div class="callout trap">',
        '<div class="admonition bug">': '<div class="callout trap">',
        '<p class="admonition-title">': '<p class="callout-title">',
    }
    for k, v in repl.items():
        out = out.replace(k, v)
    out = re.sub(r'<div class="admonition([^"]*)"', '<div class="callout"', out)
    out = out.replace('<p class="admonition-title">', '<p class="callout-title">')
    return out, getattr(MD, "toc", "")


def add_code_labels(src_md: str, html_out: str) -> str:
    """按源码里 fence 出现的顺序，给每个高亮块加语言标签。"""
    langs = re.findall(r"^```([A-Za-z0-9_+-]+)[ \t]*$", src_md, re.M)
    parts = html_out.split('<div class="highlight">')
    if len(parts) == 1:
        return html_out
    out = [parts[0]]
    for i, chunk in enumerate(parts[1:]):
        lang = langs[i] if i < len(langs) else ""
        label = ""
        if lang:
            pretty = {"py": "python", "sh": "bash", "js": "javascript", "ts": "typescript"}.get(lang, lang)
            label = f'<div class="code-label">{html.escape(pretty or "")}</div>'
        out.append(label + '<div class="highlight">' + chunk)
    return "".join(out)


# ---------------------------------------------------------------- 载入内容

def load_content():
    lessons, refs = [], []
    for path in sorted(CONTENT.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta.get("slug"):
            continue
        meta.setdefault("tier", "B")
        meta.setdefault("minutes", "10")
        meta.setdefault("module", "A")
        meta.setdefault("num", "0")
        meta["num"] = int(meta["num"])
        meta.setdefault("source", "")
        meta.setdefault("source_title", "官方原文")
        meta.setdefault("lede", "")
        meta.setdefault("desc", "")
        meta["_path"] = path
        meta["_body"] = body
        if meta.get("kind") == "reference":
            refs.append(meta)
        else:
            lessons.append(meta)
    lessons.sort(key=lambda m: m["num"])
    refs.sort(key=lambda m: str(m.get("sort", m["slug"])))
    return lessons, refs


# ---------------------------------------------------------------- 模板

def esc(s):
    return html.escape(s, quote=True)


def sidebar_html(lessons, refs, active_slug, base):
    out = ['<aside class="sidebar">']
    out.append(
        f'<div class="sidebar-brand"><a href="{base}index.html">Deep Agents 教学站</a>'
        '<span class="sub">Agent Harness 原理 · 中文</span></div>'
    )
    for key, title, _sub, _intro in MODULES:
        group = [les for les in lessons if les["module"] == key]
        if not group:
            continue
        out.append(f'<div class="nav-group"><div class="nav-group-title">{esc(title)}</div><ul>')
        for les in group:
            cls = ' class="active"' if les["slug"] == active_slug else ""
            out.append(
                f'<li><a href="{base}lessons/{les["slug"]}.html" data-slug="{les["slug"]}"{cls}>'
                f'<span class="num">{les["num"]:02d}</span><span>{esc(les["title"])}</span>'
                f'<span class="tier">{les["tier"]}</span></a></li>'
            )
        out.append("</ul></div>")
    if refs:
        out.append('<div class="nav-group"><div class="nav-group-title">速查手册</div><ul>')
        for r in refs:
            cls = ' class="active"' if r["slug"] == active_slug else ""
            out.append(
                f'<li><a href="{base}reference/{r["slug"]}.html" data-slug="{r["slug"]}"{cls}>'
                f'<span class="num">▸</span><span>{esc(r["title"])}</span></a></li>'
            )
        out.append("</ul></div>")
    out.append("</aside>")
    return "\n".join(out)


def page(title, body, lessons, refs, active_slug, base, crumbs, extra_head=""):
    site = {
        "lessons": [{"slug": les["slug"], "num": les["num"], "title": les["title"], "module": les["module"], "tier": les["tier"]} for les in lessons],
        "refs": [{"slug": r["slug"], "title": r["title"]} for r in refs],
    }
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Deep Agents 教学站</title>
<meta name="description" content="深入理解 Deep Agents agent harness 原理的中文教学站">
<link rel="stylesheet" href="{base}assets/styles.css">
{extra_head}
</head>
<body>
<div class="shell">
{sidebar_html(lessons, refs, active_slug, base)}
<div class="main">
  <div class="topbar"><div class="wrap">
    <button class="menu-btn" aria-label="切换目录">☰</button>
    <span class="crumbs">{crumbs}</span>
    <span class="progress-pill">
      <span class="txt">0%</span>
      <span class="bar"><i></i></span>
    </span>
  </div></div>
  <div class="wrap">
{body}
  </div>
</div>
</div>
<script>window.SITE = {json.dumps(site, ensure_ascii=False)};</script>
<script src="{base}assets/course.js"></script>
</body>
</html>
"""


# ---------------------------------------------------------------- 生成单课

def build_lesson(meta, lessons, refs):
    slug = meta["slug"]
    body_md, questions = extract_quiz(meta["_body"])
    html_body, toc = convert_md(body_md)
    html_body = add_code_labels(body_md, html_body)

    idx = lessons.index(meta)
    prev_l = lessons[idx - 1] if idx > 0 else None
    next_l = lessons[idx + 1] if idx + 1 < len(lessons) else None

    tier_label = "Tier A · 原理深挖" if meta["tier"] == "A" else "Tier B · 集成速览"
    tier_cls = "" if meta["tier"] == "A" else " b"

    parts = []
    parts.append(f"""<header class="lesson-head">
  <div class="lesson-kicker">
    <span>第 {meta['num']:02d} 课</span>
    <span class="dot">·</span>
    <span>{esc(meta['module_cn'])}</span>
    <span class="dot">·</span>
    <span>{esc(meta['minutes'])} 分钟</span>
    <span class="tier-badge{tier_cls}">{esc(tier_label)}</span>
  </div>
  <h1>{esc(meta['title'])}</h1>
  <p class="lede">{meta['lede']}</p>
</header>""")

    toc_box = ""
    if toc:
        toc_box = ('<details class="toc-box"><summary>本页目录</summary>'
                   + toc.replace('<div class="toc">', '').replace('</div>', '', 1)
                   + '</details>')

    parts.append('<article>')
    parts.append(toc_box)
    parts.append(html_body)
    parts.append('</article>')

    parts.append(render_quiz(slug, questions))

    parts.append(f"""<div class="mastery">
  <label><input type="checkbox" data-slug="{slug}">
  <span>本课已掌握
  <span class="hint">勾选后，左侧目录和首页会标记完成，进度保存在本机浏览器里。
  能通过上面的自测、并且能不看笔记复述本课的核心机制，再勾。</span></span></label>
</div>""")

    # 页脚
    src_box = ""
    if meta["source"]:
        src_box = (f'<div class="source-box"><span class="lbl">本课事实来源 · 建议通读原文</span>'
                   f'<a href="{esc(meta["source"])}" target="_blank" rel="noopener">{esc(meta["source_title"])}</a>'
                   f'<br><span style="color:#8b909c;font-size:11.5px">{esc(meta["source"])}</span></div>')

    prevnext = ['<div class="prevnext">']
    if prev_l:
        prevnext.append(f'<a class="prev" href="{prev_l["slug"]}.html"><span class="dir">← 上一课</span>'
                        f'<span class="ttl">{esc(prev_l["title"])}</span></a>')
    else:
        prevnext.append('<a class="prev" href="../index.html"><span class="dir">← 返回</span>'
                        '<span class="ttl">课程地图</span></a>')
    if next_l:
        prevnext.append(f'<a class="next" href="{next_l["slug"]}.html"><span class="dir">下一课 →</span>'
                        f'<span class="ttl">{esc(next_l["title"])}</span></a>')
    prevnext.append('</div>')

    parts.append(f"""<footer class="lesson-foot">
  {src_box}
  <div class="ask-teacher">有讲不清楚的地方，直接把问题抛给我——我是这门课的老师，
  可以就任何一节、任何一行代码展开，也可以按你的问题临时加一课。</div>
  {''.join(prevnext)}
</footer>""")

    crumbs = (f'<a href="../index.html">课程地图</a> / <b>{esc(meta["module_cn"])}</b> / '
              f'<b>第 {meta["num"]:02d} 课</b>')
    out = page(meta["title"], "\n".join(parts), lessons, refs, slug, "../", crumbs)
    (LESSONS / f"{slug}.html").write_text(out, encoding="utf-8")
    return out


# ---------------------------------------------------------------- 生成参考页

def build_reference(meta, lessons, refs):
    slug = meta["slug"]
    body_md, questions = extract_quiz(meta["_body"])
    html_body, toc = convert_md(body_md)
    html_body = add_code_labels(body_md, html_body)
    parts = [f"""<header class="lesson-head">
  <div class="lesson-kicker"><span>速查手册</span><span class="dot">·</span>
  <span>随手翻，不按顺序读</span><span class="tier-badge b">REFERENCE</span></div>
  <h1>{esc(meta['title'])}</h1>
  <p class="lede">{meta['lede']}</p>
</header>"""]
    if toc:
        parts.append('<details class="toc-box"><summary>本页目录</summary>'
                     + toc.replace('<div class="toc">', '').replace('</div>', '', 1) + '</details>')
    parts.append('<article>' + html_body + '</article>')
    parts.append(render_quiz(slug, questions))
    parts.append('<footer class="lesson-foot"><div class="ask-teacher">'
                 '这份手册会随着课程推进不断补条目。发现缺了什么，直接告诉老师。</div>'
                 '<div class="prevnext"><a href="../index.html"><span class="dir">← 返回</span>'
                 '<span class="ttl">课程地图</span></a></div></footer>')
    crumbs = f'<a href="../index.html">课程地图</a> / <b>速查手册</b> / <b>{esc(meta["title"])}</b>'
    out = page(meta["title"], "\n".join(parts), lessons, refs, slug, "../", crumbs)
    (REFERENCE / f"{slug}.html").write_text(out, encoding="utf-8")
    return out


# ---------------------------------------------------------------- 生成首页

def build_index(lessons, refs):
    total_min = sum(int(les["minutes"]) for les in lessons)
    n_a = sum(1 for les in lessons if les["tier"] == "A")

    parts = [f"""<header class="hero">
  <div class="lesson-kicker"><span>Deep Agents · Agent Harness 原理</span></div>
  <h1>看穿 Agent Harness 的内部构造</h1>
  <p class="lede">这门课不复述官方文档，而是把 Deep Agents 拆开：
  一次 <code>create_deep_agent()</code> 到底装配了什么，
  上下文窗口是怎么被管住的，委派为什么能省 token，
  以及一个人工智能体要被安全地放进生产还需要补哪几层。
  全部内容基于官方文档 v0.x 快照，覆盖左侧导航 <b>全部 35 个页面</b>。</p>
  <div class="hero-stats">
    <div><b>{len(lessons)}</b>课</div>
    <div><b>{len(MODULES)}</b>个模块</div>
    <div><b>{n_a}</b>课原理深挖</div>
    <div><b>{total_min // 60}h{total_min % 60:02d}m</b>总时长</div>
    <div><b>{len(refs)}</b>份速查手册</div>
  </div>
</header>"""]

    parts.append("""<div class="callout key">
<p class="callout-title">先读这一段 · 这门课怎么用</p>
<p>课程按「先建心智模型 → 再拆执行环境 → 再拆上下文 → 再拆委派 → 最后管控与上线」的顺序排列。
<code>Tier A</code> 的课需要逐字读、逐行读代码；<code>Tier B</code> 的课是集成与教程类，
读机制要点 + 关键 API 即可。每课结尾都有 2–4 道检索题，
<b>请不要回看上文</b>——努力回忆的过程本身才是学习发生的地方。</p>
<p>你没有 API Key，所以这门课的练习形式是<b>读代码 + 推演机制 + 离线自测</b>，
而不是把 demo 跑通。这恰好更利于长期记忆。</p>
</div>""")

    parts.append("""<h2 style="border:0;margin-bottom:.2em">推荐学习路径</h2>
<ol class="path-list">
<li><b>第 01–04 课</b> — 建立心智模型。这四课决定你后面看任何一节时，「它插在哪儿」这个问题有没有答案。</li>
<li><b>第 05–10 课</b> — 执行环境。重点不是 API 怎么写，而是理解为什么「虚拟文件系统」是地基。</li>
<li><b>第 11–18 课</b> — 上下文工程。这是 harness 存在的理由，值得反复读。</li>
<li><b>第 19–24 课</b> — 委派。理解 context quarantine 与三种 subagent 的分工。</li>
<li><b>第 25–27 课</b> — 管控。中断、韧性、profile。</li>
<li><b>第 28–33 课</b> — 流式与前端。想明白「一棵树怎么变成几条流」。</li>
<li><b>第 34–40 课</b> — 成品模式与生产。可以跳读，按需回看。</li>
</ol>""")

    for key, title, sub, intro in MODULES:
        group = [les for les in lessons if les["module"] == key]
        if not group:
            continue
        parts.append('<section class="module-block">')
        parts.append(f'<div class="module-head"><h2>{esc(title)}</h2>'
                     f'<span class="tag">{esc(sub)} · {len(group)} 课</span></div>')
        parts.append(f'<p class="module-intro">{intro}</p>')
        parts.append('<div class="cards">')
        for les in group:
            tcls = "A" if les["tier"] == "A" else "B"
            parts.append(
                f'<a class="card" data-slug="{les["slug"]}" href="lessons/{les["slug"]}.html">'
                f'<span class="cn"><span>第 {les["num"]:02d} 课 · {les["minutes"]} 分钟</span>'
                f'<span class="t">{tcls}</span></span>'
                f'<span class="ct">{esc(les["title"])}</span>'
                f'<span class="cd">{les["desc"]}</span></a>'
            )
        parts.append("</div></section>")

    if refs:
        parts.append('<section class="module-block"><div class="module-head">'
                     '<h2>速查手册</h2><span class="tag">Reference · 常回来翻</span></div>'
                     '<p class="module-intro">课程会被遗忘，手册不会。这些是把课压缩到最小后的可检索形态，'
                     '也是这门课里最值得打印出来的部分。</p><div class="ref-grid">')
        for r in refs:
            parts.append(f'<a class="card" href="reference/{r["slug"]}.html">'
                         f'<span class="cn"><span>速查</span></span>'
                         f'<span class="ct">{esc(r["title"])}</span>'
                         f'<span class="cd">{r["desc"]}</span></a>')
        parts.append("</div></section>")

    parts.append("""<section class="module-block"><div class="module-head">
<h2>关于「智慧」</h2><span class="tag">Wisdom</span></div>
<p class="module-intro">把机制读懂只是知识。真正的检验发生在你用它去解释一个奇怪的现象、
或者向别人指出一个设计取舍的时候。这门课建议你把疑问带到社区里去验证：</p>
<ul>
<li><a href="https://forum.langchain.com/" target="_blank" rel="noopener">LangChain Forum</a> — 官方维护，适合问 harness 行为与版本问题。</li>
<li><a href="https://github.com/langchain-ai/deepagents/issues" target="_blank" rel="noopener">deepagents GitHub Issues</a> — 源码级追问，或确认是不是 bug。</li>
<li><a href="https://www.reddit.com/r/LangChain/" target="_blank" rel="noopener">r/LangChain</a> — 生产踩坑经验。</li>
</ul>
</section>""")

    out = page("课程地图", "\n".join(parts), lessons, refs, "", "", '<b>课程地图</b>')
    (OUT / "index.html").write_text(out, encoding="utf-8")


# ---------------------------------------------------------------- main

def main():
    global LESSONS, REFERENCE, OUT

    import argparse
    ap = argparse.ArgumentParser(description="生成 Deep Agents 教学站")
    ap.add_argument(
        "--out", default=".",
        help="站点输出目录（相对仓库根或绝对路径）。默认 '.'，即仓库根。",
    )
    args = ap.parse_args()
    OUT = Path(args.out)
    if not OUT.is_absolute():
        OUT = (ROOT / OUT).resolve()
    LESSONS = OUT / "lessons"
    REFERENCE = OUT / "reference"

    LESSONS.mkdir(parents=True, exist_ok=True)
    REFERENCE.mkdir(parents=True, exist_ok=True)
    lessons, refs = load_content()
    if not lessons:
        raise SystemExit("content/ 下没有找到课程，先写内容。")

    module_names = {k: t for k, t, _, _ in MODULES}
    for les in lessons + refs:
        les["module_cn"] = module_names.get(les["module"], les["module"])

    # slug 必须全局唯一：它同时是文件名、导航锚点与 localStorage 进度键。
    seen = {}
    for item in lessons + refs:
        s = item["slug"]
        if s in seen:
            raise SystemExit(
                f"slug 冲突：{s!r} 同时出现在 '{seen[s]}' 与 '{item['_path'].name}'。"
                "改掉其中一个再构建。"
            )
        seen[s] = item["_path"].name

    for les in lessons:
        build_lesson(les, lessons, refs)
    for r in refs:
        build_reference(r, lessons, refs)
    build_index(lessons, refs)

    # 把 pygments 需要的 token 类也写进一个独立文件，方便日后换主题
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "assets" / "pygments.css").write_text(
        HtmlFormatter(style="material").get_style_defs(".highlight"), encoding="utf-8")

    if OUT != ROOT:
        # 输出目录与源目录不同（例如 --out docs）：把共享组件一并拷过去，
        # 使输出目录成为可独立发布的完整站点。
        for name in ("styles.css", "course.js"):
            shutil.copy2(ROOT / "assets" / name, OUT / "assets" / name)

        # GitHub Pages 默认会跑 Jekyll。.nojekyll 让它跳过处理，
        # 否则以下划线开头的文件/目录会被忽略，且构建会变慢。
        (OUT / ".nojekyll").write_text("", encoding="utf-8")

    where = "仓库根" if OUT == ROOT else str(OUT.relative_to(ROOT)) if str(OUT).startswith(str(ROOT)) else str(OUT)
    print(f"✓ 输出到 {where}：{len(lessons)} 课 + {len(refs)} 份速查手册")
    for les in lessons:
        print(f"   {les['num']:02d}  [{les['module']}/{les['tier']}] {les['title']}  ->  lessons/{les['slug']}.html")
    for r in refs:
        print(f"   ·   [REF]  {r['title']}  ->  reference/{r['slug']}.html")


if __name__ == "__main__":
    main()
