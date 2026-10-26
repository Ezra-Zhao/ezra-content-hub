#!/usr/bin/env python3
"""Build the 每日灵修 podcast RSS feed from hub content dirs."""
import os, re, html
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/Ezra-Zhao/ezra-content-hub/main"
PAGES = "https://ezra-zhao.github.io/ezra-content-hub"
PDT = timezone(timedelta(hours=-7))

def parse_episode(series, date, hour):
    d = os.path.join(ROOT, "content", series, date)
    md_path = os.path.join(d, "index.md")
    au_path = os.path.join(d, "audio.mp3")
    if not (os.path.exists(md_path) and os.path.exists(au_path)):
        return None
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else date
    prog = "AM" if series.endswith("-am") else "PM"
    scr = re.search(r"经文：(.+)", text)
    theme = re.search(r"##\s*一句话主题\s*\n+(.+)", text)
    dur = re.search(r"时长：([0-9:]+)", text)
    desc_parts = []
    if theme:
        desc_parts.append(theme.group(1).strip())
    if scr:
        desc_parts.append("经文：" + scr.group(1).strip())
    desc = " ".join(desc_parts) or title
    pub = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, tzinfo=PDT)
    url = RAW + "/content/" + series + "/" + date + "/audio.mp3"
    # B2 (2026-10-26 Ezra approved): scene suffix on episode titles,
    # new episodes only (date >= 2026-10-31); back catalogue unchanged.
    suffix = ""
    if date >= "2026-10-31":
        suffix = "｜晨起读经" if prog == "AM" else "｜睡前灵修"
        if title.endswith(suffix):
            suffix = ""
    return {
        "title": "[" + prog + "] " + title + suffix,
        "desc": desc,
        "pub": pub,
        "url": url,
        "size": os.path.getsize(au_path),
        "guid": series + "-" + date,
        "duration": dur.group(1) if dur else "",
    }

eps = []
for series, hour in (("devotion-am", 7), ("devotion-pm", 21)):
    base = os.path.join(ROOT, "content", series)
    if not os.path.isdir(base):
        continue
    for date in sorted(os.listdir(base)):
        ep = parse_episode(series, date, hour)
        if ep:
            eps.append(ep)
eps.sort(key=lambda e: e["pub"], reverse=True)

items = []
for ep in eps:
    dur_xml = ""
    if ep["duration"]:
        dur_xml = "\n      <itunes:duration>" + ep["duration"] + "</itunes:duration>"
    items.append(
        "    <item>\n"
        "      <title>" + html.escape(ep["title"]) + "</title>\n"
        "      <description>" + html.escape(ep["desc"]) + "</description>\n"
        "      <pubDate>" + format_datetime(ep["pub"]) + "</pubDate>\n"
        "      <guid isPermaLink=\"false\">" + ep["guid"] + "</guid>\n"
        "      <enclosure url=\"" + ep["url"] + "\" length=\"" + str(ep["size"]) + "\" type=\"audio/mpeg\"/>" + dur_xml + "\n"
        "    </item>"
    )

now = format_datetime(datetime.now(PDT))
feed = (
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n"
    "  <channel>\n"
    "    <title>每日灵修｜2分钟读经与祷告</title>\n"
    "    <link>" + PAGES + "/</link>\n"
    "    <atom:link href=\"" + PAGES + "/podcast/devotion.xml\" rel=\"self\" type=\"application/rss+xml\"/>\n"
    "    <language>zh-cn</language>\n"
    "    <description>每日灵修：早间起后版与睡前版，围绕当日经文默想与祷告。主讲 Guangyi Zhao。关键词：每日灵修、读经、祷告、圣经、早祷、睡前灵修。全部节目与文字稿：https://ezra-zhao.github.io/ezra-content-hub/ 同组节目：讲道节目《瓦器分享》也在本枢纽更新。</description>\n"
    "    <copyright>© 2026 Guangyi Zhao</copyright>\n"
    "    <lastBuildDate>" + now + "</lastBuildDate>\n"
    "    <itunes:author>Guangyi Zhao</itunes:author>\n"
    "    <itunes:summary>每日灵修：早间起后版与睡前版，围绕当日经文默想与祷告。主讲 Guangyi Zhao。关键词：每日灵修、读经、祷告、圣经、早祷、睡前灵修。全部节目与文字稿：https://ezra-zhao.github.io/ezra-content-hub/ 同组节目：讲道节目《瓦器分享》也在本枢纽更新。</itunes:summary>\n"
    "    <itunes:keywords>每日灵修,读经,祷告,圣经,早祷,睡前灵修,基督教,默想</itunes:keywords>\n"
    "    <itunes:owner>\n"
    "      <itunes:name>Guangyi Zhao</itunes:name>\n"
    "      <itunes:email>ezra777.zhao@gmail.com</itunes:email>\n"
    "    </itunes:owner>\n"
    "    <itunes:image href=\"" + PAGES + "/podcast/cover-devotion.png\"/>\n"
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
out = os.path.join(out_dir, "devotion.xml")
open(out, "w", encoding="utf-8").write(feed)
print("wrote " + out + " with " + str(len(eps)) + " episodes")
