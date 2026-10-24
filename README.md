# LiKui · 个人主页

> **把技术做成系统，把思考沉淀成作品。**

这是 [LiKui](https://likui.info/) 的个人主页源码仓库。网站围绕个人介绍、数字空间、开源项目、技术兴趣和书影音记录展开，采用轻量的原生前端技术构建，并通过 GitHub Actions 自动维护部分数据。

<p align="center">
  <a href="https://likui.info/"><strong>访问在线主页 ↗</strong></a>
  &nbsp;·&nbsp;
  <a href="https://about.likui.info/">关于我</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/ilikui">GitHub</a>
</p>

---

## 目录

- [项目简介](#项目简介)
- [站点模块](#站点模块)
- [技术方案](#技术方案)
- [仓库结构](#仓库结构)
- [书影音数据规范](#书影音数据规范)
- [自动化工作流](#自动化工作流)
- [本地运行](#本地运行)
- [部署说明](#部署说明)
- [维护与排障](#维护与排障)
- [致谢](#致谢)

## 项目简介

个人主页不仅是个人名片，也是连接技术实践、阅读记录和知识管理的入口。设计目标：

- **清晰导航**：集中展示个人空间、项目与技术方向。
- **轻量易维护**：以 HTML、CSS、JavaScript 和 JSON 为主，不依赖前端框架构建。
- **响应式体验**：适配桌面与移动端，并支持主题切换。
- **数据与页面分离**：书籍、电影、音乐记录由 JSON 文件提供，展示层与数据源相互独立。
- **自动化更新**：通过 GitHub Actions 同步豆瓣收藏、备份数据，并生成 GitHub 贡献图动画。

## 站点模块

| 模块 | 内容 |
| --- | --- |
| 个人介绍 | 简介、关注领域、站内导航与联系入口 |
| 我的空间 | 笔记、博客、RSS 等个人数字空间入口 |
| 项目与记录 | 开源项目、个人作品及相关记录 |
| 技术栈 | 技术兴趣与相关技术站点链接 |
| 书影音 | 豆瓣书籍、电影、音乐收藏，支持按类型和状态浏览 |
| GitHub 贡献图 | 由自动化工作流生成的贡献图动画素材 |

## 技术方案

| 层次 | 技术 / 工具 | 用途 |
| --- | --- | --- |
| 页面结构 | HTML5 | 内容与语义结构 |
| 页面样式 | CSS3 | 布局、响应式样式与主题 |
| 页面交互 | 原生 JavaScript | 导航、筛选和交互行为 |
| 数据 | JSON | 书影音记录与页面数据 |
| 自动化 | GitHub Actions | 定时同步、手动触发、提交数据 |
| 豆瓣同步 | [doumark-action](https://github.com/lizheming/doumark-action) | 导出书籍、电影和音乐记录 |
| 贡献图 | [snk](https://github.com/Platane/snk) | 生成 GitHub 贡献图动画 |

本项目面向静态网站托管。无需安装 Node.js 或额外的前端构建工具；本地预览需要 Python（或其他 HTTP 静态文件服务器）。

## 仓库结构

```text
home/
├── index.html                      # 个人主页
├── favicon.ico                     # 站点图标
├── douban/
│   └── db.html                     # 书影音展示页面
├── static/
│   ├── css/                        # 样式文件
│   ├── js/                         # 交互脚本
│   ├── img/                        # 图片与视觉素材
│   ├── svg/                        # SVG 资源
│   └── data/
│       ├── book.json               # 书籍数据
│       ├── movie.json              # 电影数据
│       ├── music.json              # 音乐数据
│       └── douban/                 # 历史数据备份
├── scripts/
│   └── merge_douban_data.py        # 合并并规范化豆瓣导出数据
└── .github/
    └── workflows/
        ├── douban.yml              # 同步豆瓣数据并更新 JSON
        ├── sync.yml                # 同步豆瓣记录到 Notion
        └── manual_run.yml           # 生成贡献图并发布到输出分支
```

## 书影音数据规范

书影音页面读取以下文件：

- [书籍数据](static/data/book.json)
- [电影数据](static/data/movie.json)
- [音乐数据](static/data/music.json)
- [展示页面](douban/db.html)

每个文件应为 JSON 数组。记录通常包含豆瓣导出字段，并通过 `status` 与 `media_type` 标识状态和媒介类型。

### 状态枚举

| JSON 值 | 含义 | 页面文案示例 |
| --- | --- | --- |
| `mark` | 已标记，计划阅读 / 观看 / 收听 | 想读、想看、想听 |
| `doing` | 正在进行 | 在读、在看、在听 |
| `done` | 已完成 | 看完、已看、已听 |

**数据约定：** `status` 只使用 `mark`、`doing`、`done`，不要把中文展示文案写入数据字段。页面可根据媒介类型将统一状态映射为不同文案。新增或修改数据后，建议检查 JSON 格式、状态值、重复记录以及封面链接。

## 自动化工作流

### 1. 豆瓣数据同步

工作流：`.github/workflows/douban.yml`

- 支持定时运行、手动触发，以及相关工作流或合并脚本变更后的触发。
- 通过 `lizheming/doumark-action` 分别导出书籍、电影、音乐的 `mark`、`doing`、`done` 状态。
- 调用 `scripts/merge_douban_data.py` 合并导出结果，按条目身份去重并规范化 `status`、`media_type`。
- 将更新后的 JSON 写入 `static/data/`，并在同步前将现有公开数据备份到 `static/data/douban/`。

若同步结果异常，先检查 Actions 日志与导出文件。合并脚本会在某一媒介类型没有返回任何记录时保护已有数据，避免空结果覆盖现有收藏。

### 2. 同步到 Notion

工作流：`.github/workflows/sync.yml`

该工作流使用 `lizheming/doumark-action` 将豆瓣书籍、电影和音乐记录同步到配置的 Notion 数据库。运行前请在仓库 **Settings → Secrets and variables → Actions** 中配置：

- `notion_token`：具有目标数据库访问权限的 Notion Integration Token。

数据库标识在工作流的 `dir` 配置中维护。请确认集成已被邀请到对应数据库，并只授予必要权限。不要将令牌写入源码或提交到仓库。

### 3. GitHub 贡献图动画

工作流：`.github/workflows/manual_run.yml`

该工作流调用 [Platane/snk](https://github.com/Platane/snk) 生成浅色、深色 SVG 以及 GIF，并发布到 `manual-run-output` 分支。若主页贡献图无法显示，请检查：

1. Actions 最近一次运行是否成功；
2. `manual-run-output` 分支中是否存在对应输出文件；
3. 页面引用的文件路径是否与实际输出目录一致；
4. 浏览器是否缓存了旧资源。

## 本地运行

推荐通过 HTTP 服务预览，避免根路径资源（例如 `/static/css/...`）在直接打开 HTML 文件时无法正确加载。

```bash
git clone https://github.com/ilikui/home.git
cd home
python -m http.server 8000
```

然后访问 [http://localhost:8000](http://localhost:8000)。

修改样式或脚本后，刷新页面即可查看效果；修改 JSON 数据后，也请检查书影音页面能否正确加载与筛选。

## 部署说明

本项目是静态站点，可部署到 Nginx、Apache、GitHub Pages 或其他静态托管服务。

1. 将仓库文件发布到站点根目录。
2. 确认 HTTPS、域名 DNS 与静态资源路径配置正确。
3. 当前页面资源路径按域名根路径部署设计；若部署到子目录，需要相应调整资源引用。
4. 验证首页、书影音页面、主题切换、状态筛选、移动端布局和外部链接。
5. 若依赖自动同步，确认 Actions 已启用，工作流权限和 Secrets 已配置。
6. 部署后检查浏览器控制台与网络请求，排查 404、JSON 解析失败或跨域问题。

## 维护与排障

| 现象 | 优先检查 |
| --- | --- |
| 页面样式丢失 | `static/css/` 文件路径、大小写、部署根路径及浏览器缓存 |
| 书影音内容为空 | JSON 是否有效、页面请求路径、浏览器控制台错误 |
| 状态筛选不正确 | 数据中的 `status` 是否为 `mark`、`doing` 或 `done` |
| 收藏重复 | 检查豆瓣导出与 `scripts/merge_douban_data.py` 的合并逻辑 |
| Actions 同步失败 | 工作流日志、令牌权限、第三方 Action 输出和仓库写权限 |
| Notion 未更新 | `notion_token`、目标数据库 ID、Integration 的数据库访问权限 |
| 贡献图未显示 | 输出分支、生成文件路径、页面引用路径与缓存 |

### 提交前检查清单

- [ ] JSON 文件可被正常解析，状态值符合约定。
- [ ] 页面引用的图片、CSS、JavaScript 与数据文件路径有效。
- [ ] 桌面端和移动端布局正常，主题切换与筛选可用。
- [ ] 没有提交访问令牌、密码或其他敏感凭据。
- [ ] 涉及工作流的改动已通过 GitHub Actions 日志确认。

## 致谢

- [lizheming/doumark-action](https://github.com/lizheming/doumark-action) — 豆瓣收藏同步
- [Platane/snk](https://github.com/Platane/snk) — GitHub 贡献图动画
- GitHub Actions — 自动化运行与发布

第三方工具及素材遵循各自的许可证与使用条款。复用代码或图片前，请确认对应资源的授权要求。
