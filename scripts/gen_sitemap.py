#!/usr/bin/env python3
"""sitemap.xml 生成脚本（ezra-content-hub）

用法：python3 scripts/gen_sitemap.py

扫描 docs/ 下全部可索引页面，生成 docs/sitemap.xml：
- 全部 HTML 页（docs/**/*.html）；
- 播客 RSS 文件（docs/podcast/*.xml）与 docs/novel-rss.xml —— 旧版 sitemap
  已收录、抓取方在用，保留不丢。

取舍（明确排除）：
- docs/upload-probe/ —— 浏览器上传探测工具页，非内容页，不索引；
- 其余非 HTML/XML 文件（index.json、图片等）不是落地页，不入 sitemap。

lastmod：优先取该文件在 git 中的最后提交日期（%cs），git 查不到时
回退到文件 mtime。构建入口 scripts/build_articles.py 在每次构建末尾
自动调用本脚本，sitemap 不再靠手工维护。
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
BASE = "https://ezra-zhao.github.io/ezra-content-hub/"
OUT = DOCS / "sitemap.xml"

EXCLUDE_DIRS = {"upload-probe"}


def git_date(path):
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%cs", "--",
             str(path.relative_to(ROOT))],
            capture_output=True, text=True, timeout=30)
        d = r.stdout.strip()
        return d if d else None
    except Exception:
        return None


def lastmod(path):
    d = git_date(path)
    if d:
        return d
    return datetime.fromtimestamp(
        path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")


def classify(rel):
    """按路径给 changefreq / priority，口径沿旧版 sitemap。"""
    if rel == "index.html":
        return "daily", "1.0"
    if rel == "shidu.html":
        return "monthly", "0.9"
    if rel == "qa.html":
        return "weekly", "0.9"
    if rel in ("privacy-policy.html", "terms-of-service.html"):
        return "monthly", "0.3"
    if rel.startswith("articles/"):
        return "weekly", "0.7"
    if rel.startswith("podcast/") or rel.endswith(".xml"):
        return "daily", "0.8"
    return "weekly", "0.5"


def collect():
    urls = []
    for p in sorted(DOCS.rglob("*.html")):
        rel = p.relative_to(DOCS).as_posix()
        if any(part in EXCLUDE_DIRS for part in Path(rel).parts):
            continue
        loc = BASE if rel == "index.html" else BASE + rel
        urls.append((loc, p, rel))
    for p in sorted((DOCS / "podcast").glob("*.xml")):
        rel = p.relative_to(DOCS).as_posix()
        urls.append((BASE + rel, p, rel))
    novel = DOCS / "novel-rss.xml"
    if novel.is_file():
        urls.append((BASE + "novel-rss.xml", novel, "novel-rss.xml"))
    return urls


def main():
    urls = collect()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    latest = ""
    for loc, path, rel in urls:
        lm = lastmod(path)
        latest = max(latest, lm)
        freq, prio = classify(rel)
        lines += ["  <url>",
                  "    <loc>" + loc + "</loc>",
                  "    <lastmod>" + lm + "</lastmod>",
                  "    <changefreq>" + freq + "</changefreq>",
                  "    <priority>" + prio + "</priority>",
                  "  </url>"]
    lines.append("</urlset>")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("sitemap 已生成：{0} 条 URL，最新 lastmod {1} -> {2}".format(
        len(urls), latest, OUT.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
