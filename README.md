# Ezra 内容中央枢纽（ezra-content-hub）

Guangyi Zhao 全部音频、视频与文字的**集中档案**。各平台限制多、政策会变，这里是自有阵地：所有成品先回到这个仓存档，再分发出去。

- 展示页（手机优先，一个链接看全貌）：GitHub Pages，见 `docs/` 目录构建的站点。
- 发布顺序（2026-10-16 定版）：**GitHub → X → 其他平台**（Spotify / Apple Podcasts / YouTube 等）。
- 内容分档：早晚双版六档（早间新闻、晚间新闻、早间股市、晚间股市、长寿前沿、硅谷科技、移民政策、湾区福利）+ 每日灵修（早间/睡前）+ 讲道《瓦器分享》+ 讲书《小憩片刻》。

## 目录说明

```
content-hub/
├── README.md          本说明
├── index.json         总索引（节目→集数：日期/标题/经文/主题/音频路径/时长/视频链接预留位）
├── docs/              GitHub Pages 站点（纯静态，读 index.json 渲染；docs/index.json 为同份索引副本）
└── content/           按节目分目录
    └── <节目>/<日期>/
        ├── audio.mp3  该集音频成品
        └── index.md   该集档案页（标题/日期/经文或主题/简介/平台链接）
```

视频本体不进仓（体积大），在索引中以 `video_url` 字段预留，指向视频平台链接。

## 入库规矩

1. 成品先入库：音频拷入 `content/<节目>/<日期>/audio.mp3`，同目录写 `index.md`。
2. 同步更新根目录 `index.json` 与 `docs/index.json`（两份保持一致），展示页自动上架。
3. 分发到 X 与其他平台后，把各集的平台链接回填到该集 `index.md` 与索引的 `links` 字段。

## 版权

© 2026 Guangyi Zhao 文稿与音频版权所有。
