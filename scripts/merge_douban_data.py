#!/usr/bin/env python3
"""Merge Douban mark/doing/done exports into the public collection JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / ".tmp" / "douban-sync"
OUTPUT_ROOT = ROOT / "static" / "data"
MEDIA_TYPES = ("book", "movie", "music")
STATUSES = ("mark", "doing", "done")


def identity(item: dict[str, Any]) -> str:
    subject = item.get("subject") or {}
    value = subject.get("id") or subject.get("url") or item.get("id")
    return str(value) if value is not None else json.dumps(item, sort_keys=True, ensure_ascii=False)


def load_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot parse Douban export: {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise RuntimeError(f"Expected a JSON array in {path}")
    return [item for item in payload if isinstance(item, dict)]


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for media_type in MEDIA_TYPES:
        merged: dict[str, dict[str, Any]] = {}
        for status in STATUSES:
            source = SOURCE_ROOT / status / f"{media_type}.json"
            for item in load_items(source):
                normalized = dict(item)
                normalized["status"] = status
                normalized["media_type"] = media_type
                key = identity(normalized)
                previous = merged.get(key)
                # If a record appears in more than one status export, keep the
                # most recently marked copy rather than duplicating the card.
                if previous is None or str(normalized.get("create_time", "")) >= str(previous.get("create_time", "")):
                    merged[key] = normalized
        items = list(merged.values())
        target = OUTPUT_ROOT / f"{media_type}.json"
        if not items and target.exists():
            raise RuntimeError(f"No {media_type} records were returned for any status; preserving existing {target}")
        items.sort(key=lambda item: str(item.get("create_time", "")), reverse=True)
        target.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts = {status: sum(item.get("status") == status for item in items) for status in STATUSES}
        print(f"{target.relative_to(ROOT)}: {len(items)} records; " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
