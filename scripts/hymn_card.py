#!/usr/bin/env python3
"""每日灵修「今日诗歌」卡（2026-11-25 Ezra 亲口定版：灵修每天都带）。

职责：
  1. 建/读赞美诗元数据索引（scripts/hymn_index.json）：候选池＝已有中文对版
     乐谱的编号；元数据来自乐谱文件头、歌曲源文件（经文依据/适用场景）、
     发行记录.md（Spotify/HyperFollow 链接）、视频/hymn-NNN/upload.json
     （YouTube 链接）、audio/ 发行版 MP3。
  2. 按日期配歌：读当日灵修 AM/PM(/NOON) 的经文与主题打分，30 天内不重复；
     结果写入配歌登记 content/hymn-of-day.json，并同步人读版登记表
     ~/workspace/your_files/播客音频线/灵修今日诗歌-配歌登记表.md。
  3. 托管音频：所配歌的发行版 MP3 首次被配时复制进 content/hymn-audio/，
     页面用 raw.githubusercontent 直链播放（与灵修音频同一托管惯例）。
  4. 渲染卡片 HTML：播放器＋简谱谱面（乐谱 md 按原样排版，唱词只随谱面
     段落标题呈现，不另贴整首歌词）＋推广链接（YouTube/Spotify/更多赞美诗）。

被 build_transcript_pages.py 在生成 devotion 中文落地页时调用：
  card_html_for_guid(guid, date) -> str（不适用时返回空串）
"""
import glob
import html
import json
import os
import re
import shutil

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.expanduser("~/workspace/your_files")
HYMN_DIR = os.path.join(WS, "万族赞美诗")
SHEET_DIR = os.path.join(HYMN_DIR, "乐谱")
AUDIO_DIR = os.path.join(HYMN_DIR, "audio")
VIDEO_DIR = os.path.join(HYMN_DIR, "视频")
RELEASE_MD = os.path.join(HYMN_DIR, "发行记录.md")
SONG_SRC_DIRS = ["01-原创敬拜", "02-民族风改编", "03-公有领域翻译"]
INDEX_PATH = os.path.join(HUB, "scripts", "hymn_index.json")
REGISTRY_PATH = os.path.join(HUB, "content", "hymn-of-day.json")
REGISTRY_MD = os.path.join(WS, "播客音频线", "灵修今日诗歌-配歌登记表.md")
AUDIO_OUT_DIR = os.path.join(HUB, "content", "hymn-audio")
RAW = "https://raw.githubusercontent.com/Ezra-Zhao/ezra-content-hub/main"
CARD_START = "2026-11-25"
NO_REPEAT_DAYS = 30
SPOTIFY_ARTIST = "https://open.spotify.com/artist/1h6UkqNEUkNJzfn7fKv64U"
MORE_HYMNS_URL = "https://ezrazhao.com/#music"

BOOKS = [
    "创世纪", "出埃及记", "利未记", "民数记", "申命记", "约书亚记",
    "士师记", "路得记", "撒母耳记上", "撒母耳记下", "列王纪上", "列王纪下",
    "历代志上", "历代志下", "以斯拉记", "尼希米记", "以斯帖记", "约伯记",
    "诗篇", "箴言", "传道书", "雅歌", "以赛亚书", "耶利米书", "耶利米哀歌",
    "以西结书", "但以理书", "何西阿书", "约珥书", "阿摩司书", "俄巴底亚书",
    "约拿书", "弥迦书", "那鸿书", "哈巴谷书", "西番雅书", "哈该书",
    "撒迦利亚书", "玛拉基书", "马太福音", "马可福音", "路加福音", "约翰福音",
    "使徒行传", "罗马书", "哥林多前书", "哥林多后书", "加拉太书", "以弗所书",
    "腓立比书", "歌罗西书", "帖撒罗尼迦前书", "帖撒罗尼迦后书",
    "提摩太前书", "提摩太后书", "提多书", "腓利门书", "希伯来书", "雅各书",
    "彼得前书", "彼得后书", "约翰一书", "约翰二书", "约翰三书", "犹大书",
    "启示录",
]
BOOK_SET = sorted(set(BOOKS), key=len, reverse=True)

# 主题同义词（灵修主题词 -> 诗歌侧用词），只做加分不做硬过滤
SYNONYMS = {
    "感恩": ["谢恩", "感恩", "称谢"],
    "惧怕": ["平安", "不要怕", "安慰"],
    "害怕": ["平安", "不要怕"],
    "焦虑": ["平安", "安息", "交托"],
    "挂虑": ["平安", "交托", "安息"],
    "安息": ["安息", "安然"],
    "怜悯": ["怜悯", "慈爱", "恩典"],
    "怜": ["怜悯", "慈爱"],
    "顺服": ["顺服", "降服"],
    "医治": ["医治", "痊愈"],
    "方向": ["指引", "引路", "光"],
    "迷茫": ["指引", "光", "引路"],
    "重新开始": ["更新", "新造", "复兴"],
    "复兴": ["复兴", "更新"],
    "信实": ["信实", "不改变"],
    "盼望": ["盼望", "等候"],
    "等候": ["等候", "盼望"],
    "喜乐": ["喜乐", "欢欣", "欢呼"],
    "平安": ["平安", "安息"],
    "过去": ["怜悯", "恩典", "赦免"],
    "罪": ["赦免", "怜悯", "宝血", "十字架"],
    "赦免": ["赦免", "怜悯"],
    "失衡": ["顺服", "真理"],
    "真理": ["真理", "顺服"],
    "同在": ["同在", "不撇下"],
    "力量": ["刚强", "得力"],
    "软弱": ["刚强", "恩典够用", "得力"],
    "感恩节": ["谢恩", "感恩"],
    "圣诞": ["降生", "马槽", "以马内利"],
    "降生": ["降生", "马槽"],
    "光": ["光", "光明"],
    "黑暗": ["光", "光明"],
    "牧者": ["牧者", "牧人"],
    "家": ["归回", "回家"],
}


def esc(s):
    return html.escape(s or "", quote=True)


def parse_refs(text):
    """从文本里抽 (书名, 章) 列表。"""
    out = []
    if not text:
        return out
    for book in BOOK_SET:
        for m in re.finditer(re.escape(book) + r"\s*(\d+)\s*[:：]", text):
            out.append((book, int(m.group(1))))
    return out


def bigrams(text):
    text = re.sub(r"[\s，。、；：！？·｜|:：\-—「」『』（）()\[\]0-9A-Za-z]", "", text or "")
    return {text[i:i + 2] for i in range(len(text) - 1)}


# ---------------- 元数据索引 ----------------

def _sheet_meta(path):
    txt = open(path, encoding="utf-8").read()
    head = "\n".join(txt.splitlines()[:30])
    key = re.search(r"调性[:：]\s*\**([^（(|\n*]+)", head)
    tempo = re.search(r"速度[:：]\s*\**(\d+)\s*BPM", head)
    meter = re.search(r"拍号[:：]\s*\**([0-9]/[0-9])", head)
    return {
        "key": key.group(1).strip() if key else "",
        "tempo": (tempo.group(1) + " BPM") if tempo else "",
        "meter": meter.group(1) if meter else "",
        "text": txt,
    }


def _song_src_meta(no):
    for d in SONG_SRC_DIRS:
        for p in glob.glob(os.path.join(HYMN_DIR, d, no + "-*.md")):
            txt = open(p, encoding="utf-8").read()
            scr = re.search(r"经文依据\*\*[:：]\s*(.+)", txt)
            scene = re.search(r"适用场景\*\*[:：]\s*(.+)", txt)
            style = re.search(r"风格\*\*[:：]\s*(.+)", txt)
            return {
                "scripture": scr.group(1).strip() if scr else "",
                "scene": scene.group(1).strip() if scene else "",
                "style": (style.group(1).strip()[:60] if style else ""),
            }
    return {"scripture": "", "scene": "", "style": ""}


def _release_links():
    """发行记录.md -> {编号: {spotify, hyperfollow}}（只取中文版条目）。"""
    out = {}
    if not os.path.exists(RELEASE_MD):
        return out
    txt = open(RELEASE_MD, encoding="utf-8").read()
    for sec in re.split(r"^## ", txt, flags=re.M)[1:]:
        m = re.match(r"(\d{3})\s*(?:[《\s])", sec)
        if not m:
            continue
        head = sec.splitlines()[0]
        if any(k in head for k in ("英文版", "韩文版", "西文版", "日文版", "法文版", "越文版")):
            continue
        no = m.group(1)
        if no in out:
            continue
        track = re.search(r"https://open\.spotify\.com/track/[A-Za-z0-9]+", sec)
        album = re.search(r"https://open\.spotify\.com/album/[A-Za-z0-9]+", sec)
        hyper = re.search(r"https://distrokid\.com/hyperfollow/ezrazhao/[A-Za-z0-9\-]+", sec)
        out[no] = {
            "spotify": (track or album).group(0) if (track or album) else "",
            "hyperfollow": hyper.group(0) if hyper else "",
        }
    return out


def _youtube_link(no):
    p = os.path.join(VIDEO_DIR, "hymn-" + no, "upload.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            if d.get("url") and d.get("privacy", "public") == "public":
                return d["url"]
        except Exception:
            pass
    return ""


def _audio_file(no, title):
    cands = [p for p in glob.glob(os.path.join(AUDIO_DIR, no + "-*.mp3"))
             if "英文版" not in os.path.basename(p)]
    if not cands:
        return ""
    exact = os.path.join(AUDIO_DIR, no + "-" + title + ".mp3")
    return exact if exact in cands else sorted(cands)[0]


def build_index(force=False):
    if not force and os.path.exists(INDEX_PATH):
        try:
            idx = json.load(open(INDEX_PATH, encoding="utf-8"))
            if idx:
                return idx
        except Exception:
            pass
    links = _release_links()
    idx = {}
    # 同一编号可能有多个谱版：发行版 > plain > 高版本号 vN > 其他变体
    sheet_by_no = {}
    for p in glob.glob(os.path.join(SHEET_DIR, "*.md")):
        name = os.path.basename(p)
        if "谱集" in name or any(k in name for k in
                                 ("英文版", "西班牙语版", "韩语版", "越文版", "日文版", "法文版")):
            continue
        m = re.match(r"(\d{3})-(.+?)-乐谱\.md$", name)
        if m:
            sheet_by_no.setdefault(m.group(1), []).append((0, m.group(2), p))
            continue
        m = re.match(r"(\d{3})-(.+?)-乐谱-发行版\.md$", name)
        if m:
            sheet_by_no.setdefault(m.group(1), []).append((0, m.group(2), p))
            continue
        m = re.match(r"(\d{3})-(.+?)-乐谱-v(\d+)[a-z]?\.md$", name)
        if m:
            sheet_by_no.setdefault(m.group(1), []).append(
                (10 - min(int(m.group(3)), 9), m.group(2), p))
            continue
        m = re.match(r"(\d{3})-(.+?)-乐谱-.+\.md$", name)
        if m:
            sheet_by_no.setdefault(m.group(1), []).append((50, m.group(2), p))
    for no, cands in sorted(sheet_by_no.items()):
        cands.sort()
        _, title, p = cands[0]
        meta = _sheet_meta(p)
        src = _song_src_meta(no)
        audio = _audio_file(no, title)
        lk = links.get(no, {})
        idx[no] = {
            "no": no,
            "title": title,
            "key": meta["key"],
            "tempo": meta["tempo"],
            "meter": meta["meter"],
            "sheet_path": p,
            "scripture": src["scripture"],
            "scene": src["scene"],
            "style": src["style"],
            "audio_src": audio,
            "youtube": _youtube_link(no),
            "spotify": lk.get("spotify", ""),
            "hyperfollow": lk.get("hyperfollow", ""),
            "refs": parse_refs(src["scripture"] + " " + title),
        }
    json.dump(idx, open(INDEX_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return idx


# ---------------- 配歌 ----------------

def _load_registry():
    if os.path.exists(REGISTRY_PATH):
        try:
            return json.load(open(REGISTRY_PATH, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_registry(reg):
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    json.dump(reg, open(REGISTRY_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    lines = ["# 灵修「今日诗歌」配歌登记表",
             "",
             "由 content-hub/scripts/hymn_card.py 自动维护（登记正本：content-hub/content/hymn-of-day.json）。",
             "规则：按当日灵修经文与主题配歌；同一首 30 天内不重复。",
             "",
             "| 日期 | 编号 | 歌名 | 当日经文 | 匹配依据 |",
             "|---|---|---|---|---|"]
    for date in sorted(reg):
        r = reg[date]
        lines.append("| {} | {} | {} | {} | {} |".format(
            date, r["no"], r["title"], r.get("devotion_refs", ""),
            r.get("basis", "").replace("|", "／")))
    try:
        os.makedirs(os.path.dirname(REGISTRY_MD), exist_ok=True)
        open(REGISTRY_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    except Exception:
        pass


def _devotion_day_info(date):
    """当日灵修（AM/PM/NOON）经文与主题文本。"""
    refs, texts, ref_strs = [], [], []
    for series in ("devotion-am", "devotion-noon", "devotion-pm"):
        p = os.path.join(HUB, "content", series, date, "index.md")
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        m = re.search(r"^#\s+(.+)$", txt, re.M)
        if m:
            texts.append(m.group(1).strip())
        s = re.search(r"经文：(.+)", txt)
        if s:
            ref_strs.append(s.group(1).strip())
            refs += parse_refs(s.group(1))
        t = re.search(r"##\s*一句话主题\s*\n+(.+)", txt)
        if t:
            texts.append(t.group(1).strip())
    return refs, " ".join(texts), "；".join(ref_strs)


def pick_for_date(date):
    reg = _load_registry()
    if date in reg:
        return reg[date]
    idx = build_index()
    refs, theme_text, ref_strs = _devotion_day_info(date)
    recent = set()
    for d, r in reg.items():
        try:
            delta = (re_date(date) - re_date(d)).days
        except Exception:
            continue
        if 0 <= delta < NO_REPEAT_DAYS:
            recent.add(r["no"])
    dev_bi = bigrams(theme_text)
    seasonal = ("圣诞", "降生", "马槽", "以马内利", "大喜的信息", "星夜里的好消息")
    in_season = date[5:] >= "12-01" or date[5:] <= "01-06"
    scored = []
    for no, h in idx.items():
        if no in recent or not h["audio_src"]:
            continue
        score, why = 0, []
        h_refs = [tuple(r) for r in h["refs"]]
        ref_hit = 0
        for (b, c) in refs:
            if (b, c) in h_refs:
                score += 100
                ref_hit = 100
                why.append("经文同章（{} {}）".format(b, c))
            elif any(b == hb for hb, _ in h_refs):
                score += 40
                ref_hit = max(ref_hit, 40)
                why.append("经文同书（{}）".format(b))
        title_hay = h["title"] + " " + h["scripture"]
        hay = title_hay + " " + h["scene"]
        inter_title = dev_bi & bigrams(title_hay)
        inter_rest = dev_bi & bigrams(h["scene"])
        if inter_title or inter_rest:
            score += 4 * len(inter_title) + 2 * len(inter_rest)
            why.append("主题词重合：" + "、".join(
                sorted(inter_title | inter_rest)[:6]))
        syn_hits = 0
        for k, syns in SYNONYMS.items():
            if syn_hits >= 2:
                break
            if k in theme_text and any(s in title_hay for s in syns):
                score += 12
                syn_hits += 1
                why.append("主题呼应（{}）".format(k))
        # 节期歌（圣诞类）非节期、无经文命中时不胜出
        if (not in_season and ref_hit == 0
                and any(s in h["title"] for s in seasonal)):
            continue
        if h["youtube"]:
            score += 2
        if h["spotify"] or h["hyperfollow"]:
            score += 2
        used = sum(1 for r in reg.values() if r["no"] == no)
        scored.append((-score, used, no, h, why))
    if not scored:
        return None
    scored.sort()
    _, _, no, h, why = scored[0]
    basis = "；".join(dict.fromkeys(why)) or "按歌名与当日主题语义匹配（无经文直引依据）"
    entry = {
        "no": no,
        "title": h["title"],
        "basis": basis,
        "devotion_refs": ref_strs,
        "key": h["key"], "tempo": h["tempo"], "meter": h["meter"],
        "youtube": h["youtube"], "spotify": h["spotify"],
        "hyperfollow": h["hyperfollow"],
    }
    reg[date] = entry
    _save_registry(reg)
    return entry


def re_date(s):
    from datetime import date as _d
    y, m, dd = s.split("-")
    return _d(int(y), int(m), int(dd))


# ---------------- 谱面与卡片渲染 ----------------

def _render_sheet(sheet_path):
    txt = open(sheet_path, encoding="utf-8").read()
    lines = txt.splitlines()
    meta_bits = []
    for ln in lines[:30]:
        m = re.search(r"(词曲[:：].+)", ln)
        if m and not any("词曲" in b for b in meta_bits):
            meta_bits.append(m.group(1).strip())
        m = re.search(r"(调性[:：].+)", ln)
        if m:
            meta_bits.append(re.sub(r"\*\*", "", m.group(1).strip()))
            break
    out = []
    if meta_bits:
        out.append('<p class="sheet-meta">' + esc("｜".join(meta_bits)) + "</p>")
    # 分段：## 标题 + 代码块
    parts = re.split(r"^##\s+", txt, flags=re.M)[1:]
    for part in parts:
        head, _, rest = part.partition("\n")
        head = head.strip()
        blocks = re.findall(r"```\n?(.*?)```", rest, re.S)
        if not blocks:
            continue
        rows = []
        for blk in blocks:
            for ln in blk.splitlines():
                ln = ln.rstrip()
                if not ln.strip():
                    continue
                m = re.match(r"\s*(\d+)\s*\[\s*([^\]]*)\]\s*(.*)$", ln)
                if m:
                    rows.append(
                        '<div class="bar"><span class="barno">{}</span>'
                        '<span class="chord">{}</span>'
                        '<span class="notes">{}</span></div>'.format(
                            esc(m.group(1)), esc(m.group(2).strip()),
                            esc(m.group(3).strip())))
                else:
                    rows.append('<div class="bar"><span class="notes">{}</span></div>'.format(esc(ln.strip())))
        if rows:
            out.append('<div class="sheet-sec"><h4>{}</h4>{}</div>'.format(
                esc(head), "\n".join(rows)))
    return "\n".join(out)


CARD_CSS = """
.hymn-card{background:#fbf7ee;border:1px solid #e3d5b8;border-radius:10px;padding:16px 16px 8px;margin:28px 0}
.hymn-card h2{margin:0 0 4px;font-size:1.15rem}
.hymn-card .song{font-size:1.05rem;font-weight:700}
.hymn-card .basis{color:#777;font-size:.85rem}
.hymn-card audio{width:100%;margin:10px 0 4px}
.sheet-meta{color:#555;font-size:.9rem;margin:8px 0}
.sheet-sec{margin:12px 0}
.sheet-sec h4{margin:6px 0 4px;font-size:.98rem;color:#6b4e00}
.bar{display:flex;gap:8px;align-items:baseline;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.86rem;line-height:1.5;border-bottom:1px dotted #e7ddc6;padding:1px 0}
.barno{color:#a08c5a;min-width:2em;text-align:right}
.chord{color:#8a5a00;font-weight:700;min-width:3.2em}
.notes{letter-spacing:.08em;white-space:pre-wrap;word-break:break-all}
.hymn-links{margin:10px 0}
"""


def ensure_audio(no):
    dst = os.path.join(AUDIO_OUT_DIR, no + ".mp3")
    if not os.path.exists(dst):
        idx = build_index()
        src = idx.get(no, {}).get("audio_src", "")
        if not src or not os.path.exists(src):
            return ""
        os.makedirs(AUDIO_OUT_DIR, exist_ok=True)
        shutil.copyfile(src, dst)
    return RAW + "/content/hymn-audio/" + no + ".mp3"


def card_html_for_guid(guid, date):
    if date < CARD_START:
        return ""
    if not re.fullmatch(r"devotion-(am|pm)-\d{4}-\d{2}-\d{2}", guid or ""):
        return ""
    entry = pick_for_date(date)
    if not entry:
        return ""
    idx = build_index()
    h = idx.get(entry["no"])
    if not h:
        return ""
    audio_url = ensure_audio(entry["no"])
    if not audio_url:
        return ""
    sheet_html = _render_sheet(h["sheet_path"])
    links = []
    if entry.get("youtube"):
        links.append('<a href="{}">在 YouTube 观看这首歌</a>'.format(esc(entry["youtube"])))
    if entry.get("spotify"):
        links.append('<a href="{}">在 Spotify 收听</a>'.format(esc(entry["spotify"])))
    elif entry.get("hyperfollow"):
        links.append('<a href="{}">在各平台收听（Spotify 等）</a>'.format(esc(entry["hyperfollow"])))
    links.append('<a href="{}">更多赞美诗（主页听歌区）</a>'.format(MORE_HYMNS_URL))
    links.append('<a href="{}">Spotify 艺人页</a>'.format(SPOTIFY_ARTIST))
    meta_line = "｜".join(x for x in [entry.get("key", ""), entry.get("tempo", ""), entry.get("meter", "")] if x)
    return (
        '<style>' + CARD_CSS + '</style>\n'
        '<section class="hymn-card">\n'
        '  <h2>今日诗歌</h2>\n'
        '  <p class="song">《' + esc(entry["title"]) + '》（原创赞美诗 ' + esc(entry["no"]) + '）</p>\n'
        + ('  <p class="basis">' + esc(meta_line) + '</p>\n' if meta_line else '')
        + '  <audio controls preload="none" src="' + esc(audio_url) + '"></audio>\n'
        '  <p class="meta">音频：<a href="' + esc(audio_url) + '">发行版直接收听 / 下载</a></p>\n'
        '  <div class="sheet">\n' + sheet_html + '\n  </div>\n'
        '  <p class="hymn-links">' + ' · '.join(links) + '</p>\n'
        '  <p class="basis">配歌依据：' + esc(entry["basis"]) + '。词曲：Guangyi Zhao。谱面为发行版对版乐谱（简谱＋和弦），唱词随谱呈现。</p>\n'
        '</section>\n'
    )


if __name__ == "__main__":
    import sys
    idx = build_index(force=True)
    pool = [h for h in idx.values() if h["audio_src"]]
    print("候选池（有谱）:", len(idx), "｜其中有发行版音频:", len(pool))
    print("有 YouTube:", sum(1 for h in idx.values() if h["youtube"]),
          "｜有 Spotify 直链:", sum(1 for h in idx.values() if h["spotify"]),
          "｜有 HyperFollow:", sum(1 for h in idx.values() if h["hyperfollow"]),
          "｜有经文依据:", sum(1 for h in idx.values() if h["scripture"]))
    if len(sys.argv) > 1:
        e = pick_for_date(sys.argv[1])
        print("配歌:", e)
