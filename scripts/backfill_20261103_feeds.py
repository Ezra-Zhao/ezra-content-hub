#!/usr/bin/env python3
"""2026-11-03 三条广播 feed 登记补登：A 组全线断更审计派单。

范围（均为「已发布/已产出但未入 feed」，审计实查口径）：
- fred-pm 2026-11-02：已于 2026-11-03 发布 YouTube（eCjuHsziXNM、
  upload.json status=published、API 回读 public），narration.mp3 在盘。
- stocks-pm 2026-10-30：视频已于 2026-11-03 补发 YouTube
  （EWgwKuYlVsA，upload-progress.json status=done），播客音频版
  podcast-audio.mp3 已生成存档（work/2026-10-30/）。
- bay-area-benefits 2026-11-02 / 2026-11-03：两期均已发布 YouTube
  （_Ne4IghnCRA / Wb0rJ1pZDrQ，upload.json status=published），
  narration.mp3 在盘。注意：两期配音为 EL 额度耗尽后的定版
  fallback 过渡男声（avocado_v2:vd2_exacting_pillar），非克隆声线，
  登记页如实标注，不冒充克隆声线版。

登记口径沿 backfill_20261102_fred.py：音频拷入 content/<prog>/<date>/、
write_page 生成节目页、index.json 双写（根目录＋docs/）。
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_broadcast_hub import read_title_theme, duration_sec, fmt_dur, write_page

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS = os.path.expanduser("~/workspace/your_files/新闻节目")
MARKET = os.path.expanduser(
    "~/workspace/goals/goal-5/hidden_files/market-video")


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


def register(hub, programs, prog_id, date, src_dir, audio_name, url,
             title=None, theme=None, page_note=None):
    narration = os.path.join(src_dir, audio_name)
    if not os.path.isfile(narration):
        return f"{prog_id}/{date} (missing {audio_name})"
    if title is None:
        title, theme = read_title_theme(src_dir)
    if title.startswith("本节目"):
        for line in open(os.path.join(src_dir, "script.md"),
                         encoding="utf-8"):
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                break
    if theme is None or theme.replace("：", "").replace(":", "").strip() in ("出处", ""):
        lead = script_lead(src_dir)
        if lead:
            theme = lead
    cdir = os.path.join(HUB, "content", prog_id, date)
    os.makedirs(cdir, exist_ok=True)
    audio_dst = os.path.join(cdir, "audio.mp3")
    shutil.copyfile(narration, audio_dst)
    sec = duration_sec(audio_dst)
    dur = fmt_dur(sec)
    page_path = os.path.join(cdir, "index.md")
    write_page(page_path, title, theme, dur, url, src_dir)
    if page_note:
        with open(page_path, "a", encoding="utf-8") as f:
            f.write(page_note)
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
    return None


def main():
    with open(os.path.join(HUB, "index.json"), encoding="utf-8") as f:
        hub = json.load(f)
    programs = {p["id"]: p for p in hub["programs"]}
    done, skipped = [], []

    # 1) fred-pm 2026-11-02
    d = os.path.join(NEWS, "episodes-evening", "2026-11-02")
    with open(os.path.join(d, "upload.json"), encoding="utf-8") as f:
        up = json.load(f)
    if up.get("status") == "published" and up.get("url"):
        err = register(hub, programs, "fred-pm", "2026-11-02", d,
                       "narration.mp3", up["url"])
        (skipped if err else done).append(err or "fred-pm/2026-11-02")
    else:
        skipped.append("fred-pm/2026-11-02 (upload.json not published)")

    # 2) stocks-pm 2026-10-30
    with open(os.path.join(MARKET, "upload-progress.json"),
              encoding="utf-8") as f:
        progess = json.load(f)
    st = progess.get("2026-10-30", {})
    wdir = os.path.join(MARKET, "work", "2026-10-30")
    if st.get("status") == "done" and st.get("url"):
        script = open(os.path.join(wdir, "script-2026-10-30.txt"),
                      encoding="utf-8").read()
        theme = " ".join(script.split("\n\n")[0].split())[:120]
        err = register(hub, programs, "stocks-pm", "2026-10-30", wdir,
                       "podcast-audio.mp3", st["url"],
                       title=st["title"], theme=theme)
        (skipped if err else done).append(err or "stocks-pm/2026-10-30")
    else:
        skipped.append("stocks-pm/2026-10-30 (upload-progress not done)")

    # 3) bay-area-benefits 2026-11-02 / 2026-11-03（fallback 声线如实标注）
    for date in ("2026-11-02", "2026-11-03"):
        d = os.path.join(NEWS, "湾区福利速报", "episodes", date)
        with open(os.path.join(d, "upload.json"), encoding="utf-8") as f:
            up = json.load(f)
        if up.get("status") == "published" and up.get("url"):
            note = ("配音说明：本期为过渡男声版（fallback_voice "
                    "avocado_v2:vd2_exacting_pillar），非 ElevenLabs "
                    "克隆声线；EL 额度 2026-11-16 重置后切回克隆声线。\n")
            err = register(hub, programs, "bay-area-benefits", date, d,
                           "narration.mp3", up["url"], page_note=note)
            (skipped if err else done).append(
                err or f"bay-area-benefits/{date}")
        else:
            skipped.append(f"bay-area-benefits/{date} (not published)")

    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-11-03"
    for path in (os.path.join(HUB, "index.json"),
                 os.path.join(HUB, "docs", "index.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hub, f, ensure_ascii=False, indent=1)
    print("registered:", len(done))
    for x in done:
        print("  +", x)
    print("skipped:", skipped)
    for pid in ("fred-am", "fred-pm", "stocks-pm", "bay-area-benefits"):
        print(pid, "count=", programs[pid]["count"],
              "latest=", programs[pid]["episodes"][0]["date"])


if __name__ == "__main__":
    main()
