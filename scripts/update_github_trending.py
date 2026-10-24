#!/usr/bin/env python3
"""Build a broad daily GitHub repository dataset for the homepage's category browser."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "static" / "data" / "github-trending.json"
API = "https://api.github.com/search/repositories"
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ilikui-home-github-trending",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Broad discovery categories. Search results are merged and deduplicated, so one
# repository can belong to several categories without appearing twice in the list.
CATEGORY_QUERIES: list[tuple[str, str]] = [
    ("AI / LLM", "topic:llm OR topic:generative-ai OR topic:large-language-models"),
    ("AI Agents", "topic:ai-agent OR topic:agents OR topic:agentic"),
    ("Machine Learning", "topic:machine-learning OR topic:deep-learning OR topic:pytorch OR topic:tensorflow"),
    ("Python", "language:Python"),
    ("C / C++", "language:C OR language:C++"),
    ("Java / Kotlin", "language:Java OR language:Kotlin"),
    ("JavaScript / TypeScript", "language:JavaScript OR language:TypeScript"),
    ("Frontend / Web", "topic:frontend OR topic:react OR topic:vue OR topic:svelte"),
    ("Backend / API", "topic:backend OR topic:api OR topic:microservices"),
    ("Go", "language:Go"),
    ("Rust", "language:Rust"),
    ("PHP", "language:PHP"),
    ("Mobile Apps", "topic:android OR topic:ios OR topic:flutter OR topic:react-native"),
    ("Embedded / IoT", "topic:embedded OR topic:firmware OR topic:iot OR topic:rtos"),
    ("AUTOSAR / Automotive", "topic:autosar OR topic:automotive OR topic:canbus OR topic:uds"),
    ("Autonomous Driving", "topic:autonomous-driving OR topic:self-driving OR topic:autonomous-vehicles"),
    ("Robotics", "topic:robotics OR topic:ros OR topic:robot"),
    ("Databases / Storage", "topic:database OR topic:postgresql OR topic:redis OR topic:storage"),
    ("Data / Analytics", "topic:data-engineering OR topic:data-science OR topic:analytics OR topic:visualization"),
    ("Cloud / DevOps", "topic:devops OR topic:kubernetes OR topic:docker OR topic:cloud-native"),
    ("Security", "topic:security OR topic:cybersecurity OR topic:penetration-testing"),
    ("Testing / Quality", "topic:testing OR topic:test-automation OR topic:quality-assurance"),
    ("Developer Tools", "topic:developer-tools OR topic:cli OR topic:productivity OR topic:code-editor"),
    ("Operating Systems", "topic:linux OR topic:operating-system OR topic:kernel"),
    ("Game / Graphics", "topic:gamedev OR topic:game-engine OR topic:graphics OR topic:computer-graphics"),
    ("Design / Media", "topic:design-tools OR topic:animation OR topic:video OR topic:creative-tools"),
    ("Blockchain / Web3", "topic:blockchain OR topic:web3 OR topic:ethereum"),
    ("Learning / Tutorials", "topic:education OR topic:tutorial OR topic:learning-resources OR topic:awesome-list"),
]

def fetch_repositories(query: str, sort: str = "stars", order: str = "desc", per_page: int = 20) -> list[dict]:
    params = urllib.parse.urlencode({
        "q": f"{query} fork:false archived:false",
        "sort": sort,
        "order": order,
        "per_page": per_page,
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
            "topics": item.get("topics", [])[:8],
            "owner_avatar": (item.get("owner") or {}).get("avatar_url", ""),
            "categories": [],
        })
    return results

def main() -> None:
    now = datetime.now(timezone.utc)
    since_7d = (now - timedelta(days=7)).date().isoformat()
    since_90d = (now - timedelta(days=90)).date().isoformat()
    merged: dict[str, dict] = {}

    def add_results(query: str, category: str | None = None, sort: str = "stars", per_page: int = 20) -> None:
        for repo in fetch_repositories(query, sort=sort, per_page=per_page):
            key = repo["url"]
            if key not in merged:
                merged[key] = repo
            current = merged[key]
            # Keep the richest available description/topics and latest counters.
            if len(repo["description"]) > len(current["description"]):
                current["description"] = repo["description"]
            current["topics"] = sorted(set(current.get("topics", [])) | set(repo.get("topics", [])))[:8]
            current["stars"] = max(current["stars"], repo["stars"])
            current["forks"] = max(current["forks"], repo["forks"])
            current["issues"] = repo["issues"]
            if category and category not in current["categories"]:
                current["categories"].append(category)

    # New projects plus an evergreen popularity pool prevent the dataset from
    # being limited to repositories created in the last week.
    add_results(f"created:>={since_7d} stars:>10", per_page=30)
    add_results(f"stars:>100 pushed:>={since_90d}", per_page=30)
    for category, query in CATEGORY_QUERIES:
        add_results(f"({query}) stars:>10 pushed:>={since_90d}", category=category, per_page=15)
        time.sleep(0.15)

    repositories = sorted(
        merged.values(),
        key=lambda repo: (repo["stars"], repo["pushed_at"]),
        reverse=True,
    )
    data = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "period": "new-this-week-and-popular-updated-last-90-days",
        "total_repositories": len(repositories),
        "category_count": len(CATEGORY_QUERIES),
        "categories": [name for name, _ in CATEGORY_QUERIES],
        "repositories": repositories,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {DATA_PATH.relative_to(ROOT)} with {len(repositories)} unique repositories across {len(CATEGORY_QUERIES)} category searches.")

if __name__ == "__main__":
    main()
