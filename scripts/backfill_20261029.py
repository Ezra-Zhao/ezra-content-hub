#!/usr/bin/env python3
"""2026-10-29 feed 回填：2026-10-26/27/28 积压期数登记入枢纽。

沿 build_broadcast_hub.py / backfill_20261027.py 的登记口径：复制
narration → content/<series>/<dir>/audio.mp3，write_page 写 index.md，
更新 index.json + docs/index.json 的 episodes/count。视频链接取各期
upload.json 的 url 字段；stocks-pm 取 goal-5 market-video 的
upload-progress.json，音频用其 work/<date>/podcast-audio.mp3（与既往
登记的 content/stocks-pm/*/audio.mp3 同源同尺寸口径）。
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_broadcast_hub import read_title_theme, duration_sec, fmt_dur, write_page

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser("~/workspace/your_files/新闻节目")
MV = os.path.expanduser("~/workspace/goals/goal-5/hidden_files/market-video")

# (prog_id, source_base, date, slot)  slot pm 仅对单节目双版线影响 dir 名
JOBS = [
    ("fred-am", os.path.join(SRC, "episodes"), "2026-10-27", "am"),
    ("fred-am", os.path.join(SRC, "episodes"), "2026-10-28", "am"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-10-27", "pm"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-10-28", "pm"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes"),
     "2026-10-27", "am"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes-evening"),
     "2026-10-27", "pm"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes"),
     "2026-10-28", "am"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes-evening"),
     "2026-10-28", "pm"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes"),
     "2026-10-27", "am"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening"),
     "2026-10-27", "pm"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes"),
     "2026-10-28", "am"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening"),
     "2026-10-28", "pm"),
    ("immigration", os.path.join(SRC, "移民政策速报", "episodes"),
     "2026-10-27", "am"),
    ("immigration", os.path.join(SRC, "移民政策速报", "episodes"),
     "2026-10-28", "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     "2026-10-26", "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     "2026-10-27", "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     "2026-10-28", "am"),
]
SINGLE = ("silicon-valley", "longevity")
STOCKS_DATES = ["2026-10-22", "2026-10-23", "2026-10-26",
                "2026-10-27", "2026-10-28"]


def upload_url(ep_dir):
    p = os.path.join(ep_dir, "upload.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("url", "") or ""
    return ""


def script_lead(ep_dir):
    """script.md H1 后的第一段正文（theme 兜底，与既往硅谷页口径一致）。"""
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

    def register(prog_id, date, dir_name, title, theme, audio_src, video_url,
                 src_note, dedupe_by_date=False):
        cdir = os.path.join(HUB, "content", prog_id, dir_name)
        os.makedirs(cdir, exist_ok=True)
        audio_dst = os.path.join(cdir, "audio.mp3")
        shutil.copyfile(audio_src, audio_dst)
        sec = duration_sec(audio_dst)
        dur = fmt_dur(sec)
        write_page(os.path.join(cdir, "index.md"), title, theme, dur,
                   video_url, src_note)
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
        if dedupe_by_date:
            prog["episodes"] = [e for e in prog["episodes"]
                                if e["date"] != date]
        else:
            prog["episodes"] = [e for e in prog["episodes"]
                                if not (e["date"] == date
                                        and e["title"] == title)]
        prog["episodes"].append(ep)
        done.append(prog_id + "/" + dir_name)

    for prog_id, base, date, slot in JOBS:
        ep_dir = os.path.join(base, date)
        narration = os.path.join(ep_dir, "narration.mp3")
        if not os.path.isfile(narration):
            skipped.append(prog_id + "/" + date + " (no narration)")
            continue
        video_url = upload_url(ep_dir)
        title, theme = read_title_theme(ep_dir)
        if title.startswith("本节目"):
            # description.txt 首行是免责声明时改用 script.md 的 H1
            # （backfill_20261027 同口径）
            for line in open(os.path.join(ep_dir, "script.md"),
                             encoding="utf-8"):
                if line.strip().startswith("# "):
                    title = line.strip()[2:].strip()
                    break
        if theme.replace("：", "").replace(":", "").strip() in ("出处", ""):
            # description.txt 第二行只是出处标题时，用 script 首段作主题
            # （与已登记的硅谷 2026-10-26 页口径一致）
            lead = script_lead(ep_dir)
            if lead:
                theme = lead
        dir_name = date + "-pm" if (prog_id in SINGLE and slot == "pm") \
            else date
        register(prog_id, date, dir_name, title, theme, narration,
                 video_url, ep_dir)

    with open(os.path.join(MV, "upload-progress.json"), encoding="utf-8") as f:
        progress = json.load(f)
    for date in STOCKS_DATES:
        info = progress.get(date, {})
        audio_src = os.path.join(MV, "work", date, "podcast-audio.mp3")
        if info.get("status") != "done" or not os.path.isfile(audio_src):
            skipped.append("stocks-pm/" + date +
                           " (status=%s, podcast-audio %s)" %
                           (info.get("status"),
                            "ok" if os.path.isfile(audio_src) else "missing"))
            continue
        title = info.get("title") or (
            "美股盘后小结 %s月%s日" % (date[5:7].lstrip("0"),
                                      date[8:10].lstrip("0")))
        register("stocks-pm", date, date, title, title, audio_src,
                 info.get("url", ""), audio_src, dedupe_by_date=True)

    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-10-29"
    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)
    print("registered:", len(done))
    for d in done:
        print("  +", d)
    print("skipped:", skipped)
    for pid in ("fred-am", "fred-pm", "silicon-valley", "longevity",
                "immigration", "bay-area-benefits", "stocks-pm"):
        print(pid, "count=", programs[pid]["count"],
              "latest=", programs[pid]["episodes"][0]["date"])


if __name__ == "__main__":
    main()
