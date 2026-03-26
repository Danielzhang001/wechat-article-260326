# 小白教程：从零到跑通

这份教程按“截图式”写法来写。

意思是：

- 每一步都告诉你“点哪里”
- 每一步都告诉你“看到什么算正常”
- 每一步都告诉你“如果不对，先查什么”

如果你以前没配过公众号 API，也可以照着做。

---

## 你最终要做到什么

跑通后，你应该能做到这件事：

把一篇 Markdown 文章交给脚本，然后它会：

1. 自动排版
2. 自动配图
3. 自动质检
4. 自动生成 reviewer 报告
5. 上传到微信公众号草稿箱

---

## 第 0 步：你先准备好这 4 样东西

开始前，先确认你手里有：

1. 一台能联网的电脑
2. Python 3.10+
3. 微信公众号的 `AppID` 和 `AppSecret`
4. Unsplash 的 `Access Key`

如果你现在没有第 3、4 项，也没关系，后面我会带你一步一步去拿。

---

## 第 1 步：打开 GitHub 仓库

打开这个地址：

[https://github.com/Danielzhang001/wechat-article-260326](https://github.com/Danielzhang001/wechat-article-260326)

### 你应该看到什么

页面里至少能看到这些文件：

- `README.md`
- `SETUP_GUIDE.md`
- `scripts/`
- `data/`
- `templates/`

### 如果你没看到

先检查：

- 你是不是打开错仓库了
- 你是不是没登录 GitHub
- 仓库是不是还没刷新到最新

---

## 第 2 步：把仓库下载到本地

### 方法 1：最简单，直接下载 ZIP

点击：

`Code -> Download ZIP`

下载后解压到你容易找到的位置，比如：

`D:\wechat-article-260326`

### 方法 2：如果你会 git

```bash
git clone https://github.com/Danielzhang001/wechat-article-260326.git
```

### 你应该看到什么

本地文件夹里能看到：

- `README.md`
- `requirements.txt`
- `scripts`
- `data`

---

## 第 3 步：安装 Python

如果你电脑里已经有 Python，可以先跳过。

### 怎么看自己有没有 Python

打开终端，输入：

```bash
python --version
```

### 正常情况

你会看到类似：

```bash
Python 3.11.8
```

### 如果提示找不到

去 Python 官网安装：

[https://www.python.org/downloads/](https://www.python.org/downloads/)

安装时记得勾上：

`Add Python to PATH`

---

## 第 4 步：安装项目依赖

进入仓库目录，然后运行：

```bash
pip install -r requirements.txt
```

### 你应该看到什么

终端里会开始安装依赖，最后通常会看到：

```bash
Successfully installed ...
```

### 如果失败

先检查 3 件事：

1. Python 是否安装成功
2. 你的网络是否正常
3. 你是不是在仓库根目录运行的命令

---

## 第 5 步：拿到公众号 AppID 和 AppSecret

打开：

[https://mp.weixin.qq.com/](https://mp.weixin.qq.com/)

登录你的公众号后台。

### 进入路径

进入：

`设置与开发 -> 基本配置`

### 你要找什么

你要找到：

- `AppID`
- `AppSecret`

### 你应该看到什么

页面上会有开发信息区域。

如果 AppSecret 没显示，你可能需要：

- 管理员扫码
- 重置或查看开发者密钥

### 这一步常见误区

- 这里用的是公众号的 `AppID`，不是小程序的
- 当前项目里，所谓“公众号 ID”就是这个 `AppID`

---

## 第 6 步：配置公众号 API 文件

在仓库里找到：

`data/wechat_config.example.json`

复制一份，改名为：

`data/wechat_config.json`

### 文件内容这样填

```json
{
  "appid": "你的公众号AppID",
  "appsecret": "你的公众号AppSecret",
  "author": "你的公众号作者名",
  "images_dir": "data/images"
}
```

### 每个字段是什么意思

- `appid`：公众号 AppID
- `appsecret`：公众号 AppSecret
- `author`：默认作者名
- `images_dir`：图片目录，先保持默认就行

### 你应该看到什么

保存后，这个文件路径存在：

`data/wechat_config.json`

---

## 第 7 步：检查公众号配置有没有写对

运行：

```bash
python scripts/wechat_config.py status
```

### 正常情况

你会看到类似：

```bash
AppID:     wx1234****cdef
Status:    Configured
AppSecret: ****
Author:    你的作者名
```

### 如果不正常

先检查：

1. `data/wechat_config.json` 文件名有没有写错
2. JSON 有没有少逗号、少引号
3. `appid` 和 `appsecret` 有没有复制错

---

## 第 8 步：拿 Unsplash Access Key

打开：

[https://unsplash.com/developers](https://unsplash.com/developers)

### 操作顺序

1. 注册账号
2. 创建一个应用
3. 进入应用详情
4. 复制 `Access Key`

### 你应该看到什么

后台里会有一组 API Key，其中你现在要用的是：

- `Access Key`

---

## 第 9 步：配置 Unsplash

在仓库里找到：

`data/unsplash_config.example.json`

复制一份，改名为：

`data/unsplash_config.json`

填成这样：

```json
{
  "access_key": "你的UnsplashAccessKey"
}
```

---

## 第 10 步：配置微信 IP 白名单

这一步非常关键。

很多人前面都配对了，最后还是上传失败，原因就是没配白名单。

### 去哪里配

回到公众号后台：

`设置与开发 -> 基本配置 -> IP 白名单`

### 你要做什么

把当前电脑的公网出口 IP 加进去。

### 如果你不知道自己公网 IP 是什么

其实可以先直接跑一次上传命令。

如果失败是白名单问题，当前项目会尽量打印：

- 白名单错误类型
- 当前公网 IP
- 修复提示

常见报错：

- `40164`
- `not in whitelist`
- `invalid ip`

### 你应该看到什么

白名单页面里能看到你新增的 IP。

---

## 第 11 步：准备一篇测试文章

你可以先在仓库目录下新建一个文件，比如：

`test_article.md`

内容先简单一点：

```markdown
# 这是一篇测试文章

这是一段开头。

### 第一节

这是第一节内容。

### 第二节

这是第二节内容。

### 第三节

这是第三节内容。
```

### 为什么要这样写

因为这套流水线是按小节 `###` 去配图的。

如果你没有小节，后面你会觉得“为什么没图”。

---

## 第 12 步：先只跑预检，不上传

运行：

```bash
python scripts/wechat_article_pipeline.py "test_article.md" --no-upload
```

### 正常情况你会看到什么

你会看到类似：

- 获取 access token
- 上传 section 图片
- 预检通过
- 输出 HTML 路径
- 输出 report 路径
- 输出 reviewer 路径

大致会像这样：

```bash
Preflight passed. HTML: ...
Report: ...
Reviewer: ...
```

### 这一步成功代表什么

说明这些已经通了：

- 微信 API 可访问
- Unsplash API 可访问
- 配图逻辑可运行
- 预检器可运行
- reviewer 脚本可运行

### 如果这一步失败

优先看终端最后几行。

常见原因：

1. 微信配置错
2. Unsplash key 没配
3. 白名单没配
4. 文章结构不满足要求

---

## 第 13 步：准备一张封面图

新建草稿时，需要一张封面图。

你可以先自己准备一个本地图片，比如：

`cover.jpg`

建议：

- JPG 或 PNG
- 尺寸正常
- 不要太大

---

## 第 14 步：正式上传到公众号草稿箱

运行：

```bash
python scripts/wechat_article_pipeline.py "test_article.md" --cover-image "cover.jpg"
```

### 正常情况你会看到什么

终端会输出：

- 图片上传成功
- 封面上传成功
- 保存草稿成功
- Draft Media ID

大致像这样：

```bash
Successfully saved as draft!
Draft Media ID: xxxxxxxxx
```

### 这一步成功后去哪里看

打开公众号后台：

`内容与互动 -> 草稿箱`

你应该能看到刚上传的测试文章。

---

## 第 15 步：如果你已经有草稿，怎么更新

如果你已经有一个草稿 `media_id`，可以直接更新：

```bash
python scripts/wechat_article_pipeline.py "test_article.md" --media-id "你的草稿media_id"
```

### 你应该看到什么

终端会输出类似：

```bash
Draft updated: 你的media_id
```

---

## 第 16 步：如果你有多个公众号怎么办

建议用 profile 管理。

### 新建 profile

```bash
python scripts/wechat_profile_manager.py new \
  --name account-a \
  --appid wx1234567890abcdef \
  --appsecret xxxxxxxxx \
  --author "账号A作者名" \
  --activate
```

### 查看 profile

```bash
python scripts/wechat_profile_manager.py list
```

### 切换 profile

```bash
python scripts/wechat_profile_manager.py use --name account-a
```

---

## 你跑通后，应该能在本地看到什么

跑完之后，通常会生成：

- `data/output/*.markdown_preflight.json`
- `data/output/*.pipeline_report.json`
- `data/output/*.auto_reviewer.json`
- `data/output/*.wechat.html`

这些是正常的运行产物。

---

## 最常见的报错，先看这里

### 报错 1：找不到 Unsplash key

说明：

`data/unsplash_config.json` 没配好。

### 报错 2：40164 / not in whitelist

说明：

公众号 IP 白名单没配好。

### 报错 3：标题缺失

说明：

你的 Markdown 没有：

```markdown
# 标题
```

### 报错 4：Publishing new draft requires --cover-image

说明：

你在“新建草稿”，但没传封面图。

### 报错 5：Reviewer did not pass

说明：

预检报告里还有硬问题，不能上传。

---

## 你第一次最推荐跑的命令

如果你是第一次配，直接按这个顺序：

```bash
python scripts/wechat_config.py status
python scripts/wechat_article_pipeline.py "test_article.md" --no-upload
python scripts/wechat_article_pipeline.py "test_article.md" --cover-image "cover.jpg"
```

---

## 这一版要特别知道的一件事

当前公开版默认配图方案是：

- **Unsplash 搜图**

不是：

- AI 生图模型

所以你现在只需要：

1. 微信 API
2. Unsplash API

就能跑通。

如果以后你要我继续扩展，我下一步可以给你补：

- 真截图版教程
- OpenAI 生图接入版
- 一键初始化脚本
