# Setup Guide

这份文档说明如何配置并使用 `wechat-article-260326` 公开仓库。

## 先说结论

当前这套公开版默认需要配置的只有两类 API：

1. 微信公众号 API
2. Unsplash API

当前仓库默认的“配图”来源是 **Unsplash**，不是 AI 生图模型。

也就是说：

- 现在可以直接配置并跑通公众号改稿、排版、配图、上传
- 现在**不需要**配置额外的生图模型才能使用
- 如果你想把 Unsplash 改成 AI 生图，当前代码里有明确接入点，但还没有内置 OpenAI / Replicate / Stability / Midjourney 之类的 provider

## 1. 环境准备

### Python

建议 Python 3.10 及以上。

安装依赖：

```bash
pip install -r requirements.txt
```

## 2. 微信公众号 API 配置

### 你需要什么

去微信公众号后台拿到：

- `AppID`
- `AppSecret`

入口通常是：

`微信公众号后台 -> 设置与开发 -> 基本配置`

### 当前代码里使用哪个“公众号 ID”

当前仓库里，真正集成的是：

- `appid`
- `appsecret`

也就是说，这里说的“公众号 ID”，在当前代码里就是 `AppID`。

代码使用位置：

- `scripts/wechat_config.py`
- `scripts/wechat_publisher.py`
- `scripts/wechat_profile_manager.py`

### 配置文件

新建：

`data/wechat_config.json`

内容示例：

```json
{
  "appid": "wx1234567890abcdef",
  "appsecret": "your_wechat_app_secret",
  "author": "你的公众号作者名",
  "images_dir": "data/images"
}
```

字段说明：

- `appid`：公众号 AppID
- `appsecret`：公众号 AppSecret
- `author`：默认作者名，上传草稿时会写入
- `images_dir`：本地图片目录

### 检查配置

```bash
python scripts/wechat_config.py status
```

### 交互式配置

```bash
python scripts/wechat_config.py setup
```

## 3. 多公众号配置

如果你不止一个公众号，建议不要反复手改 `data/wechat_config.json`，而是使用 profile。

### 新建一个公众号 profile

```bash
python scripts/wechat_profile_manager.py new \
  --name my-account \
  --appid wx1234567890abcdef \
  --appsecret your_wechat_app_secret \
  --author "你的作者名" \
  --activate
```

### 查看已保存 profile

```bash
python scripts/wechat_profile_manager.py list
```

### 切换 profile

```bash
python scripts/wechat_profile_manager.py use --name my-account
```

### 切换后顺手验 token

```bash
python scripts/wechat_profile_manager.py select --verify
```

profile 文件默认保存在：

`data/wechat_profiles/*.json`

## 4. 微信 IP 白名单配置

这是最容易卡住的地方。

### 为什么要配

微信公众号 API 只允许白名单 IP 调用关键接口。如果你的机器公网 IP 不在白名单，上传会失败，常见报错是：

- `40164`
- `not in whitelist`
- `invalid ip`

### 去哪里配

进入：

`微信公众号后台 -> 设置与开发 -> 基本配置 -> IP 白名单`

把你当前机器的出口公网 IP 加进去。

### 这套代码怎么帮你定位问题

当前仓库里，`scripts/wechat_publisher.py` 已经做了白名单错误识别。

当上传失败且属于白名单问题时，它会尽量输出：

- 错误类型
- 错误信息
- 当前公网 IP
- 修复提示

也就是说，跑一次上传命令，如果因为白名单失败，终端里会直接告诉你该去哪里改。

## 5. Unsplash API 配置

### 你需要什么

去 [Unsplash Developers](https://unsplash.com/developers) 创建应用，然后拿到：

- `Access Key`

### 配置文件

新建：

`data/unsplash_config.json`

内容示例：

```json
{
  "access_key": "your_unsplash_access_key"
}
```

### 当前代码怎么用它

当前配图逻辑在：

- `scripts/unsplash_image_fetcher.py`
- `scripts/wechat_article_pipeline.py`

流程是：

1. 文章分小节
2. 每个小节推断关键词
3. 去 Unsplash 搜图
4. 下载图片
5. 上传到微信 CDN
6. 插入正文

## 6. 生图 API / 生图模型说明

### 当前公开版的真实状态

当前公开仓库**没有内置 AI 生图 provider**。

也就是说，这一版没有直接集成：

- OpenAI Images
- Replicate
- Stability
- Midjourney
- 即梦
- 可灵
- OpenRouter 图像模型

当前默认配图方案只有：

- Unsplash 搜图

### 你现在要不要配置“生图 API”

如果你只是想把这套工具跑起来：

- **不用配**

如果你想让它改成“AI 生成图片”而不是“Unsplash 搜图”：

- **当前版本还要继续开发**

### 如果以后要接 AI 生图，代码接入点在哪里

主要接入点在：

`scripts/wechat_article_pipeline.py`

具体是这里的逻辑：

- `insert_section_images(...)`
- `infer_query(...)`

现在它做的是：

- 根据小节内容得到关键词
- 调用 `UnsplashImageFetcher`

如果以后要换成 AI 生图，思路是：

1. 新增一个 image generator 类，比如 `ImageGenProvider`
2. 输入：标题、小节标题、小节正文、风格
3. 输出：本地图片文件路径
4. 然后复用现有 `publisher._upload_image(...)` 上传到微信

### 如果你一定要在这个项目里接“生图模型”，建议新增的配置文件格式

例如新增：

`data/imagegen_config.json`

示例：

```json
{
  "provider": "openai",
  "api_key": "your_image_api_key",
  "model": "gpt-image-1",
  "size": "1536x1024",
  "quality": "high",
  "style": "editorial documentary"
}
```

但注意：

- 这只是建议的配置结构
- 当前公开仓库还**没有消费这个文件**

## 7. 推荐运行方式

### 只做预检，不上传

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --no-upload
```

这一步会做：

- Markdown 预检
- HTML 转换
- 小节配图
- HTML 预检
- 自动 reviewer 报告

### 新建公众号草稿

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --cover-image "<cover.jpg>"
```

### 更新已有草稿

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --media-id "<draft_media_id>"
```

## 8. reviewer 报告机制

当前仓库已经加入 reviewer 门禁。

上传前需要 reviewer pass。

如果你不手动传：

```bash
--review-report <review.json>
```

流水线会自动生成：

`data/output/<article>.auto_reviewer.json`

脚本位置：

`scripts/wechat_reviewer.py`

## 9. 配置完成后的最小验收流程

建议按这个顺序自测：

1. 配好 `data/wechat_config.json`
2. 配好 `data/unsplash_config.json`
3. 去公众号后台把公网 IP 加白名单
4. 跑：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --no-upload
```

5. 再跑：

```bash
python scripts/wechat_article_pipeline.py "<article.md>" --cover-image "<cover.jpg>"
```

如果这两步都通，说明你的：

- 微信配置
- Unsplash 配置
- 白名单
- reviewer gate
- 上传流程

都已经跑通。

## 10. 安全建议

- `data/wechat_config.json` 不要提交到 GitHub
- `data/unsplash_config.json` 不要提交到 GitHub
- `data/output/` 不要提交到 GitHub
- `data/images/` 不要提交到 GitHub
- 不要把公众号草稿 media_id、mmbiz 图链、token 日志上传到公开仓库

可以结合 `README_SECURITY.md` 一起看。
