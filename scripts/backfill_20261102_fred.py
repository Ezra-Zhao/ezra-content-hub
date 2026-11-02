#!/usr/bin/env python3
"""2026-11-02 fred 线 feed 回填：时效日检派单补产轮登记。

范围：fred-am 2026-10-30 / 2026-10-31 / 2026-11-01、fred-pm 2026-10-31 /
2026-11-01——均为已在 YouTube 发布（upload.json 有 url、回读 public）
且 narration.mp3 在盘的期。fred-pm 2026-10-31 的 upload.json 为回读补写
格式（无 status 字段），其发布事实已由 pipeline-log 与本轮 API 口径
核实（public/processed、入时效列表 position 46），按已发布登记；
其余各期 status 均为 published。登记口径沿 backfill_20261031.py。
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
    ("fred-am", os.path.join(SRC, "episodes"), "2026-10-30"),
    ("fred-am", os.path.join(SRC, "episodes"), "2026-10-31"),
    ("fred-am", os.path.join(SRC, "episodes"), "2026-11-01"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-10-31"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-11-01"),
]


def script_lead(ep_dir):
    sp = os.path.join(ep_dir, "script.md")
    if not os.path.isfile(sp):
        return ""
    seen_h1 = False
    for line in open(sp, encoding="utf-8"):
        s = line.strip()
        if s.startswith("# "):
            seen_h1 = True
            continue
        if seen_h1 and s and not s.startswith(("#", ">", "---")):
            return s[:120]
    return ""


def main():
    with open(os.path.join(HUB, "index.json"), encoding="utf-8") as f:
        hub = json.load(f)
    programs = {p["id"]: p for p in hub["programs"]}
    done, skipped = [], []
    for prog_id, base, date in JOBS:
        ep_dir = os.path.join(base, date)
        narration = os.path.join(ep_dir, "narration.mp3")
        up_p = os.path.join(ep_dir, "upload.json")
        if not os.path.isfile(narration) or not os.path.isfile(up_p):
            skipped.append(f"{prog_id}/{date} (missing narration or upload.json)")
            continue
        with open(up_p, encoding="utf-8") as f:
            up = json.load(f)
        url = up.get("url") or ""
        status = (up.get("status") or "").strip()
        published = bool(url) and (status.startswith("published")
                                   or up.get("privacyStatus") == "public")
        if not published:
            skipped.append(f"{prog_id}/{date} (not published, status={status})")
            continue
        title, theme = read_title_theme(ep_dir)
        if title.startswith("本节目"):
            for line in open(os.path.join(ep_dir, "script.md"), encoding="utf-8"):
                if line.strip().startswith("# "):
                    title = line.strip()[2:].strip()
                    break
        if theme.replace("：", "").replace(":", "").strip() in ("出处", ""):
            lead = script_lead(ep_dir)
            if lead:
                theme = lead
        cdir = os.path.join(HUB, "content", prog_id, date)
        os.makedirs(cdir, exist_ok=True)
        audio_dst = os.path.join(cdir, "audio.mp3")
        shutil.copyfile(narration, audio_dst)
        sec = duration_sec(audio_dst)
        dur = fmt_dur(sec)
        write_page(os.path.join(cdir, "index.md"), title, theme, dur, url, ep_dir)
        ep = {
            "date": date, "title": title, "scripture": "",
            "theme": theme or title,
            "audio": f"content/{prog_id}/{date}/audio.mp3",
            "page": f"content/{prog_id}/{date}/index.md",
            "duration_sec": sec, "duration": dur,
            "video_url": url,
            "links": {"spotify": "", "x": "", "youtube": url},
        }
        prog = programs[prog_id]
        prog["episodes"] = [e for e in prog["episodes"]
                            if not (e["date"] == date and e["title"] == title)]
        prog["episodes"].append(ep)
        done.append(f"{prog_id}/{date}")
    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-11-02"
    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)
    print("registered:", len(done))
    for d in done:
        print("  +", d)
    print("skipped:", skipped)
    for pid in ("fred-am", "fred-pm"):
        print(pid, "count=", programs[pid]["count"],
              "latest=", programs[pid]["episodes"][0]["date"])


if __name__ == "__main__":
    main()
