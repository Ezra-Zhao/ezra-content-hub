#!/usr/bin/env python3
"""文章区构建脚本（ezra-content-hub）

用法：python3 scripts/build_articles.py

做三件事：
1. 把 articles/<系列>/<slug>.md 渲染成 docs/articles/<系列>/<slug>.html 阅读页（同站深色主题，手机优先）。
2. 扫描全部文章的 frontmatter，重建 index.json 与 docs/index.json 里的 articles 结构（系列→篇目，按日期倒序）。
3. 文章 md 格式：文件头 YAML frontmatter，字段 title / date / author / scripture（可选）/ series（目录名，可省略）。

入库流程见 README「文章入库流程」。注意：本仓为公开仓，未经 Ezra 确认的稿件不得入库。
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = ROOT / "articles"
DOCS_DIR = ROOT / "docs"
DOCS_ARTICLES = DOCS_DIR / "articles"

SERIES_META = {
    "sermons": {
        "name": "讲道集",
        "desc": "Guangyi Zhao 的讲道文稿：原文解经、逐字稿全文。已公开发布的篇目陆续归入本系列。",
        "category": "信仰",
    },
    "flash": {
        "name": "每日速报",
        "desc": "《代码与诗篇》速报：财经、科技、安全与应急的当日要点，数字逐项标注来源与证据等级。",
        "category": "时效",
    },
    "novel": {
        "name": "小说连载",
        "desc": "见证文学连载《低谷里有人陪你走》：苦难与挣扎中的真实记录，化名文学化改写，每章一个完整小故事。版权所有，非独家首发于本枢纽。",
        "category": "信仰",
    },
    "baylocal": {
        "name": "湾区本地速报",
        "desc": "圣何塞 + 硅谷湾区本地新闻：市政、交通、安全与天气、社区与学区动态，数字逐项标注来源与证据等级。",
        "category": "时效",
    },
    "tech-nvidia": {
        "name": "英伟达技术研究",
        "desc": "数据中心基础设施一线视角拆解 NVIDIA 平台：Blackwell/GB300、NVLink、液冷与供电、CUDA 与推理软件栈。只用 NVIDIA 官方公开资料，数字标出处。",
        "category": "科技",
    },
}

PAGE_CSS = """
:root{--bg:#0f1420;--card:#1a2233;--ink:#eef2f8;--sub:#9fb0c9;--acc:#e8b34b;--line:#2c3a55}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.85}
.wrap{max-width:760px;margin:0 auto;padding:22px 18px 48px}
a{color:var(--acc);text-decoration:none}
.back{font-size:13px;color:var(--sub)}
h1{font-size:23px;line-height:1.45;margin:14px 0 6px}
.meta{color:var(--sub);font-size:13px;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}
article h2{font-size:19px;margin:26px 0 8px}
article h3{font-size:16px;margin:20px 0 6px}
article p{margin:10px 0;font-size:16px}
article blockquote{border-left:3px solid var(--acc);padding:2px 0 2px 12px;margin:12px 0;color:#dbe5f2}
article ul,article ol{margin:10px 0 10px 22px}
article li{margin:4px 0}
article hr{border:none;border-top:1px solid var(--line);margin:22px 0}
footer{color:var(--sub);font-size:12px;text-align:center;margin-top:36px;border-top:1px solid var(--line);padding-top:14px}
"""


def _parse_meta_block(block):
    meta = {}
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def parse_frontmatter(text):
    """解析 md 文件头的 YAML frontmatter（只支持 key: value 平面字段）。

    容错：文件丢了开头的 --- 分隔线、只剩 key: value 头块接 --- 时也认
    （2026-11 湾区速报 8 篇曾因此整批标题丢失、页面显示「未命名」）。"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end == -1:
            return {}, text
        body = text[end + 4 :].lstrip("\n")
        return _parse_meta_block(text[3:end]), body
    # 无开头 ---：前若干行若全是 key: value 且以 --- 收尾，按 frontmatter 解析
    lines = text.splitlines()
    head = []
    for i, line in enumerate(lines[:12]):
        s = line.strip()
        if s == "---":
            if head and all(":" in h for h in head):
                return _parse_meta_block("\n".join(head)), \
                    "\n".join(lines[i + 1:]).lstrip("\n")
            break
        if not s or ":" not in s:
            break
        head.append(s)
    return {}, text


def extract_title(body):
    """标题兜底：正文首个 # 标题 → 首个非空行（去 markdown 标记）。"""
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        m = re.match(r"^#{1,4}\s+(.*)$", s)
        if m:
            return re.sub(r"[*_`]", "", m.group(1)).strip()
        if s.startswith((">", "---", "![", "（", "(")) and len(s) < 40:
            continue  # 译稿说明/引用等短行不是标题，继续往下找
        return re.sub(r"[*_`]", "", s).strip()
    return ""


def strip_md(s):
    s = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"[*_`#>]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_description(body, limit=150):
    """meta description：正文首个实质段落（报头短句自动与下一段拼接），
    去标记后截断到约 limit 字。"""
    texts = []
    for block in re.split(r"\n\s*\n", body):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith(("#", "![", "---", "***")):
            continue
        if re.match(r"^\s*[-*]\s+", first) or re.match(r"^\s*\d+[.)]\s+", first):
            continue
        text = strip_md(" ".join(l.lstrip("> ") for l in lines))
        if len(text) < 15:
            continue  # 译稿说明、经文出处等短行不作描述
        texts.append(text)
        if sum(len(t) for t in texts) >= 60:
            break
    if not texts:
        return ""
    desc = " ".join(texts)
    if len(desc) > limit:
        desc = desc[:limit].rstrip("，、；：,. ") + "…"
    return desc


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md_to_html(md):
    out = []
    para = []
    list_buf = []
    list_tag = None

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(x.strip() for x in para)) + "</p>")
            para.clear()

    def flush_list():
        nonlocal list_tag
        if list_buf:
            items = "".join("<li>" + inline(x) + "</li>" for x in list_buf)
            out.append("<{0}>{1}</{0}>".format(list_tag, items))
            list_buf.clear()
            list_tag = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if re.match(r"^\s*(-{3,}|\*{3,})\s*$", line):
            flush_para(); flush_list(); out.append("<hr>"); continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush_para(); flush_list()
            lvl = len(m.group(1)) + 1  # 页面 H1 是标题，正文从 H2 起
            out.append("<h{0}>{1}</h{0}>".format(min(lvl, 4), inline(m.group(2))))
            continue
        if line.strip().startswith(">"):
            flush_para(); flush_list()
            out.append("<blockquote>" + inline(line.strip().lstrip(">").strip()) + "</blockquote>")
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line.strip())
        if m:
            flush_para(); flush_list()
            out.append("<p><img src=\"" + html.escape(m.group(2), quote=True) + "\" alt=\"" + html.escape(m.group(1), quote=True) + "\" style=\"max-width:100%;border-radius:10px\"></p>")
            continue
        m = re.match(r"^\s*[-*]\s+(.*)$", line)
        if m:
            flush_para()
            if list_tag not in (None, "ul"):
                flush_list()
            list_tag = "ul"; list_buf.append(m.group(1)); continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m:
            flush_para()
            if list_tag not in (None, "ol"):
                flush_list()
            list_tag = "ol"; list_buf.append(m.group(1)); continue
        if not line.strip():
            flush_para(); flush_list(); continue
        flush_list()
        para.append(line)
    flush_para(); flush_list()
    return "\n".join(out)


def render_page(meta, body_html, body_md=""):
    title = html.escape(meta["title"])
    desc = meta.get("description") or extract_description(body_md)
    desc_line = ""
    if desc:
        desc_line = ("<meta name=\"description\" content=\""
                     + html.escape(desc, quote=True) + "\">\n")
    meta_bits = []
    if meta.get("date"):
        meta_bits.append(html.escape(meta["date"]))
    if meta.get("author"):
        meta_bits.append("作者：" + html.escape(meta["author"]))
    if meta.get("scripture"):
        meta_bits.append("经文：" + html.escape(meta["scripture"]))
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        + desc_line
        + "<title>" + title + " · Ezra 内容中央枢纽</title>\n<style>" + PAGE_CSS + "</style>\n</head>\n<body>\n"
        "<div class=\"wrap\">\n<a class=\"back\" href=\"../../index.html\">← 返回内容中央枢纽</a>\n"
        "<h1>" + title + "</h1>\n"
        "<div class=\"meta\">" + " · ".join(meta_bits) + "</div>\n"
        "<article>\n" + body_html + "\n</article>\n"
        "<footer>© 2026 Guangyi Zhao 文稿版权所有 · Ezra 内容中央枢纽</footer>\n"
        "</div>\n</body>\n</html>\n"
    )


def main():
    if not ARTICLES_DIR.is_dir():
        print("articles/ 不存在，无事可做")
        return 0
    series_list = []
    for series_dir in sorted(p for p in ARTICLES_DIR.iterdir() if p.is_dir()):
        sid = series_dir.name
        meta_s = SERIES_META.get(sid, {"name": sid, "desc": "", "category": ""})
        items = []
        for md_file in sorted(series_dir.glob("*.md")):
            if md_file.name.lower() == "readme.md":
                continue
            meta, body = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            if not meta.get("title"):
                meta["title"] = extract_title(body)
            if not meta.get("title"):
                print("错误：{0} 无标题（frontmatter 无 title、正文也提取不到），"
                      "构建停住，先补标题再重跑".format(md_file), file=sys.stderr)
                return 1
            slug = md_file.stem
            rel_md = "articles/{0}/{1}.md".format(sid, slug)
            rel_html = "articles/{0}/{1}.html".format(sid, slug)
            out_path = DOCS_ARTICLES / sid / (slug + ".html")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(render_page(meta, md_to_html(body), body), encoding="utf-8")
            items.append({
                "date": meta.get("date", ""),
                "title": meta["title"],
                "scripture": meta.get("scripture", ""),
                "author": meta.get("author", "Guangyi Zhao"),
                "path": rel_md,
                "page": rel_html,
            })
            print("渲染 {0} -> docs/{1}".format(rel_md, rel_html))
        items.sort(key=lambda x: x["date"], reverse=True)
        series_list.append({
            "id": sid,
            "name": meta_s["name"],
            "desc": meta_s["desc"],
            "category": meta_s["category"],
            "count": len(items),
            "items": items,
        })
    for idx_path in (ROOT / "index.json", DOCS_DIR / "index.json"):
        data = json.loads(idx_path.read_text(encoding="utf-8"))
        data["articles"] = series_list
        idx_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print("已更新索引 {0}（系列 {1} 个）".format(idx_path.relative_to(ROOT), len(series_list)))
    # 构建末尾自动重建 sitemap（SEO 修复 2026-11-14：不再手工维护）
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_sitemap.py")],
                       capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        print("警告：sitemap 生成失败，构建结果不完整", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
