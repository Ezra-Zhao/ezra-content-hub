#!/usr/bin/env python3
"""2026-10-27 feed 回填：fred-pm 10-26、longevity-pm 10-26、immigration 10-26。
沿 build_broadcast_hub.py 的登记口径：复制 narration → content/<series>/<dir>/audio.mp3，
写 index.md 页，更新 index.json + docs/index.json 的 episodes/count。
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_broadcast_hub import read_title_theme, duration_sec, fmt_dur, write_page

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser("~/workspace/your_files/新闻节目")

JOBS = [
    # (prog_id, ep_dir, dir_name, date, video_url)
    ("fred-pm", os.path.join(SRC, "episodes-evening", "2026-10-26"),
     "2026-10-26", "2026-10-26", "https://www.youtube.com/watch?v=eyl-XsSzUg0"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening", "2026-10-26"),
     "2026-10-26-pm", "2026-10-26", "https://www.youtube.com/watch?v=vdWjP5XwSm0"),
    ("immigration", os.path.join(SRC, "移民政策速报", "episodes", "2026-10-26"),
     "2026-10-26", "2026-10-26", "https://www.youtube.com/watch?v=tQglAy7dhMc"),
]


def main():
    with open(os.path.join(HUB, "index.json"), encoding="utf-8") as f:
        hub = json.load(f)
    programs = {p["id"]: p for p in hub["programs"]}
    done = []
    for prog_id, ep_dir, dir_name, date, video_url in JOBS:
        narration = os.path.join(ep_dir, "narration.mp3")
        if not os.path.isfile(narration):
            print("MISSING narration:", prog_id, ep_dir)
            continue
        cdir = os.path.join(HUB, "content", prog_id, dir_name)
        os.makedirs(cdir, exist_ok=True)
        audio_dst = os.path.join(cdir, "audio.mp3")
        shutil.copyfile(narration, audio_dst)
        sec = duration_sec(audio_dst)
        dur = fmt_dur(sec)
        title, theme = read_title_theme(ep_dir)
        if title.startswith("本节目"):
            # description.txt 首行是免责声明时改用 script.md 的 H1
            for line in open(os.path.join(ep_dir, "script.md"),
                             encoding="utf-8"):
                if line.strip().startswith("# "):
                    title = line.strip()[2:].strip()
                    break
        write_page(os.path.join(cdir, "index.md"), title, theme, dur,
                   video_url, ep_dir)
        ep = {
            "date": date, "title": title, "scripture": "",
            "theme": theme or title,
            "audio": "content/%s/%s/audio.mp3" % (prog_id, dir_name),
            "page": "content/%s/%s/index.md" % (prog_id, dir_name),
            "duration_sec": sec, "duration": dur,
            "video_url": video_url,
            "links": {"spotify": "", "x": "", "youtube": video_url},
        }
        prog = programs[prog_id]
        prog["episodes"] = [e for e in prog["episodes"]
                            if not (e["date"] == date and e["title"] == title)]
        prog["episodes"].append(ep)
        done.append(prog_id + "/" + dir_name)
    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-10-27"
    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)
    print("registered:", done)
    for pid in ("fred-pm", "longevity", "immigration"):
        print(pid, "count=", programs[pid]["count"],
              "latest=", programs[pid]["episodes"][0]["date"])


if __name__ == "__main__":
    main()
