#!/usr/bin/env python3
"""Aggregate public RSS feeds into a small, static news digest."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "static" / "data" / "news.json"
FEEDS = [
    {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "category": "科技"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "科技"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "category": "科技"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "国际"},
    {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "category": "科技"},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "category": "国际"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/", "category": "科技"},
    {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default", "category": "人工智能"},
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "人工智能"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "category": "开源"},
]

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()

def child_text(element: ET.Element, *names: str) -> str:
    wanted = {n.lower() for n in names}
    for child in element.iter():
        if child is element:
            continue
        if local_name(child.tag) in wanted and child.text:
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
        if local_name(child.tag) == "guid" and child.text and child.text.startswith("http"):
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
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            return ""

def fetch_feed(feed: dict) -> list[dict]:
    request = urllib.request.Request(feed["url"], headers={
        "User-Agent": "LiKuiHomeRSS/1.0 (+https://likui.info/)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    items = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
    output = []
    for item in items[:35]:
        title = child_text(item, "title")
        link = item_link(item)
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        summary = child_text(item, "description", "summary", "content", "encoded")
        summary = re.sub(r"<[^>]+>", " ", summary)
        summary = re.sub(r"\s+", " ", summary).strip()
        output.append({
            "title": re.sub(r"\s+", " ", title),
            "url": link,
            "summary": summary[:420],
            "source": feed["name"],
            "category": feed["category"],
            "published": parse_date(child_text(item, "pubdate", "published", "updated", "date")),
        })
    return output

def main() -> None:
    all_items: dict[str, dict] = {}
    failures = []
    for feed in FEEDS:
        try:
            items = fetch_feed(feed)
            for item in items:
                key = item["url"].split("#", 1)[0]
                if key not in all_items:
                    all_items[key] = item
            print(f'{feed["name"]}: {len(items)} items')
        except (urllib.error.URLError, TimeoutError, ET.ParseError, OSError, ValueError) as exc:
            failures.append(f'{feed["name"]}: {exc}')
            print(f'WARN {feed["name"]}: {exc}')
        time.sleep(0.15)

    # Preserve the last known-good dataset if every feed fails.
    if not all_items:
        raise RuntimeError("Every RSS feed failed; existing news.json was left untouched. " + "; ".join(failures))

    items = sorted(all_items.values(), key=lambda x: x.get("published") or "", reverse=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(FEEDS) - len(failures),
        "failed_sources": failures,
        "items": items[:180],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {min(len(items), 180)} unique stories to {OUTPUT}")

if __name__ == "__main__":
    main()
