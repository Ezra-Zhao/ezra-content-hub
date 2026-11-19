#!/usr/bin/env python3
"""Build the 《小憩片刻》 (book-talk) podcast RSS feeds, one per language.

Mirrors build_sermons_feed.py: episodes are read from
content/<series>/<ep>/index.md + audio.mp3, enclosures point at
raw.githubusercontent.com URLs of the committed audio files.

Series (Ezra 2026-11-19 定版六语）:
  jiangshu     中文（主 feed)      -> docs/podcast/jiangshu.xml
  jiangshu-en  English            -> docs/podcast/jiangshu-en.xml
  jiangshu-es  Español            -> docs/podcast/jiangshu-es.xml
  jiangshu-vi  Tiếng Việt         -> docs/podcast/jiangshu-vi.xml
  jiangshu-pt  Português          -> docs/podcast/jiangshu-pt.xml
  jiangshu-ru  Русский            -> docs/podcast/jiangshu-ru.xml

index.md episode format (one parser for all languages):
  # <episode title>
  Date: YYYY-MM-DD
  Duration: M:SS
  Summary: <one-paragraph show notes>
"""
import os
import re
import html
from datetime import datetime, time, timedelta, timezone
from email.utils import format_datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = "https://raw.githubusercontent.com/Ezra-Zhao/ezra-content-hub/main"
PAGES = "https://ezrazhao.com"
LOCAL = ZoneInfo("America/Los_Angeles")

AUTHOR = "Guangyi Zhao"
EMAIL = "ezra777.zhao@gmail.com"

SERIES = {
    "jiangshu": {
        "fname": "jiangshu.xml",
        "lang": "zh-CN",
        "title": "小憩片刻｜Guangyi Zhao 讲书",
        "desc": ("小憩片刻：Guangyi Zhao 的讲书节目——每集用八到十分钟讲清一本书的主线与取舍，"
                 "五大领域轮值：商业、科技、健康、神学、历史。在版书只做解读，经典选读只用公版书。"
                 "关键词：讲书、读书、商业、科技、历史。全部节目：https://ezrazhao.com/ "
                 "同组节目：《每日灵修》《瓦器分享》也在本枢纽更新。"),
        "keywords": "讲书,读书,商业,科技,健康,神学,历史,个人成长",
        "cover": "cover-jiangshu.png",
    },
    "jiangshu-en": {
        "fname": "jiangshu-en.xml",
        "lang": "en",
        "title": "A Moment's Rest | Book Talks by Guangyi Zhao",
        "desc": ("A Moment's Rest: Guangyi Zhao talks books — one book per episode, eight to ten minutes, "
                 "rotating through business, technology, health, theology and history. Modern books are "
                 "discussed and interpreted; full readings only from public-domain classics. "
                 "All shows: https://ezrazhao.com/"),
        "keywords": "books,book talk,business,technology,history,personal growth",
        "cover": "cover-jiangshu.png",
    },
    "jiangshu-es": {
        "fname": "jiangshu-es.xml",
        "lang": "es",
        "title": "Un momento de descanso | Libros con Guangyi Zhao",
        "desc": ("Un momento de descanso: Guangyi Zhao habla de libros — un libro por episodio, de ocho a diez "
                 "minutos, en rotación por negocios, tecnología, salud, teología e historia. Los libros "
                 "modernos se interpretan; las lecturas completas son solo de clásicos de dominio público. "
                 "Todos los programas: https://ezrazhao.com/"),
        "keywords": "libros,lectura,negocios,tecnología,historia,crecimiento personal",
        "cover": "cover-jiangshu.png",
    },
    "jiangshu-vi": {
        "fname": "jiangshu-vi.xml",
        "lang": "vi",
        "title": "Khoảnh Khắc Nghỉ Ngơi | Giới thiệu sách cùng Guangyi Zhao",
        "desc": ("Khoảnh Khắc Nghỉ Ngơi: Guangyi Zhao giới thiệu sách — mỗi tập một cuốn sách, tám đến mười "
                 "phút, luân phiên qua kinh doanh, công nghệ, sức khỏe, thần học và lịch sử. Sách hiện đại "
                 "chỉ được diễn giải; đọc toàn văn chỉ với tác phẩm kinh điển thuộc phạm vi công cộng. "
                 "Tất cả chương trình: https://ezrazhao.com/"),
        "keywords": "sách,giới thiệu sách,kinh doanh,công nghệ,lịch sử,phát triển bản thân",
        "cover": "cover-jiangshu.png",
    },
    "jiangshu-pt": {
        "fname": "jiangshu-pt.xml",
        "lang": "pt",
        "title": "Um Momento de Descanso | Livros com Guangyi Zhao",
        "desc": ("Um Momento de Descanso: Guangyi Zhao fala de livros — um livro por episódio, de oito a dez "
                 "minutos, em rotação por negócios, tecnologia, saúde, teologia e história. Livros modernos "
                 "são interpretados; leituras completas apenas de clássicos de domínio público. "
                 "Todos os programas: https://ezrazhao.com/"),
        "keywords": "livros,leitura,negócios,tecnologia,história,crescimento pessoal",
        "cover": "cover-jiangshu.png",
    },
    "jiangshu-ru": {
        "fname": "jiangshu-ru.xml",
        "lang": "ru",
        "title": "Минутка отдыха | Книги с Гуанъи Чжао",
        "desc": ("Минутка отдыха: Гуанъи Чжао рассказывает о книгах — одна книга в выпуске, восемь–десять "
                 "минут, ротация по темам: бизнес, технологии, здоровье, богословие и история. Современные "
                 "книги только интерпретируются; полные чтения — только классика общественного достояния. "
                 "Все программы: https://ezrazhao.com/"),
        "keywords": "книги,бизнес,технологии,история,личностный рост",
        "cover": "cover-jiangshu.png",
    },
}


def parse_episode(series, ep_dir):
    d = os.path.join(ROOT, "content", series, ep_dir)
    md_path = os.path.join(d, "index.md")
    au_path = os.path.join(d, "audio.mp3")
    if not (os.path.exists(md_path) and os.path.exists(au_path)):
        return None
    text = open(md_path, encoding="utf-8").read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else ep_dir
    date_m = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    date_s = date_m.group(1) if date_m else "2026-11-19"
    dur = re.search(r"^Duration:\s*([0-9:]+)", text, re.M)
    summ = re.search(r"^Summary:\s*(.+)$", text, re.M)
    pub = datetime.combine(
        datetime.strptime(date_s, "%Y-%m-%d").date(), time(20, 0), tzinfo=LOCAL
    )
    return {
        "title": title,
        "desc": summ.group(1).strip() if summ else title,
        "pub": pub,
        "url": RAW + "/content/" + series + "/" + ep_dir + "/audio.mp3",
        "size": os.path.getsize(au_path),
        "guid": series + "-" + ep_dir,
        "duration": dur.group(1) if dur else "",
    }


def build(series, cfg):
    base = os.path.join(ROOT, "content", series)
    eps = []
    if os.path.isdir(base):
        for ep_dir in sorted(os.listdir(base)):
            ep = parse_episode(series, ep_dir)
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
    cover_url = PAGES + "/podcast/" + cfg["cover"]
    feed = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\" "
        "xmlns:atom=\"http://www.w3.org/2005/Atom\">\n"
        "  <channel>\n"
        "    <title>" + html.escape(cfg["title"]) + "</title>\n"
        "    <link>" + PAGES + "/</link>\n"
        "    <atom:link href=\"" + PAGES + "/podcast/" + cfg["fname"]
        + "\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        "    <description>" + html.escape(cfg["desc"]) + "</description>\n"
        "    <language>" + cfg["lang"] + "</language>\n"
        "    <itunes:author>" + AUTHOR + "</itunes:author>\n"
        "    <itunes:owner>\n"
        "      <itunes:name>" + AUTHOR + "</itunes:name>\n"
        "      <itunes:email>" + EMAIL + "</itunes:email>\n"
        "    </itunes:owner>\n"
        "    <itunes:image href=\"" + cover_url + "\"/>\n"
        "    <image>\n"
        "      <url>" + cover_url + "</url>\n"
        "      <title>" + html.escape(cfg["title"]) + "</title>\n"
        "      <link>" + PAGES + "/</link>\n"
        "    </image>\n"
        "    <itunes:category text=\"Education\"/>\n"
        "    <itunes:keywords>" + html.escape(cfg["keywords"]) + "</itunes:keywords>\n"
        "    <itunes:explicit>false</itunes:explicit>\n"
        + ("\n".join(items) + "\n" if items else "")
        + "  </channel>\n</rss>\n"
    )
    out = os.path.join(ROOT, "docs", "podcast", cfg["fname"])
    with open(out, "w", encoding="utf-8") as f:
        f.write(feed)
    return len(eps), out


def main():
    for series, cfg in SERIES.items():
        n, out = build(series, cfg)
        print(f"{series}: {n} episodes -> {out}")


if __name__ == "__main__":
    main()
