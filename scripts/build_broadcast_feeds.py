#!/usr/bin/env python3
"""Build self-hosted podcast RSS feeds for the daily broadcast shows.

Mirrors build_devotion_feed.py: episodes are read from hub content dirs
(content/<series>/<date[-pm]>/index.md + audio.mp3), enclosures point at
the raw.githubusercontent.com URLs of the committed audio files.
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

# feed file -> (title, description, itunes category, [(series, hour), ...])
FEEDS = {
    "fred.xml": (
        "美国百指日报",
        "每天用 100 个美国关键经济指标（FRED）看异常、比变化，深耕 AI 与生物科技。早晚双版。主讲 Guangyi Zhao。",
        "Business",
        [("fred-am", 7), ("fred-pm", 21)],
    ),
    "silicon-valley.xml": (
        "硅谷科技日报",
        "硅谷与全球科技动态速报：AI、科技公司与产业进展。主讲 Guangyi Zhao。",
        "Technology",
        [("silicon-valley", 18)],
    ),
    "longevity.xml": (
        "长寿前沿日报",
        "每天替你读长寿与健康领域的前沿论文与研究。主讲 Guangyi Zhao。",
        "Health &amp; Fitness",
        [("longevity", 18)],
    ),
    "immigration.xml": (
        "移民政策速报",
        "美国移民政策与法规变化速报与解读。主讲 Guangyi Zhao。",
        "News",
        [("immigration", 18)],
    ),
    "bay-area-benefits.xml": (
        "湾区福利速报",
        "湾区福利、补助与生活资讯速报。主讲 Guangyi Zhao。",
        "News",
        [("bay-area-benefits", 18)],
    ),
    "stocks-pm.xml": (
        "美股盘后小结",
        "每个交易日的美股盘后小结：三大指数、板块轮动与个股要点。主讲 Guangyi Zhao。",
        "Business",
        [("stocks-pm", 22)],
    ),
}


def parse_episode(series, dir_name, hour):
    d = os.path.join(ROOT, "content", series, dir_name)
    md_path = os.path.join(d, "index.md")
    au_path = os.path.join(d, "audio.mp3")
    if not (os.path.exists(md_path) and os.path.exists(au_path)):
        return None
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else dir_name
    theme = re.search(r"##\s*一句话主题\s*\n+(.+)", text)
    dur = re.search(r"时长：([0-9:]+)", text)
    date = dir_name[:10]
    if dir_name.endswith("-pm"):
        hour = 21
    pub = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, tzinfo=PDT)
    return {
        "title": title,
        "desc": theme.group(1).strip() if theme else title,
        "pub": pub,
        "url": RAW + "/content/" + series + "/" + dir_name + "/audio.mp3",
        "size": os.path.getsize(au_path),
        "guid": series + "-" + dir_name,
        "duration": dur.group(1) if dur else "",
    }


def build(fname, title, desc, category, series_list):
    eps = []
    for series, hour in series_list:
        base = os.path.join(ROOT, "content", series)
        if not os.path.isdir(base):
            continue
        for dir_name in sorted(os.listdir(base)):
            ep = parse_episode(series, dir_name, hour)
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
        "    <title>" + html.escape(title) + "</title>\n"
        "    <link>" + PAGES + "/</link>\n"
        "    <atom:link href=\"" + PAGES + "/podcast/" + fname
        + "\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        "    <language>zh-cn</language>\n"
        "    <description>" + html.escape(desc) + "</description>\n"
        "    <copyright>© 2026 Guangyi Zhao</copyright>\n"
        "    <lastBuildDate>" + now + "</lastBuildDate>\n"
        "    <itunes:author>Guangyi Zhao</itunes:author>\n"
        "    <itunes:summary>" + html.escape(desc) + "</itunes:summary>\n"
        "    <itunes:owner>\n"
        "      <itunes:name>Guangyi Zhao</itunes:name>\n"
        "      <itunes:email>ezra777.zhao@gmail.com</itunes:email>\n"
        "    </itunes:owner>\n"
        "    <itunes:category text=\"" + category + "\"/>\n"
        "    <itunes:explicit>false</itunes:explicit>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
    out_dir = os.path.join(ROOT, "docs", "podcast")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, fname)
    with open(out, "w", encoding="utf-8") as f:
        f.write(feed)
    print("wrote " + out + " with " + str(len(eps)) + " episodes")
    return len(eps)


if __name__ == "__main__":
    total = 0
    for fname, (title, desc, cat, series) in FEEDS.items():
        total += build(fname, title, desc, cat, series)
    print("TOTAL feed episodes:", total)
