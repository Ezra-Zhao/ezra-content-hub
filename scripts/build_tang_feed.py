#!/usr/bin/env python3
"""Build the 《信仰问题解答》唐崇荣讲道改编播讲 podcast RSS feed from hub content/tang-sermons.

Mirrors build_broadcast_feeds.py / build_devotion_feed.py: episodes are
read from content/sermons/<date>/index.md + audio.mp3, enclosures point
at raw.githubusercontent.com URLs of the committed audio files.

Channel image: docs/podcast/cover-tang.png (dedicated 唐改系列 cover,
3000x3000 PNG, copied from 播客音频线/封面/瓦器分享-cover.png).
"""
import os
import re
import html
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/Ezra-Zhao/ezra-content-hub/main"
PAGES = "https://ezra-zhao.github.io/ezra-content-hub"
PDT = timezone(timedelta(hours=-7))

TITLE = "信仰问题解答｜唐崇荣讲道改编播讲"
DESC = ("信仰问题解答：唐崇荣牧师讲道改编，由赵广义编纂播讲——系统神学、护教与信仰疑难逐问解答。"
        "署名口径：改编自唐崇荣牧师《信仰问题解答》，核心观点归原作者。"
        "文字版：https://github.com/Ezra-Zhao/Sermon-Sharing 全部节目：https://ezra-zhao.github.io/ezra-content-hub/")
KEYWORDS = "信仰问答,系统神学,护教,唐崇荣,讲道,基督教"
FNAME = "tangqa.xml"


def parse_episode(date):
    d = os.path.join(ROOT, "content", "tang-sermons", date)
    md_path = os.path.join(d, "index.md")
    au_path = os.path.join(d, "audio.mp3")
    if not (os.path.exists(md_path) and os.path.exists(au_path)):
        return None
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else date
    theme = re.search(r"##\s*一句话主题\s*\n+(.+)", text)
    scr = re.search(r"经文：(.+)", text)
    dur = re.search(r"时长：([0-9:]+)", text)
    desc_parts = []
    if theme:
        desc_parts.append(theme.group(1).strip())
    if scr:
        desc_parts.append("经文：" + scr.group(1).strip())
    pub = datetime.strptime(date, "%Y-%m-%d").replace(hour=8, tzinfo=PDT)
    return {
        "title": title,
        "desc": " ".join(desc_parts) or title,
        "pub": pub,
        "url": RAW + "/content/tang-sermons/" + date + "/audio.mp3",
        "size": os.path.getsize(au_path),
        "guid": "tangqa-" + date,
        "duration": dur.group(1) if dur else "",
    }


def main():
    base = os.path.join(ROOT, "content", "tang-sermons")
    eps = []
    for date in sorted(os.listdir(base)):
        ep = parse_episode(date)
        if ep:
            eps.append(ep)
    eps.sort(key=lambda e: e["pub"], reverse=True)
    items = []
    for ep in eps:
        dur_xml = ""
        if ep["duration"]:
            dur_xml = ("\n      <itunes:duration>" + ep["duration"]
                       + "</itunes:duration>")
        items.append(
            "    <item>\n"
            "      <title>" + html.escape(ep["title"]) + "</title>\n"
            "      <description>" + html.escape(ep["desc"])
            + "</description>\n"
            "      <pubDate>" + format_datetime(ep["pub"]) + "</pubDate>\n"
            "      <guid isPermaLink=\"false\">" + ep["guid"] + "</guid>\n"
            "      <enclosure url=\"" + ep["url"] + "\" length=\""
            + str(ep["size"]) + "\" type=\"audio/mpeg\"/>" + dur_xml + "\n"
            "    </item>"
        )
    now = format_datetime(datetime.now(PDT))
    feed = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n"
        "  <channel>\n"
        "    <title>" + html.escape(TITLE) + "</title>\n"
        "    <link>" + PAGES + "/</link>\n"
        "    <atom:link href=\"" + PAGES + "/podcast/" + FNAME
        + "\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        "    <language>zh-cn</language>\n"
        "    <description>" + html.escape(DESC) + "</description>\n"
        "    <copyright>© 2026 Guangyi Zhao</copyright>\n"
        "    <lastBuildDate>" + now + "</lastBuildDate>\n"
        "    <itunes:author>Guangyi Zhao</itunes:author>\n"
        "    <itunes:summary>" + html.escape(DESC) + "</itunes:summary>\n"
        "    <itunes:keywords>" + KEYWORDS + "</itunes:keywords>\n"
        "    <itunes:owner>\n"
        "      <itunes:name>Guangyi Zhao</itunes:name>\n"
        "      <itunes:email>ezra777.zhao@gmail.com</itunes:email>\n"
        "    </itunes:owner>\n"
        "    <itunes:image href=\"" + PAGES + "/podcast/cover-tang.png\"/>\n"
        "    <itunes:category text=\"Religion &amp; Spirituality\">\n"
        "      <itunes:category text=\"Christianity\"/>\n"
        "    </itunes:category>\n"
        "    <itunes:category text=\"Society &amp; Culture\"/>\n"
        "    <itunes:explicit>false</itunes:explicit>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
    out_dir = os.path.join(ROOT, "docs", "podcast")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, FNAME)
    with open(out, "w", encoding="utf-8") as f:
        f.write(feed)
    print("wrote " + out + " with " + str(len(eps)) + " episodes")


if __name__ == "__main__":
    main()
