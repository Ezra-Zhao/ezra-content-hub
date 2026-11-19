#!/usr/bin/env python3
"""播客逐字稿落地页生成器（2026-11-19 建，AI 收录体检·任务二）。

为每个 feed 中「已有逐字稿」的集生成一个静态落地页（HTML），内容：
集标题、日期、一句话要点、音频播放器/链接、逐字稿全文、回链 feed 与索引。
落地页同时生成每 feed 的索引页与总索引页，供搜索引擎与 AI 爬虫抓取全文。

用法：
  python3 scripts/build_transcript_pages.py --feed waqi            # 瓦器全量
  python3 scripts/build_transcript_pages.py --feed devotion --limit 10
  python3 scripts/build_transcript_pages.py --feed all --dry-run   # 只盘点覆盖

逐字稿来源（只用现成稿件，缺稿的集跳过并在盘点里标缺，绝不编造）：
  - 瓦器 EP1/EP2：播客音频线/瓦器验证/EP{n}-转写稿.md（ASR 转写定版稿）
  - 瓦器 EP3+：各 瓦器EP{n}/tts.txt（口播全文，即 TTS 定版文本）；
    集号↔日期由各集 fetch_and_publish_waqi.py 内的 DATE 常量映射
  - 瓦器内的讲道有声化集：讲道有声化/<日期>-<题>/tts.txt
  - 灵修中文：每日灵修/tts-YYYYMMDD/正稿[-睡前]-YYYY-MM-DD.txt；
    缺时回退到 每日灵修/正稿[-睡前]-YYYY-MM-DD.md 的正文段（说明节之后）
  - 灵修 EN/ES：tts-YYYYMMDD/正稿-{EN|ES}[-睡前]-YYYY-MM-DD.txt
  - 灵修 HI：播客音频线/每日灵修[-睡前]-HI-EP<YYYYMMDD>.mp3.tts.txt（部分集）
新集按同一命名规律放稿后，重跑本脚本即可增量生成（已存在的页面会重建）。
"""
import argparse
import glob
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://ezra-zhao.github.io/ezra-content-hub"
WS = os.path.expanduser("~/workspace/your_files")
PODCAST_LINE = os.path.join(WS, "播客音频线")
DEVOTION_SRC = os.path.join(WS, "新闻节目", "每日灵修")
OUT_ROOT = os.path.join(HUB, "docs", "podcast", "episodes")

FEEDS = {
    "waqi": {"file": "waqi.xml", "name": "瓦器分享｜圣经讲解与讲道"},
    "devotion": {"file": "devotion.xml", "name": "每日灵修｜2分钟读经与祷告"},
    "devotion-en": {"file": "devotion-en.xml", "name": "Daily Devotion (English)"},
    "devotion-es": {"file": "devotion-es.xml", "name": "Devoción Diaria (Español)"},
    "devotion-vi": {"file": "devotion-vi.xml", "name": "Linh Thao Hằng Ngày (Tiếng Việt)"},
    "devotion-hi": {"file": "devotion-hi.xml", "name": "दैनिक भक्ति (हिन्दी)"},
    "audiobook": {"file": "audiobook.xml", "name": "有声伴读"},
    "tangqa": {"file": "tangqa.xml", "name": "信仰问题解答（唐崇荣问答改编）"},
}

CSS = """
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:760px;margin:0 auto;padding:20px 16px 48px;line-height:1.75;color:#222}
h1{font-size:1.45rem;line-height:1.4}
.meta{color:#666;font-size:.92rem}
.theme{background:#f6f3ec;border-left:4px solid #b98a2f;padding:10px 14px;margin:16px 0}
audio{width:100%;margin:12px 0}
.transcript p{margin:.7em 0}
footer{margin-top:36px;border-top:1px solid #ddd;padding-top:12px;font-size:.9rem;color:#555}
a{color:#8a5a00}
li{margin:.35em 0}
"""


def esc(s):
    return html.escape(s or "", quote=True)


def feed_items(feed_key):
    path = os.path.join(HUB, "docs", "podcast", FEEDS[feed_key]["file"])
    root = ET.parse(path).getroot()
    ch = root.find("channel")
    items = []
    for it in ch.findall("item"):
        enc = it.find("enclosure")
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate"))
            date = dt.strftime("%Y-%m-%d")
        except Exception:
            date = ""
        items.append({
            "title": (it.findtext("title") or "").strip(),
            "date": date,
            "guid": (it.findtext("guid") or "").strip(),
            "audio": enc.get("url") if enc is not None else "",
            "desc": (it.findtext("description") or "").strip(),
        })
    return items


def content_theme(series, date):
    """从枢纽 content/<series>/<date>/index.md 取一句话主题。"""
    p = os.path.join(HUB, "content", series, date, "index.md")
    if not os.path.exists(p):
        return ""
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"##\s*一句话主题\s*\n+(.+)", txt)
    if m:
        return m.group(1).strip()
    m = re.search(r"##\s*一句话要点\s*\n+(.+)", txt)
    return m.group(1).strip() if m else ""


def strip_md_header_transcript(path):
    """瓦器转写稿：取第一个 --- 之后的正文。"""
    txt = open(path, encoding="utf-8").read()
    parts = txt.split("\n---", 1)
    body = parts[1] if len(parts) > 1 else txt
    return body.strip()


def waqi_ep_map():
    """扫 瓦器EP{n}/fetch_and_publish_waqi.py 的 DATE 常量 → {date: ep_dir}。"""
    out = {}
    for d in glob.glob(os.path.join(PODCAST_LINE, "瓦器EP*")):
        for py in glob.glob(os.path.join(d, "fetch_and_publish_waqi.py")):
            m = re.search(r'DATE\s*=\s*"(\d{4}-\d{2}-\d{2})"',
                          open(py, encoding="utf-8").read())
            if m:
                out[m.group(1)] = d
    return out


WAQI_SPECIAL = {
    # 讲道有声化第一批（非瓦器 EP 序，同 feed 发布）
    "2026-10-08": os.path.join(PODCAST_LINE, "讲道有声化",
                               "2026-10-08-起初神创造天地", "tts.txt"),
    # EP1/EP2 早于 瓦器EP{n} 目录体例，逐字稿在 瓦器验证/
    "2026-10-15": os.path.join(PODCAST_LINE, "瓦器验证", "EP1-转写稿.md"),
    "2026-10-09": os.path.join(PODCAST_LINE, "瓦器验证", "EP2-转写稿.md"),
}


def resolve_waqi(item, ep_map):
    date = item["date"]
    if date in WAQI_SPECIAL and os.path.exists(WAQI_SPECIAL[date]):
        p = WAQI_SPECIAL[date]
        return p, "转写稿（ASR 定版）" if p.endswith("转写稿.md") else "口播全文（tts 定版）"
    d = ep_map.get(date)
    if d:
        n = re.search(r"EP(\d+)", os.path.basename(d)).group(1)
        tr = os.path.join(PODCAST_LINE, "瓦器验证", f"EP{n}-转写稿.md")
        if os.path.exists(tr):
            return tr, "转写稿（ASR 定版）"
        tts = os.path.join(d, "tts.txt")
        if os.path.exists(tts):
            return tts, "口播全文（tts 定版）"
    return None, ""


def devotion_txt(date, pm, lang=None):
    ymd = date.replace("-", "")
    if lang in (None, "zh"):
        name = f"正稿-{'睡前-' if pm else ''}{date}.txt"
    else:
        name = f"正稿-{lang}-{'睡前-' if pm else ''}{date}.txt"  # 实名如 正稿-EN-睡前-2026-11-19.txt
    p = os.path.join(DEVOTION_SRC, f"tts-{ymd}", name)
    return p if os.path.exists(p) else None


def devotion_md_body(date, pm):
    p = os.path.join(DEVOTION_SRC, f"正稿-{'睡前-' if pm else ''}{date}.md")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8").read()
    # 正文在 ## 说明 之后的 --- 分隔线后
    m = re.split(r"\n---\s*\n", txt, maxsplit=1)
    body = m[1] if len(m) > 1 else txt
    body = re.sub(r"©.*$", "", body, flags=re.S).strip()
    tmp = os.path.join("/tmp", f"devotion-body-{date}-{'pm' if pm else 'am'}.txt")
    open(tmp, "w", encoding="utf-8").write(body)
    return tmp


def resolve_devotion(item, lang=None):
    # 中文 feed guid: devotion-am-YYYY-MM-DD；外语 feed: devotion-am-en-YYYY-MM-DD
    m = re.match(r"devotion-(am|pm)-(?:[a-z]{2}-)?(\d{4}-\d{2}-\d{2})", item["guid"])
    if not m:
        return None, ""
    pm = m.group(1) == "pm"
    date = m.group(2)
    if lang in ("VI",):
        return None, ""  # VI 稿散存，未成册，标缺待整
    if lang == "HI":
        ymd = date.replace("-", "")
        p = os.path.join(PODCAST_LINE,
                         f"每日灵修-{'睡前-' if pm else ''}HI-EP{ymd}.mp3.tts.txt")
        return (p, "口播稿（tts 旁存）") if os.path.exists(p) else (None, "")
    p = devotion_txt(date, pm, lang)
    if p:
        return p, "口播全文（tts 定版）"
    if lang in (None, "zh"):
        p2 = devotion_md_body(date, pm)
        if p2:
            return p2, "正稿正文（定版稿）"
    return None, ""


RESOLVERS = {
    "waqi": lambda it: resolve_waqi(it, waqi_ep_map()),
    "devotion": lambda it: resolve_devotion(it),
    "devotion-en": lambda it: resolve_devotion(it, "EN"),
    "devotion-es": lambda it: resolve_devotion(it, "ES"),
    "devotion-vi": lambda it: resolve_devotion(it, "VI"),
    "devotion-hi": lambda it: resolve_devotion(it, "HI"),
    "audiobook": lambda it: (None, ""),   # 底本为伴读全稿，逐字稿落地页另案
    "tangqa": lambda it: (None, ""),      # 稿在唐改EPn 目录，未纳入本轮解析
}


def paragraphs(text):
    text = text.replace("\r\n", "\n")
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras


def render_page(feed_key, item, theme, transcript_text, src_kind):
    feed_name = FEEDS[feed_key]["name"]
    feed_url = f"{SITE}/podcast/{FEEDS[feed_key]['file']}"
    paras = "\n".join(f"      <p>{esc(p)}</p>" for p in paragraphs(transcript_text))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(item['title'])}｜{esc(feed_name)}</title>
<meta name="description" content="{esc(theme or item['title'])}">
<style>{CSS}</style>
</head>
<body>
<header>
  <p class="meta"><a href="../index.html">{esc(feed_name)}</a> · {esc(item['date'])}</p>
  <h1>{esc(item['title'])}</h1>
</header>
<div class="theme"><strong>一句话要点：</strong>{esc(theme or item['desc'][:120])}</div>
<audio controls preload="none" src="{esc(item['audio'])}"></audio>
<p class="meta">音频：<a href="{esc(item['audio'])}">直接收听 / 下载</a> · 订阅：<a href="{esc(feed_url)}">RSS feed</a></p>
<section class="transcript">
  <h2>逐字稿全文</h2>
{paras}
</section>
<footer>
  <p>逐字稿来源：{esc(src_kind)}，与音频经转写验证核对。© 2026 Guangyi Zhao 版权所有。</p>
  <p><a href="index.html">← 本节目全部落地页</a> · <a href="../index.html">播客落地页总索引</a> · <a href="{SITE}/">Ezra 内容枢纽</a></p>
</footer>
</body>
</html>
"""


def render_index(feed_key, rows):
    feed_name = FEEDS[feed_key]["name"]
    feed_url = f"{SITE}/podcast/{FEEDS[feed_key]['file']}"
    lis = "\n".join(
        f'    <li>{esc(r["date"])} · <a href="{esc(r["guid"])}.html">{esc(r["title"])}</a></li>'
        for r in rows)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(feed_name)}｜逐字稿落地页索引</title>
<style>{CSS}</style>
</head>
<body>
<h1>{esc(feed_name)}</h1>
<p class="meta">每集一页：音频＋逐字稿全文。订阅：<a href="{esc(feed_url)}">RSS feed</a> · <a href="../index.html">播客落地页总索引</a> · <a href="{SITE}/">Ezra 内容枢纽</a></p>
<ul>
{lis}
</ul>
</body>
</html>
"""


def render_top_index(feed_rows):
    lis = "\n".join(
        f'    <li><a href="{k}/index.html">{esc(FEEDS[k]["name"])}</a>（已建落地页 {n} 集）</li>'
        for k, n in feed_rows)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>播客逐字稿落地页｜Ezra 内容枢纽</title>
<style>{CSS}</style>
</head>
<body>
<h1>播客逐字稿落地页</h1>
<p class="meta">每集一页：标题、日期、一句话要点、音频与逐字稿全文，方便阅读、检索与引用。</p>
<ul>
{lis}
</ul>
<footer><p><a href="{SITE}/">← Ezra 内容枢纽首页</a></p></footer>
</body>
</html>
"""


def build(feed_key, limit=None, dry_run=False):
    items = feed_items(feed_key)
    resolver = RESOLVERS[feed_key]
    series = {"waqi": "sermons"}.get(feed_key, "")
    done, missing = [], []
    for it in items:
        path, kind = resolver(it)
        if not path:
            missing.append(it)
            continue
        if limit and len(done) >= limit:
            continue
        raw = open(path, encoding="utf-8").read()
        if path.endswith("转写稿.md"):
            raw = strip_md_header_transcript(path)
        theme = ""
        if series:
            theme = content_theme(series, it["date"])
        elif feed_key.startswith("devotion"):
            m = re.match(r"(devotion-(?:am|pm))-", it["guid"])
            if m:
                theme = content_theme(m.group(1), it["date"])
        if not dry_run:
            out_dir = os.path.join(OUT_ROOT, feed_key)
            os.makedirs(out_dir, exist_ok=True)
            page = render_page(feed_key, it, theme, raw, kind)
            open(os.path.join(out_dir, f"{it['guid']}.html"), "w",
                 encoding="utf-8").write(page)
        done.append({**it, "src": path, "kind": kind})
    if not dry_run and done:
        out_dir = os.path.join(OUT_ROOT, feed_key)
        rows = sorted(done, key=lambda r: r["date"], reverse=True)
        open(os.path.join(out_dir, "index.html"), "w",
             encoding="utf-8").write(render_index(feed_key, rows))
    return items, done, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default="all")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    keys = list(FEEDS) if args.feed == "all" else [args.feed]
    feed_rows = []
    for k in keys:
        items, done, missing = build(k, args.limit, args.dry_run)
        feed_rows.append((k, len(done)))
        print(f"[{k}] feed 共 {len(items)} 集｜有逐字稿 {len(done)}｜缺 {len(missing)}")
        for m in missing:
            print(f"    缺稿：{m['date']} {m['title'][:50]}")
    if not args.dry_run:
        # 总索引扫盘上全部已有 feed 索引页（不只当轮运行的 feed，防覆盖丢档）
        existing = []
        for k in FEEDS:
            idx = os.path.join(OUT_ROOT, k, "index.html")
            if os.path.exists(idx):
                import subprocess
                cnt = subprocess.run(["grep", "-c", "<li>", idx],
                                     capture_output=True, text=True).stdout.strip()
                existing.append((k, cnt))
        os.makedirs(OUT_ROOT, exist_ok=True)
        open(os.path.join(OUT_ROOT, "index.html"), "w",
             encoding="utf-8").write(render_top_index(existing))


if __name__ == "__main__":
    main()
