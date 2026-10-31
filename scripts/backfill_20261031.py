#!/usr/bin/env python3
"""2026-10-31 feed 回填：2026-10-29/30 广播线 RSS 登记断档疏通。

沿 build_broadcast_hub.py / backfill_20261029.py 的登记口径：复制
narration -> content/<series>/<dir>/audio.mp3，write_page 写 index.md，
更新 index.json + docs/index.json 的 episodes/count。视频链接取各期
upload.json 的 url 字段；stocks-pm 取 goal-5 market-video 的
upload-progress.json，音频用其 work/<date>/podcast-audio.mp3。

登记门（时效日检 2026-10-31 派工口径）：只登记已在 YouTube 发布且
narration.mp3 在盘的期。upload.json 的 status 判定：
- fred / silicon-pm / longevity / bay-area-benefits：status 以
  published 开头（published / published_solo_resume，后者须有
  resume 续传成功留痕与 video_id/url，本批仅硅谷晚间 2026-10-29 一期）；
- immigration：该线 upload.json 历来以 uploaded 记已直传发布
  （2026-10-26/27/28 三期均以此状态登记入 feed），有 video_id/url
  者按已发布计，本批仅 2026-10-29 一期。
状态变更（运行中实查）：silicon-valley 日间 2026-10-29 在派工时为
assembled_qc_passed_upload_blocked_quota（未发布），本脚本运行期间
（2026-10-31 07:4x PDT）由续传轮上传成功（videoId STDDD5a1Yfo、
oEmbed 回读、已入技术讲解播放列表，upload.json status 已回写
published、retry_log 留痕），故按已发布登记，不再列跳过。

跳过期（本脚本在 SKIPS_CHECK 中逐个探盘留痕，不登记）：
- fred-am 2026-10-30：源目录仅 facts+写稿输入，无 narration、无 upload；
- silicon-valley 日间 2026-10-30：status text_prep_only，无 narration；
- immigration 2026-10-30：源目录仅 facts.json，无 narration、无 upload；
- stocks-pm 2026-10-30：upload-progress.json 无此日期条目（缺期）。
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
    ("fred-am", os.path.join(SRC, "episodes"), "2026-10-29", "am"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-10-29", "pm"),
    ("fred-pm", os.path.join(SRC, "episodes-evening"), "2026-10-30", "pm"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes"),
     "2026-10-29", "am"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes-evening"),
     "2026-10-29", "pm"),
    ("silicon-valley", os.path.join(SRC, "硅谷科技日报", "episodes-evening"),
     "2026-10-30", "pm"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes"),
     "2026-10-29", "am"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening"),
     "2026-10-29", "pm"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes"),
     "2026-10-30", "am"),
    ("longevity", os.path.join(SRC, "长寿前沿日报", "episodes-evening"),
     "2026-10-30", "pm"),
    ("immigration", os.path.join(SRC, "移民政策速报", "episodes"),
     "2026-10-29", "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     "2026-10-29", "am"),
    ("bay-area-benefits", os.path.join(SRC, "湾区福利速报", "episodes"),
     "2026-10-30", "am"),
]
SINGLE = ("silicon-valley", "longevity")
STOCKS_DATES = ["2026-10-29"]

# 应跳过期：(label, ep_dir) 与 stocks 日期，运行中逐个探盘留痕
SKIPS_CHECK = [
    ("fred-am/2026-10-30", os.path.join(SRC, "episodes", "2026-10-30")),
    ("silicon-valley-am/2026-10-30",
     os.path.join(SRC, "硅谷科技日报", "episodes", "2026-10-30")),
    ("immigration/2026-10-30",
     os.path.join(SRC, "移民政策速报", "episodes", "2026-10-30")),
]


def load_upload(ep_dir):
    p = os.path.join(ep_dir, "upload.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def is_published(prog_id, up):
    status = (up.get("status") or "").strip()
    url = up.get("url") or ""
    if not url:
        return False
    if status.startswith("published"):
        return True
    if prog_id == "immigration" and status == "uploaded":
        return True
    return False


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
        up = load_upload(ep_dir)
        if not is_published(prog_id, up):
            skipped.append(prog_id + "/" + date +
                           " (not published, status=%s)" % up.get("status"))
            continue
        video_url = up.get("url", "") or ""
        title, theme = read_title_theme(ep_dir)
        if title.startswith("本节目"):
            for line in open(os.path.join(ep_dir, "script.md"),
                             encoding="utf-8"):
                if line.strip().startswith("# "):
                    title = line.strip()[2:].strip()
                    break
        if theme.replace("：", "").replace(":", "").strip() in ("出处", ""):
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

    for label, ep_dir in SKIPS_CHECK:
        up = load_upload(ep_dir)
        narr = os.path.isfile(os.path.join(ep_dir, "narration.mp3"))
        print("skip-check:", label, "narration=", narr,
              "status=", up.get("status"))
    if "2026-10-30" not in progress:
        print("skip-check: stocks-pm/2026-10-30 not in upload-progress.json")

    for p in hub["programs"]:
        p["episodes"].sort(key=lambda e: e["date"], reverse=True)
        p["count"] = len(p["episodes"])
    hub["updated"] = "2026-10-31"
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
