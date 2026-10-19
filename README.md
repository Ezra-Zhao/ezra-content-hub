# Ezra 内容中央枢纽（ezra-content-hub）

Guangyi Zhao 全部音频、视频与文字的**集中档案**。各平台限制多、政策会变，这里是自有阵地：所有成品先回到这个仓存档，再分发出去。

- 展示页（手机优先，一个链接看全貌）：GitHub Pages，见 `docs/` 目录构建的站点。
- 发布顺序（2026-10-16 定版）：**GitHub → X → 其他平台**（Spotify / Apple Podcasts / YouTube 等）。
- 内容分档：早晚双版八档（早间新闻、晚间新闻、早间股市、晚间股市、长寿前沿、硅谷科技、移民政策、湾区福利）+ 每日灵修（早间/睡前）+ 讲道《瓦器分享》+ 讲书《小憩片刻》；文章区按系列归档，首个系列为「讲道集」。

## 目录说明

```
content-hub/
├── README.md          本说明
├── index.json         总索引（节目→集数 + articles 文章结构；docs/index.json 为同份副本）
├── docs/              GitHub Pages 站点（纯静态，读 index.json 渲染）
│   └── articles/      构建生成的文章阅读页（勿手改，由 scripts/build_articles.py 生成）
├── content/           音频档案，按节目分目录
│   └── <节目>/<日期>/
│       ├── audio.mp3  该集音频成品
│       └── index.md   该集档案页（标题/日期/经文或主题/简介/平台链接）
├── articles/          文章档案，按系列分目录（源文件）
│   └── <系列>/<日期>-<slug>.md   每篇一个 md，文件头带 frontmatter（标题/日期/系列/作者/经文）
└── scripts/
    └── build_articles.py  文章构建：md → 阅读页 HTML + 重建索引 articles 结构
```

视频本体不进仓（体积大），在索引中以 `video_url` 字段预留，指向视频平台链接。

## 入库规矩

1. 成品先入库：音频拷入 `content/<节目>/<日期>/audio.mp3`，同目录写 `index.md`。
2. 同步更新根目录 `index.json` 与 `docs/index.json`（两份保持一致），展示页自动上架。
3. 分发到 X 与其他平台后，把各集的平台链接回填到该集 `index.md` 与索引的 `links` 字段。

## 文章入库流程

文章先出、有就上、成系列往这里堆（2026-10-16 定）。步骤：

1. **先过确认门**：本仓是公开仓。讲章、书稿等文字入库前必须已获 Ezra 本人确认可公开发布；标有「内部草稿 / 待确认 / 待终审」的稿件一律不入库。私人材料（证明信、收据、证件扫描等）永不入库。
2. 把成稿 md 放进 `articles/<系列>/`，文件名用 `<日期>-<英文slug>.md`；文件头写 frontmatter：

   ```
   ---
   title: 文章标题
   date: 2026-10-16
   series: sermons
   author: Guangyi Zhao
   scripture: 核心经文（可省略）
   ---
   ```

3. 跑构建：`python3 scripts/build_articles.py`——自动生成 `docs/articles/` 阅读页，并重建根目录与 `docs/` 两份 `index.json` 的 articles 结构；展示页的「文章」板块随即上架。
4. `git add -A && git commit && git push`，等 Pages 构建完成后打开线上文章页核验一遍再算入库完成。

## 版权

© 2026 Guangyi Zhao 文稿与音频版权所有。
