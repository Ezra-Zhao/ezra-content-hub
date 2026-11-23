#!/usr/bin/env python3
"""Rebuild devotion-en.xml / devotion-es.xml from content dirs.

2026-10-27 疏通轮新增：此前 en/es feed 无仓内构建脚本（靠外部流程手维），
A6 英/西断档三天与此有关。本脚本沿用既有 feed 的频道头（原样保留、仅
更新 lastBuildDate），按 content/devotion-{am,pm}-{en,es} 目录重建 items。

Item 规则（与既有 feed 一致）：
- title: [AM]/[PM] + 页面 H1（中午档 [NOON]，2026-11-23 英/西新增，照中文版）
- description: 一句话主题 + " Scripture: "/" Escritura: " + 页面经文字段
- pubDate: AM 07:00 / NOON 12:00 / PM 21:00 (PDT, -0700)
- guid: <series>-<date>; enclosure: raw URL + 文件字节数; duration: 页面时长
"""
import html
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = HUB
PAGES = "https://ezrazhao.com"
RAW = "https://raw.githubusercontent.com/Ezra-Zhao/ezra-content-hub/main"
PDT = timezone(timedelta(hours=-7))

FEEDS = {
    "devotion-en.xml": ((("devotion-am-en", 7), ("devotion-noon-en", 12), ("devotion-pm-en", 21)), " Scripture: "),
    "devotion-es.xml": ((("devotion-am-es", 7), ("devotion-noon-es", 12), ("devotion-pm-es", 21)), " Escritura: "),
    "devotion-vi.xml": ((("devotion-am-vi", 7), ("devotion-pm-vi", 21)), " Kinh Thánh: "),
    "devotion-hi.xml": ((("devotion-am-hi", 7), ("devotion-pm-hi", 21)), " पवित्रशास्त्र: "),
}


def parse_episode(series, date, hour):
    d = os.path.join(ROOT, "content", series, date)
    md_path = os.path.join(d, "index.md")
    au_path = os.path.join(d, "audio.mp3")
    if not (os.path.exists(md_path) and os.path.exists(au_path)):
        return None
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else date
    theme = re.search(r"##\s*一句话主题\s*\n+(.+)", text)
    verse = re.search(r"经文：(.+)", text)
    dur = re.search(r"时长：([0-9:]+)", text)
    pub = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, tzinfo=PDT)
    return {
        "title": {7: "[AM] ", 12: "[NOON] ", 21: "[PM] "}[hour] + title,
        "theme": theme.group(1).strip() if theme else title,
        "verse": verse.group(1).strip() if verse else "",
        "pub": pub,
        "url": RAW + "/content/" + series + "/" + date + "/audio.mp3",
        "size": os.path.getsize(au_path),
        "guid": series + "-" + date,
        "duration": dur.group(1) if dur else "",
    }


def main():
    for fname, (series_list, scripture_word) in FEEDS.items():
        out = os.path.join(ROOT, "docs", "podcast", fname)
        old = open(out, encoding="utf-8").read()
        head = old.split("    <item>")[0]
        head = re.sub(
            r"<lastBuildDate>.*?</lastBuildDate>",
            "<lastBuildDate>" + format_datetime(datetime.now(PDT)) + "</lastBuildDate>",
            head,
        )
        eps = []
        for series, hour in series_list:
            base = os.path.join(ROOT, "content", series)
            if not os.path.isdir(base):
                continue
            for date in sorted(os.listdir(base)):
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                    continue
                ep = parse_episode(series, date, hour)
                if ep:
                    eps.append(ep)
        eps.sort(key=lambda e: e["pub"], reverse=True)
        items = []
        for ep in eps:
            desc = ep["theme"]
            if ep["verse"]:
                desc += scripture_word + ep["verse"]
            dur_xml = ""
            if ep["duration"]:
                dur_xml = "\n      <itunes:duration>" + ep["duration"] + "</itunes:duration>"
            items.append(
                "    <item>\n"
                "      <title>" + html.escape(ep["title"]) + "</title>\n"
                "      <description>" + html.escape(desc) + "</description>\n"
                "      <pubDate>" + format_datetime(ep["pub"]) + "</pubDate>\n"
                "      <guid isPermaLink=\"false\">" + ep["guid"] + "</guid>\n"
                "      <enclosure url=\"" + ep["url"] + "\" length=\"" + str(ep["size"]) + "\" type=\"audio/mpeg\"/>" + dur_xml + "\n"
                "    </item>"
            )
        feed = head + "\n".join(items) + "\n  </channel>\n</rss>\n"
        open(out, "w", encoding="utf-8").write(feed)
        print("wrote " + out + " with " + str(len(eps)) + " episodes")


if __name__ == "__main__":
    main()
