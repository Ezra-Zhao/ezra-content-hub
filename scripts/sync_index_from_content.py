#!/usr/bin/env python3
"""把 index.json 的广播节目 episodes 与 content/ 目录实际存量对齐。

背景：历次 feed 补传只登记了 content 目录与 RSS，网站索引（index.json）
长期滞后（如 fred-am 索引 2 集 vs content 10 集）。本脚本按各集 index.md
页（标题/主题/时长/视频）重建下列节目的 episodes 列表，devotion/sermons
等有专属管线的节目不动。
"""
import json
import os
import re

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAMS = ["fred-am", "fred-pm", "silicon-valley", "longevity",
            "immigration", "bay-area-benefits", "stocks-pm"]


def parse_page(series, dir_name):
    d = os.path.join(HUB, "content", series, dir_name)
    md = os.path.join(d, "index.md")
    au = os.path.join(d, "audio.mp3")
    if not (os.path.isfile(md) and os.path.isfile(au)):
        return None
    text = open(md, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else dir_name
    theme = re.search(r"##\s*一句话主题\s*\n+(.+)", text)
    dur = re.search(r"时长：([0-9]+):([0-9]{2})", text)
    vid = re.search(r"视频：(\S+)", text)
    video_url = vid.group(1) if vid and vid.group(1).startswith("http") else ""
    sec = int(dur.group(1)) * 60 + int(dur.group(2)) if dur else 0
    return {
        "date": dir_name[:10],
        "title": title,
        "scripture": "",
        "theme": theme.group(1).strip() if theme else title,
        "audio": "content/%s/%s/audio.mp3" % (series, dir_name),
        "page": "content/%s/%s/index.md" % (series, dir_name),
        "duration_sec": sec,
        "duration": ("%d:%02d" % (sec // 60, sec % 60)) if sec else "",
        "video_url": video_url,
        "links": {"spotify": "", "x": "", "youtube": video_url},
    }


def main():
    with open(os.path.join(HUB, "index.json"), encoding="utf-8") as f:
        hub = json.load(f)
    programs = {p["id"]: p for p in hub["programs"]}
    for pid in PROGRAMS:
        base = os.path.join(HUB, "content", pid)
        if not os.path.isdir(base):
            continue
        eps = []
        for dir_name in sorted(os.listdir(base)):
            ep = parse_page(pid, dir_name)
            if ep:
                eps.append(ep)
        eps.sort(key=lambda e: e["date"], reverse=True)
        old = programs[pid]["count"]
        programs[pid]["episodes"] = eps
        programs[pid]["count"] = len(eps)
        print(pid, "index count", old, "->", len(eps))
    hub["updated"] = "2026-10-27"
    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
