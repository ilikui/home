#!/usr/bin/env python3
"""Sync home/static/data/book.json into ilikui/Notes' reading list."""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SOURCE = Path("static/data/book.json")
OWNER = "ilikui"
REPO = "Notes"
BRANCH = "main"
TARGET = "pages/阅读笔记/好书推荐.md"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{urllib.parse.quote(TARGET, safe='/')}"
START = "<!-- BOOKS:AUTO-GENERATED:START -->"
END = "<!-- BOOKS:AUTO-GENERATED:END -->"

STATUS = {"done": "已读", "doing": "在读", "mark": "待读"}
UNKNOWN = "未提供"


def clean(value):
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def md_escape(value):
    return clean(value).replace("|", "\\|")


def book_fields(item):
    subject = item.get("subject") or {}
    title = clean(subject.get("title")) or "未命名书籍"
    authors = subject.get("author") or []
    author = "、".join(clean(x) for x in authors if clean(x)) or UNKNOWN
    tags = item.get("tags") or []
    tags_text = "、".join(clean(x) for x in tags if clean(x)) or "未分类"
    cover = clean(subject.get("cover_url"))
    if not cover:
        pic = subject.get("pic") or {}
        cover = clean(pic.get("large") or pic.get("normal"))
    url = clean(subject.get("url") or subject.get("sharing_url") or item.get("sharing_url"))
    rating = subject.get("rating") or {}
    rating_value = rating.get("value")
    rating_text = f'{rating_value}/10' if rating_value is not None else "暂无评分"
    rating_count = rating.get("count")
    count_text = f'（{rating_count} 人评价）' if rating_count is not None else ""
    subtitle = clean(subject.get("card_subtitle"))
    comment = clean(item.get("comment"))
    status = STATUS.get(clean(item.get("status")), clean(item.get("status")) or "未标记")
    return {
        "title": title, "author": author, "tags": tags_text, "cover": cover,
        "url": url, "rating": rating_text, "rating_count": count_text,
        "subtitle": subtitle, "comment": comment, "status": status,
    }


def render(books):
    lines = [
        START,
        f"> 本区块由 `ilikui/home/static/data/book.json` 自动生成，共 **{len(books)} 本**。请在源 JSON 中维护书籍数据；本区块会在同步时整体更新。",
        "",
        "## 书单总览",
        "",
        "| # | 封面 | 书名 | 作者 | 分类/标签 | 阅读状态 | 豆瓣评分 |",
        "|--:|---|---|---|---|---|--:|",
    ]
    fields = [book_fields(item) for item in books]
    for i, b in enumerate(fields, 1):
        title = md_escape(b["title"])
        cover = f'![{title} 封面]({b["cover"]})' if b["cover"] else "—"
        book_link = f"[{title}]({b['url']})" if b["url"] else title
        lines.append(
            f"| {i} | {cover} | {book_link} | {md_escape(b['author'])} | "
            f"{md_escape(b['tags'])} | {b['status']} | {b['rating']} |"
        )
    lines += ["", "## 书籍详情", ""]
    for i, b in enumerate(fields, 1):
        title = b["title"]
        lines += [f"### {i}. {title}", ""]
        if b["cover"]:
            if b["url"]:
                lines.append(f'[![{title} 封面]({b["cover"]})]({b["url"]})')
            else:
                lines.append(f'![{title} 封面]({b["cover"]})')
            lines.append("")
        lines += [
            f'- **作者：** {b["author"]}',
            f'- **分类/标签：** {b["tags"]}',
            f'- **阅读状态：** {b["status"]}',
            f'- **豆瓣评分：** {b["rating"]}{b["rating_count"]}',
        ]
        if b["subtitle"]:
            lines.append(f'- **版本信息：** {b["subtitle"]}')
        if b["url"]:
            lines.append(f'- **豆瓣链接：** [查看《{title}》]({b["url"]})')
        if b["comment"]:
            lines.append(f'- **个人短评：** {b["comment"]}')
        lines.append("")
    lines += [END]
    return "\n".join(lines).rstrip()


def api_request(method, payload=None):
    token = os.environ.get("NOTES_REPO_TOKEN", "").strip()
    if not token:
        raise RuntimeError("缺少 NOTES_REPO_TOKEN。请在 ilikui/home 仓库配置可写入 ilikui/Notes 的 PAT。")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        API + f"?ref={BRANCH}",
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "home-books-sync",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {detail}") from exc


def main():
    books = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(books, list):
        raise ValueError("book.json 顶层必须是数组")
    if not books:
        raise ValueError("book.json 为空，拒绝用空书单覆盖目标页面")
    generated = render(books)
    remote = api_request("GET")
    current = base64.b64decode(remote["content"]).decode("utf-8")
    if START in current and END in current:
        prefix, rest = current.split(START, 1)
        _, suffix = rest.split(END, 1)
        updated = prefix.rstrip() + "\n\n" + generated + suffix
    else:
        begin = current.find("## 书单总览")
        finish = current.find("## 如何建立可复用的书单")
        if begin < 0 or finish < 0 or finish <= begin:
            raise RuntimeError("目标页面缺少预期章节，拒绝覆盖以保护原有笔记")
        updated = current[:begin].rstrip() + "\n\n" + generated + "\n\n" + current[finish:]
    if updated == current:
        print(f"No changes: {len(books)} books already synchronized.")
        return
    payload = {
        "message": f"chore: sync {len(books)} books from home",
        "content": base64.b64encode(updated.encode("utf-8")).decode("ascii"),
        "sha": remote["sha"],
        "branch": BRANCH,
    }
    result = api_request("PUT", payload)
    print(f"Synced {len(books)} books. Commit: {result['commit']['sha']}")


if __name__ == "__main__":
    main()
