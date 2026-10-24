# LiKui · 个人主页

> 把技术做成系统，把思考沉淀成作品。

这是个人主页的源代码仓库，采用原生 HTML、CSS 与 JavaScript 构建，集中展示个人介绍、常用数字空间、项目入口、技术兴趣和书影音收藏。页面以轻量、响应式和易维护为目标。

- **在线主页**：[likui.info](https://likui.info/)
- **关于我**：[about.likui.info](https://about.likui.info/)
- **GitHub**：[github.com/ilikui](https://github.com/ilikui)
- **源码仓库**：[ilikui/home](https://github.com/ilikui/home)

## 页面内容

| 模块 | 说明 |
| --- | --- |
| 个人介绍 | 个人简介、关注领域与站内导航 |
| 我的空间 | 笔记、日记、博客和 RSS 阅读器入口 |
| 项目与记录 | 关于我页面、书影音收藏 |
| 技术与开源 | GitHub 贡献记录展示与项目入口 |
| 书影音收藏 | 读取豆瓣同步生成的书籍、电影和音乐数据，并提供分类浏览 |

## 技术栈

- **前端**：HTML5、CSS3、原生 JavaScript
- **数据格式**：JSON
- **自动化**：GitHub Actions
- **内容同步**：[lizheming/doumark-action](https://github.com/lizheming/doumark-action)
- **贡献图动画**：[Platane/snk](https://github.com/Platane/snk)

无需安装前端框架或构建工具；页面主要由静态文件组成，可直接部署到支持静态网站的 Web 服务。

## 仓库结构

```text
home/
├── index.html                 # 个人主页入口
├── favicon.ico                # 站点图标
├── douban/
│   └── db.html                # 书影音收藏页面
├── static/
│   ├── css/                   # 页面样式
│   ├── js/                    # 页面交互脚本
│   ├── img/                   # 图片与视觉素材
│   ├── svg/                   # SVG 资源与贡献图
│   └── data/
│       ├── book.json          # 豆瓣书籍数据
│       ├── movie.json         # 豆瓣电影数据
│       ├── music.json         # 豆瓣音乐数据
│       └── douban/            # 历史数据备份
├── script/
│   ├── main.py                # 电影图片下载辅助脚本
│   └── movie.json             # 脚本使用的数据文件
└── .github/
    └── workflows/
        ├── douban.yml         # 豆瓣数据同步到 JSON 文件
        ├── sync.yml           # 豆瓣数据同步到 Notion
        └── manual_run.yml     # 生成 GitHub 贡献图动画
```

## 数据与自动化

### 豆瓣书影音数据

书影音页面使用仓库中的静态 JSON 数据，不需要在访客浏览器中实时请求豆瓣接口：

- [书籍数据](static/data/book.json)
- [电影数据](static/data/movie.json)
- [音乐数据](static/data/music.json)
- [收藏展示页面](douban/db.html)

`.github/workflows/douban.yml` 支持定时运行和手动触发（`workflow_dispatch`），通过 `lizheming/doumark-action` 获取豆瓣账号 `olikuio` 的书籍、电影和音乐记录，再提交更新后的数据文件。工作流还会尝试将当日旧数据移动到 `static/data/douban/` 作为备份；首次运行前应确认备份目录存在且目标文件存在，避免因 `mv` 步骤失败导致任务中断。

### 同步到 Notion

`.github/workflows/sync.yml` 将豆瓣书籍、电影和音乐记录同步到指定的 Notion 数据库。需要在仓库的 **Settings → Secrets and variables → Actions** 中配置 `notion_token`，并确保该令牌对相应数据库具有访问权限。数据库标识与同步目标应以工作流配置为准。

### GitHub 贡献图动画

`.github/workflows/manual_run.yml` 定时或手动生成贡献图 SVG/GIF，并发布到 `manual-run-output` 分支。主页引用的图片文件路径、输出分支内容和工作流产物需要保持一致；若贡献图未显示，请先检查 Actions 最近一次运行结果及输出分支文件。

## 本地预览

由于页面使用根路径资源（例如 `/static/css/style.css`），推荐通过本地 HTTP 服务预览，而不是直接双击 HTML 文件。

使用 Python：

```bash
git clone https://github.com/ilikui/home.git
cd home
python -m http.server 8000
```

然后打开 [http://localhost:8000](http://localhost:8000)。

## 部署

这是静态站点，可部署到 Nginx、Apache、对象存储静态托管或其他静态网站服务。

1. 将仓库内容部署到站点根目录。
2. 确认站点支持 HTTPS，并将域名 DNS 指向对应托管服务。
3. 检查 `index.html` 中的资源路径和外链是否符合部署路径；当前资源引用按域名根目录部署设计。
4. 检查首页、书影音页面、深色模式、移动端布局及外部链接。
5. 如果需要自动更新数据，确认 GitHub Actions 已启用，且仓库具有工作流所需权限和 Secrets。

## 维护建议

- 修改首页布局前，先检查 `index.html`、`static/css/` 与 `static/js/` 的对应关系。
- 更新豆瓣数据后，检查 JSON 是否有效、书影音页面是否能正常读取，以及历史备份是否完整。
- 不要将访问令牌或其他凭据写入仓库文件；敏感值应放在 GitHub Actions Secrets。
- 自动化任务失败时，优先查看对应 workflow 的日志，不要仅凭页面仍可访问就判断数据已经更新。
- 对外链、数据字段和静态资源路径的调整，应同时检查桌面端与移动端显示。

## 许可证与致谢

本项目使用的第三方工具和服务遵循各自的许可证与使用条款。特别感谢：

- [doumark-action](https://github.com/lizheming/doumark-action)
- [snk](https://github.com/Platane/snk)

如需复用本仓库中的代码或素材，请先确认对应文件的版权与许可证要求。
