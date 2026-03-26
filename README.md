# WeChat Article Writer

微信公众号文章流水线：改稿、排版、配图、质检、审核、上传草稿。

这个仓库公开版只保留可分享的核心代码和示例配置，不包含任何真实凭证、运行产物、草稿内容或图片缓存。

文档入口：

- [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- [BEGINNER_GUIDE_ZH.md](./BEGINNER_GUIDE_ZH.md)
- [README_SECURITY.md](./README_SECURITY.md)

## Features

- Markdown 转公众号 HTML
- 一节一图
- 微信 CDN 图片上传
- 上传前强预检
- reviewer 报告门禁
- IP 白名单错误识别
- 新建草稿或更新已有草稿

## Project Structure

```text
.
├── data
│   ├── unsplash_config.example.json
│   ├── wechat_config.example.json
│   └── wechat_profiles
│       └── profile.example.json
├── scripts
│   ├── config.py
│   ├── md_to_html.py
│   ├── unsplash_image_fetcher.py
│   ├── wechat_article_pipeline.py
│   ├── wechat_config.py
│   ├── wechat_profile_manager.py
│   ├── wechat_publisher.py
│   ├── wechat_quality_guard.py
│   └── wechat_reviewer.py
├── templates
│   ├── company_ending.html
│   └── html_styles.html
├── .gitignore
├── README.md
├── README_SECURITY.md
└── requirements.txt
```

## Setup

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 复制示例配置并填写你自己的值

- `data/wechat_config.example.json`
- `data/unsplash_config.example.json`
- `data/wechat_profiles/profile.example.json`

建议本地复制为：

- `data/wechat_config.json`
- `data/unsplash_config.json`
- `data/wechat_profiles/profile.json`

这些真实配置默认被 `.gitignore` 忽略，不会进入仓库。

## Recommended Usage

只预检，不上传：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --no-upload
```

新建公众号草稿：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --cover-image "<cover.jpg>"
```

更新已有草稿：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --media-id "<draft_media_id>"
```

如果你传了人工 reviewer 报告：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --review-report "<review.json>" --media-id "<draft_media_id>"
```

如果没传，流水线会自动生成：

```text
data/output/<article>.auto_reviewer.json
```

## Pipeline Stages

1. Markdown 预检
2. HTML 转换
3. 小节配图并上传到微信 CDN
4. HTML 预检
5. 生成 reviewer 报告
6. reviewer 通过后才允许上传
7. 新建或更新公众号草稿

## Security

- 不要提交 `data/*.json` 真实配置
- 不要提交 `data/output/` 运行产物
- 不要提交 `data/images/` 图片缓存
- 不要提交你的草稿内容、媒体 ID、access token 或 mmbiz 图链

发布前建议读一遍 [README_SECURITY.md](./README_SECURITY.md)。
