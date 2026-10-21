#!/usr/bin/env python3
"""Register existing broadcast stock into the hub (index.json + content dirs).

Scope (2026-10-21 distribution push): only finished stock (narration.mp3 /
published video) is registered. No new content is produced; audio for the
stocks show is the audio track of its already-published finished videos.

Excluded on purpose:
- News (news-am/news-pm): internal briefing for Ezra only, never public.
- FRED morning 2026-10-13..16: known unit errors, uncorrected versions.
- Script-only episode dirs (no narration/final): not finished stock.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser("~/workspace/your_files/新闻节目")
STOCKS = os.path.expanduser(
    "~/workspace/goals/goal-5/hidden_files/market-video")

YT = {
    ("immigration", "2026-10-16"): "https://www.youtube.com/watch?v=X4wgpVsvhr8",
    ("immigration", "2026-10-19"): "https://www.youtube.com/watch?v=bP0Au4tJUqI",
    ("immigration", "2026-10-20"): "https://www.youtube.com/watch?v=X-VA7-4Ae84",
    ("longevity", "2026-10-16"): "https://www.youtube.com/watch?v=p_H91GBe-4I",
    ("longevity", "2026-10-19"): "https://www.youtube.com/watch?v=D-6m-KGftv8",
}

# (program_id, source_dir, slot) slot: am/pm label inside single-program shows
JOBS = [
    ("fred-am", os.path.join(SRC, "episodes"),
     ["2026-10-17", "2026-10-20"], "am"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"),
     ["2026-10-17", "2026-10-18", "2026-10-20"], "pm"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes"),
     ["2026-10-16", "2026-10-20"], "am"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes-evening"),
     ["2026-10-19", "2026-10-20"], "pm"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes"),
     ["2026-10-16", "2026-10-19"], "am"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening"),
     ["2026-10-20"], "pm"),
    ("immigration", os.path.join(SRC, "移民政策速报", "episodes"),
     ["2026-10-16", "2026-10-19", "2026-10-20"], "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     ["2026-10-16", "2026-10-20"], "am"),
]


def duration_sec(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=60)
    try:
        return int(round(float(out.stdout.strip())))
    except ValueError:
        return 0


def fmt_dur(sec):
    return "%d:%02d" % (sec // 60, sec % 60)


def read_title_theme(ep_dir):
    """Title from script.md H1 (or description.txt for FRED); theme = lead."""
    title, theme = "", ""
    desc = os.path.join(ep_dir, "description.txt")
    script = os.path.join(ep_dir, "script.md")
    if os.path.isfile(desc):
        lines = [l.strip() for l in open(desc, encoding="utf-8")
                 if l.strip()]
        if lines:
            title = lines[0]
        if len(lines) > 1:
            theme = lines[1]
    if os.path.isfile(script):
        lines = open(script, encoding="utf-8").read().splitlines()
        h1 = ""
        para = ""
        for l in lines:
            s = l.strip()
            if not h1 and s.startswith("# "):
                h1 = s[2:].strip()
                continue
            if h1 and s and not s.startswith(("#", ">", "---")):
                para = s
                break
        if not title:
            title = h1
        if not theme:
            theme = para
    theme = re.sub(r"\s+", " ", theme)[:120]
    return title, theme


def write_page(path, title, theme, dur, video_url, src_dir):
    video_line = video_url if video_url else "本地存档 final.mp4（待上传）"
    body = (
        "# " + title + "\n\n"
        "## 一句话主题\n" + (theme or title) + "\n\n"
        "时长：" + dur + "\n"
        "视频：" + video_line + "\n"
        "来源：存量成品，2026-10-21 分发攻坚登记入枢纽。\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def main():
    with open(os.path.join(HUB, "index.json"), encoding="utf-8") as f:
        hub = json.load(f)
    programs = {p["id"]: p for p in hub["programs"]}

    if "fred-am" not in programs:
        fred_am = {
            "id": "fred-am", "name": "百指日报 · 早间", "slot": "早间",
            "desc": "美国百指日报早版：100 个美国关键经济指标（FRED）看异常、比变化，深耕 AI 与生物科技。",
            "category": "时效", "episodes": [], "count": 0}
        fred_pm = {
            "id": "fred-pm", "name": "百指日报 · 晚间", "slot": "晚间",
            "desc": "美国百指日报晚版：当日经济指标收官复盘与次日前瞻。",
            "category": "时效", "episodes": [], "count": 0}
        ids = [p["id"] for p in hub["programs"]]
        at = ids.index("stocks-pm") + 1
        hub["programs"][at:at] = [fred_am, fred_pm]
        programs["fred-am"] = fred_am
        programs["fred-pm"] = fred_pm

    registered = {}

    def add_episode(prog_id, date, dir_name, title, theme, audio_src,
                    video_url, src_note):
        cdir = os.path.join(HUB, "content", prog_id, dir_name)
        os.makedirs(cdir, exist_ok=True)
        audio_dst = os.path.join(cdir, "audio.mp3")
        shutil.copyfile(audio_src, audio_dst)
        sec = duration_sec(audio_dst)
        dur = fmt_dur(sec)
        write_page(os.path.join(cdir, "index.md"), title, theme, dur,
                   video_url, src_note)
        ep = {
            "date": date,
            "title": title,
            "scripture": "",
            "theme": theme or title,
            "audio": "content/%s/%s/audio.mp3" % (prog_id, dir_name),
            "page": "content/%s/%s/index.md" % (prog_id, dir_name),
            "duration_sec": sec,
            "duration": dur,
            "video_url": video_url,
            "links": {"spotify": "", "x": "", "youtube": video_url},
        }
        prog = programs[prog_id]
        prog["episodes"] = [e for e in prog["episodes"]
                            if not (e["date"] == date
                                    and e["title"] == title)]
        prog["episodes"].append(ep)
        registered.setdefault(prog_id, []).append(date + "/" + dir_name)

    for prog_id, base, dates, slot in JOBS:
        single = prog_id in ("silicon-valley", "longevity")
        for date in dates:
            ep_dir = os.path.join(base, date)
            narration = os.path.join(ep_dir, "narration.mp3")
            if not os.path.isfile(narration):
                print("SKIP no narration:", prog_id, date)
                continue
            title, theme = read_title_theme(ep_dir)
            if single and slot == "pm":
                title += " · 晚版"
            dir_name = date + "-pm" if (single and slot == "pm") else date
            video_url = YT.get((prog_id, date), "")
            add_episode(prog_id, date, dir_name, title, theme, narration,
                        video_url, ep_dir)

    # Stocks evening show: episodes already published on YouTube; audio is
    # extracted from the finished local video files (existing stock only).
    prog_id = "stocks-pm"
    with open(os.path.join(STOCKS, "upload-progress.json"),
              encoding="utf-8") as f:
        progress = json.load(f)
    for date in sorted(progress):
        info = progress[date]
        if info.get("status") != "done":
            continue
        video_url = info.get("url", "")
        title = info.get("title") or (
            "美股盘后小结 %s月%s日" % (date[5:7].lstrip("0"),
                                      date[8:10].lstrip("0")))
        src_video = os.path.join(STOCKS, "work", date,
                                 "market-%s_169.mp4" % date)
        if not os.path.isfile(src_video):
            alt = os.path.join(STOCKS, "samples",
                               "market-%s_169.mp4" % date)
            if os.path.isfile(alt):
                src_video = alt
        cdir = os.path.join(HUB, "content", prog_id, date)
        os.makedirs(cdir, exist_ok=True)
        audio_dst = os.path.join(cdir, "audio.mp3")
        if os.path.isfile(src_video) and not os.path.isfile(audio_dst):
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-i", src_video,
                 "-vn", "-codec:a", "libmp3lame", "-q:a", "4", audio_dst],
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                print("AUDIO EXTRACT FAIL", date, r.stderr[:200])
        if not os.path.isfile(audio_dst):
            print("SKIP stocks no audio:", date)
            continue
        sec = duration_sec(audio_dst)
        dur = fmt_dur(sec)
        write_page(os.path.join(cdir, "index.md"), title, title, dur,
                   video_url, src_video)
        ep = {
            "date": date, "title": title, "scripture": "", "theme": title,
            "audio": "content/%s/%s/audio.mp3" % (prog_id, date),
            "page": "content/%s/%s/index.md" % (prog_id, date),
            "duration_sec": sec, "duration": dur,
            "video_url": video_url,
            "links": {"spotify": "", "x": "", "youtube": video_url},
        }
        prog = programs[prog_id]
        prog["episodes"] = [e for e in prog["episodes"]
                            if e["date"] != date]
        prog["episodes"].append(ep)
        registered.setdefault(prog_id, []).append(date)

    desc_fix = {
        "stocks-pm": "晚间股市播报：美股盘后小结，三大指数、板块与个股要点。",
        "longevity": "长寿与健康前沿速报：每天替你读长寿与健康领域的论文与研究。",
        "silicon-valley": "硅谷科技动态速报：AI 与科技公司最新进展。",
        "immigration": "移民政策速报：美国移民政策与法规变化解读。",
        "bay-area-benefits": "湾区福利与生活资讯速报：福利、补助与生活信息。",
    }
    for pid, desc in desc_fix.items():
        if pid in programs and programs[pid]["episodes"]:
            programs[pid]["desc"] = desc

    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-10-21"

    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)
    print(json.dumps(registered, ensure_ascii=False, indent=1))
    print("TOTAL new/updated episodes:",
          sum(len(v) for v in registered.values()))


if __name__ == "__main__":
    sys.exit(main())
