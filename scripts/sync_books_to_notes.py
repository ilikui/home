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
API_ROOT = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"
API = f"{API_ROOT}/{urllib.parse.quote(TARGET, safe='/')}"
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
    pic = subject.get("pic") or {}
    source_cover = clean(pic.get("large") or pic.get("normal") or subject.get("cover_url"))
    book_id = clean(subject.get("id"))
    cover = f"/assets/books/{book_id}.jpg" if book_id else ""
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
        "source_cover": source_cover, "book_id": book_id,
        "url": url, "rating": rating_text, "rating_count": count_text,
        "subtitle": subtitle, "comment": comment, "status": status,
    }


def cover_image(url, title):
    if not url:
        return "—"
    safe_url = url.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
    safe_title = clean(title).replace("[", "\\[").replace("]", "\\]")
    return f"![{safe_title} 封面]({safe_url})"


def render(books, uploaded_covers=None):
    uploaded_covers = uploaded_covers or set()
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
    for b in fields:
        if b["book_id"] not in uploaded_covers:
            b["cover"] = b["source_cover"]
    for i, b in enumerate(fields, 1):
        title = md_escape(b["title"])
        cover = cover_image(b["cover"], title)
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
            image = cover_image(b["cover"], title)
            if b["url"]:
                lines.append(f'<a href="{b["url"]}">{image}</a>')
            else:
                lines.append(image)
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


def sync_cover_assets(books):
    """Download Douban cover originals and store them in Notes/assets/books."""
    token = os.environ.get("NOTES_REPO_TOKEN", "").strip()
    if not token:
        print("WARNING: 未配置 NOTES_REPO_TOKEN，跳过封面上传；将使用豆瓣封面原始链接。")
        return set()
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "home-books-sync",
    }
    uploaded = set()
    for item in books:
        fields = book_fields(item)
        book_id, source = fields["book_id"], fields["source_cover"]
        if not book_id or not source:
            print(f"Skip cover without id/source: {fields['title']}")
            continue
        request = urllib.request.Request(
            source, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://book.douban.com/"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                image_data = response.read()
                content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/") or len(image_data) < 1000:
                raise RuntimeError(f"Invalid cover response for {book_id}: {content_type}, {len(image_data)} bytes")
        except Exception as exc:
            print(f"WARNING: 下载封面失败 {book_id} ({source}): {exc}；回退到豆瓣原图链接。")
            continue

        path = f"assets/books/{book_id}.jpg"
        endpoint = f"{API_ROOT}/{urllib.parse.quote(path, safe='/')}"
        existing = None
        get_req = urllib.request.Request(endpoint + f"?ref={BRANCH}", headers=headers)
        try:
            with urllib.request.urlopen(get_req, timeout=30) as response:
                existing = json.loads(response.read().decode("utf-8")).get("sha")
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                print(f"WARNING: 检查封面文件失败 {path}: HTTP {exc.code}；跳过本张封面。")
                continue
        payload = {
            "message": f"assets: sync book cover {book_id}",
            "content": base64.b64encode(image_data).decode("ascii"),
            "branch": BRANCH,
        }
        if existing:
            payload["sha"] = existing
        body = json.dumps(payload).encode("utf-8")
        put_req = urllib.request.Request(
            endpoint, data=body, method="PUT",
            headers={**headers, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(put_req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            print(f"Uploaded {path} ({len(image_data)} bytes), commit {result['commit']['sha']}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"WARNING: 上传封面失败 {path}: HTTP {exc.code}: {detail}；回退到豆瓣原图链接。")
            continue
        uploaded.add(book_id)
    return uploaded


def main():
    books = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(books, list):
        raise ValueError("book.json 顶层必须是数组")
    if not books:
        raise ValueError("book.json 为空，拒绝用空书单覆盖目标页面")
    if not os.environ.get("NOTES_REPO_TOKEN", "").strip():
        raise RuntimeError("缺少 NOTES_REPO_TOKEN，无法更新 ilikui/Notes 书单。请在 ilikui/home 仓库配置具有 ilikui/Notes Contents: Read and write 权限的 PAT。")
    uploaded_covers = sync_cover_assets(books)
    generated = render(books, uploaded_covers)
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
