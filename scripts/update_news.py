#!/usr/bin/env python3
"""Build a static news digest using the RSS catalog maintained in ilikui/Dailly."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static" / "data" / "news.json"
# Reuse the user's existing, broad RSS catalog instead of maintaining two lists.
DAILLY_CATALOG = "https://raw.githubusercontent.com/ilikui/Dailly/main/Cfg/rss.json"
MAX_FEEDS = 80
MAX_ITEMS_PER_FEED = 20
MAX_TOTAL_ITEMS = 180
FALLBACK_FEEDS = [
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "category": "科技"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "科技"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "国际"},
    {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "科技"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "category": "国际"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "category": "开源"},
]

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()

def child_text(element: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in element.iter():
        if child is not element and local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""

def item_link(item: ET.Element) -> str:
    for child in item:
        if local_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href:
                return href.strip()
            if child.text and child.text.strip():
                return child.text.strip()
        if local_name(child.tag) == "guid" and child.text and child.text.strip().startswith("http"):
            return child.text.strip()
    return ""

def parse_date(raw: str) -> str:
    if not raw:
        return ""
    try:
        value = parsedate_to_datetime(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError):
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            return ""

def load_feeds() -> list[dict]:
    request = urllib.request.Request(DAILLY_CATALOG, headers={"User-Agent": "LiKuiHomeRSS/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            config = json.loads(response.read().decode("utf-8-sig"))
        feeds = []
        if isinstance(config, list):
            for row in config:
                if not isinstance(row, dict):
                    continue
                url = str(row.get("url", "")).strip()
                if not url.startswith(("https://", "http://")):
                    continue
                feeds.append({
                    "name": str(row.get("name") or url.split("/")[2]),
                    "url": url,
                    "category": str(row.get("type") or "其他"),
                })
        if feeds:
            # Cap requests per run while keeping the catalog's category diversity.
            selected = []
            seen_urls = set()
            for feed in feeds:
                if feed["url"] not in seen_urls:
                    seen_urls.add(feed["url"])
                    selected.append(feed)
                if len(selected) >= MAX_FEEDS:
                    break
            print(f"Loaded {len(selected)} RSS sources from ilikui/Dailly")
            return selected
        raise ValueError("Dailly RSS catalog contains no valid feed URLs")
    except Exception as exc:
        print(f"WARN Could not load Dailly RSS catalog ({exc}); using fallback sources")
        return FALLBACK_FEEDS

def fetch_feed(feed: dict) -> list[dict]:
    request = urllib.request.Request(feed["url"], headers={
        "User-Agent": "Mozilla/5.0 (compatible; LiKuiHomeRSS/1.0; +https://likui.info/)",
        "Accept": "application/rss+xml, application/atom+xml, application/json, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read()
    # Dailly's catalog includes JSON Feed sources as well as RSS/Atom.
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
        rows = payload.get("items", []) if isinstance(payload, dict) else []
        normalized = []
        for row in rows[:MAX_ITEMS_PER_FEED]:
            if not isinstance(row, dict):
                continue
            normalized.append({
                "title": row.get("title", ""),
                "url": row.get("url") or row.get("external_url") or "",
                "summary": row.get("summary") or row.get("content_text") or "",
                "published": row.get("date_published") or row.get("date_modified") or "",
            })
    except (ValueError, UnicodeDecodeError):
        root = ET.fromstring(raw)
        nodes = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
        normalized = []
        for node in nodes[:MAX_ITEMS_PER_FEED]:
            normalized.append({
                "title": child_text(node, "title"),
                "url": item_link(node),
                "summary": child_text(node, "description", "summary", "content", "encoded"),
                "published": child_text(node, "pubdate", "published", "updated", "date"),
            })

    output = []
    for row in normalized:
        title = re.sub(r"\s+", " ", str(row.get("title") or "")).strip()
        url = str(row.get("url") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue
        summary = re.sub(r"<[^>]+>", " ", str(row.get("summary") or ""))
        summary = re.sub(r"\s+", " ", summary).strip()
        output.append({
            "title": title,
            "url": url,
            "summary": summary[:420],
            "source": feed["name"],
            "category": feed["category"],
            "published": parse_date(str(row.get("published") or "")),
        })
    return output

def main() -> None:
    feeds = load_feeds()
    all_items: dict[str, dict] = {}
    failures: list[str] = []
    successful_sources = 0

    # Parallel fetching keeps a large feed catalog within GitHub Actions' time limit.
    with ThreadPoolExecutor(max_workers=16) as executor:
        jobs = {executor.submit(fetch_feed, feed): feed for feed in feeds}
        for job in as_completed(jobs):
            feed = jobs[job]
            try:
                items = job.result()
                successful_sources += 1
                for item in items:
                    key = item["url"].split("#", 1)[0].rstrip("/")
                    if key not in all_items:
                        all_items[key] = item
                print(f'{feed["name"]}: {len(items)} items')
            except Exception as exc:
                message = f'{feed["name"]}: {exc}'
                failures.append(message)
                print(f"WARN {message}")

    # Never replace a working dataset with an empty result.
    if not all_items:
        raise RuntimeError(
            "All RSS sources failed or returned no usable items; existing news.json was preserved. "
            + "; ".join(failures[:12])
        )

    items = sorted(all_items.values(), key=lambda row: row.get("published") or "", reverse=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": successful_sources,
        "catalog": "ilikui/Dailly",
        "failed_source_count": len(failures),
        "failed_sources": failures[:30],
        "items": items[:MAX_TOTAL_ITEMS],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {min(len(items), MAX_TOTAL_ITEMS)} unique stories from {successful_sources}/{len(feeds)} sources")

if __name__ == "__main__":
    main()
