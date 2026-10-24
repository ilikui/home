#!/usr/bin/env python3
"""Fetch popular recently-created GitHub repositories and render a static page."""
from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "static" / "data" / "github-trending.json"
PAGE_PATH = ROOT / "github-trending.html"
API = "https://api.github.com/search/repositories"
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ilikui-home-github-trending",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def fetch_repositories(query: str, sort: str = "stars", order: str = "desc", per_page: int = 30) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": query, "sort": sort, "order": order, "per_page": per_page,
    })
    request = urllib.request.Request(f"{API}?{params}", headers=HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API request failed for query {query!r}: {exc}") from exc
    results = []
    for item in payload.get("items", []):
        results.append({
            "name": item.get("full_name", ""),
            "url": item.get("html_url", ""),
            "description": item.get("description") or "No description provided.",
            "language": item.get("language") or "Not specified",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "issues": item.get("open_issues_count", 0),
            "created_at": item.get("created_at", ""),
            "pushed_at": item.get("pushed_at", ""),
            "topics": item.get("topics", [])[:5],
            "owner_avatar": (item.get("owner") or {}).get("avatar_url", ""),
        })
    return results


def render_page(data: dict) -> str:
    cards = []
    for index, repo in enumerate(data["repositories"], 1):
        topics = "".join(f'<span class="topic">{html.escape(topic)}</span>' for topic in repo["topics"])
        description = html.escape(repo["description"])
        name = html.escape(repo["name"])
        url = html.escape(repo["url"], quote=True)
        language = html.escape(repo["language"])
        avatar = html.escape(repo["owner_avatar"], quote=True)
        cards.append(f"""
        <article class="repo-card">
          <div class="repo-top"><span class="rank">#{index:02d}</span><span class="language">{language}</span></div>
          <div class="repo-title-row"><img src="{avatar}" alt="" loading="lazy"><h2><a href="{url}" target="_blank" rel="noopener noreferrer">{name}</a></h2></div>
          <p class="description">{description}</p>
          <div class="topics">{topics}</div>
          <div class="metrics"><span>★ {repo["stars"]:,}</span><span>⑂ {repo["forks"]:,}</span><span>◎ {repo["issues"]:,} issues</span></div>
        </article>""")
    generated = html.escape(data["generated_at"])
    count = len(cards)
    cards_html = "\n".join(cards) or '<p class="empty">No repositories found for this period.</p>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="每日 GitHub 热门开源仓库精选，由 GitHub Actions 自动更新。">
<meta name="theme-color" content="#0b1020"><title>GitHub Trending · LiKui</title>
<style>
:root{{--bg:#0b1020;--panel:#111a2e;--line:#25324b;--text:#eef3ff;--muted:#9baac4;--accent:#8b9cff;}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at top,#18264a 0,transparent 55%),var(--bg);color:var(--text);font:16px/1.6 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
a{{color:inherit;text-decoration:none}}a:hover{{color:var(--accent)}}.wrap{{width:min(1120px,calc(100% - 36px));margin:auto}}
header{{padding:34px 0 24px;display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:1px solid var(--line)}}
.brand{{font-weight:800;letter-spacing:.04em}}.back{{color:var(--muted);border:1px solid var(--line);padding:8px 13px;border-radius:999px}}
.hero{{padding:58px 0 32px}}.eyebrow{{color:#a8b4ff;font-size:.78rem;letter-spacing:.16em;font-weight:700}}h1{{font-size:clamp(2.4rem,6vw,4.6rem);line-height:1.05;letter-spacing:-.055em;margin:14px 0}}.lead{{color:var(--muted);max-width:650px;font-size:1.05rem}}
.stats{{display:flex;flex-wrap:wrap;gap:10px;margin-top:24px}}.stat{{padding:9px 13px;background:#151f37;border:1px solid var(--line);border-radius:12px;color:#dbe4ff;font-size:.88rem}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;padding:12px 0 64px}}
.repo-card{{min-width:0;padding:20px;background:linear-gradient(145deg,#151f35,#101729);border:1px solid var(--line);border-radius:18px;display:flex;flex-direction:column;transition:transform .2s,border-color .2s}}
.repo-card:hover{{transform:translateY(-3px);border-color:#6475c9}}.repo-top{{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:.78rem}}.rank{{color:#aeb9ff;font-weight:800}}.language{{padding:3px 8px;border:1px solid var(--line);border-radius:999px}}
.repo-title-row{{display:flex;align-items:center;gap:10px;margin-top:17px;min-width:0}}.repo-title-row img{{width:30px;height:30px;border-radius:50%;background:#26334e}}h2{{font-size:1rem;overflow-wrap:anywhere;margin:0}}.description{{color:var(--muted);font-size:.91rem;min-height:4.4em;margin:12px 0}}
.topics{{display:flex;flex-wrap:wrap;gap:6px;min-height:28px}}.topic{{font-size:.72rem;color:#c4ceff;background:#222d4d;border-radius:6px;padding:3px 7px}}
.metrics{{display:flex;flex-wrap:wrap;gap:12px;margin-top:auto;padding-top:18px;color:#c7d2e8;font-size:.8rem}}footer{{border-top:1px solid var(--line);padding:22px 0 34px;color:var(--muted);font-size:.85rem;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}}
@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}header{{align-items:flex-start}}.hero{{padding-top:40px}}}}
</style></head>
<body><div class="wrap">
<header><a class="brand" href="/">LiKui / OPEN SOURCE RADAR</a><a class="back" href="/">← 返回主页</a></header>
<section class="hero"><div class="eyebrow">DAILY OPEN-SOURCE DISCOVERY</div><h1>GitHub Trending<span style="color:#8b9cff">.</span></h1>
<p class="lead">每日发现值得关注的开源项目。按最近 7 天创建的仓库中 Star 数排序，提供项目简介、主要语言与社区指标，帮助你持续追踪技术趋势。</p>
<div class="stats"><span class="stat">精选 {count} 个仓库</span><span class="stat">更新于 {generated} UTC</span><span class="stat">数据来源：GitHub Search API</span></div></section>
<main class="grid">{cards_html}</main>
<footer><span>LiKui Personal Hub · Build, Learn, Share.</span><span>自动更新 · GitHub Actions</span></footer>
</div></body></html>"""


def main() -> None:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=7)).date().isoformat()
    repositories = fetch_repositories(f"created:>={since} fork:false archived:false", per_page=30)
    # Keep the page useful during quieter weeks by supplementing with recently active projects.
    known = {repo["url"] for repo in repositories}
    if len(repositories) < 20:
        for repo in fetch_repositories("pushed:>=2024-01-01 fork:false archived:false", sort="updated", per_page=30):
            if repo["url"] not in known:
                repositories.append(repo)
                known.add(repo["url"])
            if len(repositories) >= 30:
                break
    data = {"generated_at": now.strftime("%Y-%m-%d %H:%M"), "period": "last-7-days", "repositories": repositories[:30]}
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PAGE_PATH.write_text(render_page(data), encoding="utf-8")
    print(f"Updated {PAGE_PATH.relative_to(ROOT)} with {len(data['repositories'])} repositories.")


if __name__ == "__main__":
    main()
