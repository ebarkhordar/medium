#!/usr/bin/env python3
"""Fetch top Medium posts from the last N days across configured tags."""

import argparse
import html
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.request import urlopen, Request
from collections import Counter

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

# ── Config ──────────────────────────────────────────────────────────────────
DEFAULT_TAGS = [
    "ai-agents",
    "agentic-ai",
    "llm",
    "large-language-models",
    "artificial-intelligence",
    "coding",
    "programming",
    "python",
    "prompt-engineering",
    "generative-ai",
    "chatgpt",
    "langchain",
]
FEED_URL = "https://medium.com/feed/tag/{tag}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# ────────────────────────────────────────────────────────────────────────────


def fetch_feed(tag: str) -> list[dict]:
    """Fetch and parse a single tag RSS feed, return list of post dicts."""
    url = FEED_URL.format(tag=tag)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=15) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        print(f"  [!] Failed to fetch '{tag}': {e}")
        return []

    ns = {"content": "http://purl.org/rss/1.0/modules/content/",
          "dc": "http://purl.org/dc/elements/1.1/"}
    posts = []
    for item in tree.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        author = item.findtext("dc:creator", "", ns).strip()
        pub_date_str = item.findtext("pubDate", "").strip()
        categories = [c.text for c in item.findall("category") if c.text]

        # Parse date
        pub_date = None
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
            try:
                pub_date = datetime.strptime(pub_date_str, fmt)
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue

        # Extract reading time / claps from description if available
        desc_raw = item.findtext("description", "")
        reading_time = _extract_reading_time(desc_raw)
        subtitle = _extract_subtitle(desc_raw)

        # Clean tracking params from link
        link = re.sub(r"\?source=rss[^&]*", "", link)

        posts.append({
            "title": html.unescape(title),
            "link": link,
            "author": html.unescape(author),
            "pub_date": pub_date,
            "pub_date_str": pub_date_str,
            "tags": categories,
            "reading_time": reading_time,
            "subtitle": subtitle,
            "source_tag": tag,
        })
    return posts


def _extract_reading_time(desc_html: str) -> str | None:
    m = re.search(r"(\d+)\s*min\s*read", desc_html, re.IGNORECASE)
    return f"{m.group(1)} min read" if m else None


def _extract_subtitle(desc_html: str) -> str:
    text = re.sub(r"<[^>]+>", "", desc_html)
    text = html.unescape(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:200] + "..." if len(text) > 200 else text


def fetch_engagement(post: dict) -> dict:
    """Scrape clap count and comment count from a Medium article page."""
    url = post["link"]
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(req, timeout=15) as resp:
            page = resp.read().decode("utf-8", errors="replace")
    except Exception:
        post["claps"] = None
        post["responses"] = None
        return post

    m = re.search(r'"clapCount":(\d+)', page)
    post["claps"] = int(m.group(1)) if m else None

    m = re.search(r'"postResponses":\{"__typename":"PostResponses","count":(\d+)\}', page)
    post["responses"] = int(m.group(1)) if m else None

    if not post["reading_time"]:
        m = re.search(r'"readingTime":([\d.]+)', page)
        if m:
            post["reading_time"] = f"{round(float(m.group(1)))} min read"

    return post


def fetch_engagement_batch(posts: list[dict]) -> list[dict]:
    """Fetch engagement metrics for multiple posts concurrently."""
    print(f"\nFetching engagement metrics for top {len(posts)} posts...")
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_engagement, p): p for p in posts}
        for f in as_completed(futures):
            p = f.result()
            claps = p.get("claps")
            symbol = "🔥" if claps and claps >= 100 else "  "
            clap_str = str(claps) if claps is not None else "?"
            print(f"  {symbol} {clap_str:>6} claps — {p['title'][:50]}")
    return posts


def deduplicate(posts: list[dict]) -> list[dict]:
    """Remove duplicate posts (same link), keep first occurrence."""
    seen = set()
    unique = []
    for p in posts:
        if p["link"] not in seen:
            seen.add(p["link"])
            unique.append(p)
    return unique


def filter_recent(posts: list[dict], days: int) -> list[dict]:
    """Keep only posts published within the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [p for p in posts if p["pub_date"] and p["pub_date"] >= cutoff]


def rank_posts(posts: list[dict]) -> list[dict]:
    """Rank posts by how many tag feeds they appeared in (proxy for virality)."""
    # Count how many different tag feeds surfaced each URL
    link_tags: dict[str, set] = {}
    for p in posts:
        link_tags.setdefault(p["link"], set()).add(p["source_tag"])

    # Merge tags from all feeds
    link_all_tags: dict[str, list] = {}
    for p in posts:
        existing = link_all_tags.get(p["link"], [])
        for t in p["tags"]:
            if t not in existing:
                existing.append(t)
        link_all_tags[p["link"]] = existing

    deduped = deduplicate(posts)
    for p in deduped:
        p["feed_count"] = len(link_tags.get(p["link"], set()))
        p["all_tags"] = link_all_tags.get(p["link"], p["tags"])

    # Sort: claps first (if fetched), then feed count, then recency
    deduped.sort(key=lambda p: (
        p.get("claps") or 0,
        p["feed_count"],
        p["pub_date"] or datetime.min.replace(tzinfo=timezone.utc),
    ), reverse=True)
    return deduped


def display(posts: list[dict], top_n: int, days: int):
    tag_counter = Counter()
    for p in posts:
        for t in p.get("all_tags", p["tags"]):
            tag_counter[t] += 1

    print(f"\n{'='*70}")
    print(f"  MEDIUM TRENDING — Top {min(top_n, len(posts))} posts (last {days} days)")
    print(f"{'='*70}\n")

    if not posts:
        print("  No posts found. Try increasing --days or adding more --tags.\n")
        return

    for i, p in enumerate(posts[:top_n], 1):
        date_str = p["pub_date"].strftime("%b %d, %Y %H:%M") if p["pub_date"] else "Unknown"
        reading = p["reading_time"] or "N/A"
        tags_str = ", ".join(p.get("all_tags", p["tags"])[:6])

        claps = p.get("claps")
        responses = p.get("responses")
        feeds = p.get("feed_count", 1)

        # Hype meter
        if claps is not None and claps >= 500:
            hype = "🔥🔥🔥 VIRAL"
        elif claps is not None and claps >= 100:
            hype = "🔥🔥 HOT"
        elif claps is not None and claps >= 20:
            hype = "🔥 Warm"
        elif claps is not None:
            hype = "💤 Low"
        else:
            hype = "❓ N/A"

        clap_str = f"{claps:,}" if claps is not None else "?"
        resp_str = str(responses) if responses is not None else "?"

        print(f"  #{i}  [{hype}]")
        print(f"  Title:      {p['title']}")
        print(f"  Author:     {p['author']}")
        print(f"  Date:       {date_str}  |  {reading}")
        print(f"  Claps:      {clap_str}  |  Responses: {resp_str}  |  Feeds: {feeds}")
        print(f"  Tags:       {tags_str}")
        if p["subtitle"]:
            print(f"  Preview:    {p['subtitle']}")
        print(f"  Link:       {p['link']}")
        print()

    # Trending tags summary
    print(f"{'─'*70}")
    print("  Trending tags across all fetched posts:")
    for tag, count in tag_counter.most_common(10):
        print(f"    • {tag} ({count})")
    print()


def save_daily(posts: list[dict], top_n: int, days: int) -> tuple[Path, Path]:
    """Save top posts to daily JSON and Markdown files under data/."""
    DATA_DIR.mkdir(exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = DATA_DIR / f"{today}.json"
    md_path = DATA_DIR / f"{today}.md"

    top_posts = posts[:top_n]

    # ── JSON ────────────────────────────────────────────────────────────
    serializable = []
    for p in top_posts:
        serializable.append({
            "title": p["title"],
            "author": p["author"],
            "link": p["link"],
            "pub_date": p["pub_date"].isoformat() if p["pub_date"] else None,
            "claps": p.get("claps"),
            "responses": p.get("responses"),
            "reading_time": p["reading_time"],
            "tags": p.get("all_tags", p["tags"]),
            "feed_count": p.get("feed_count", 1),
            "preview": p.get("subtitle", ""),
        })
    with open(json_path, "w") as f:
        json.dump({"date": today, "days_window": days, "posts": serializable}, f, indent=2)

    # ── Markdown ────────────────────────────────────────────────────────
    lines = [f"# Medium Trending — {today}", f"Top {len(top_posts)} posts (last {days} days)\n"]
    for i, p in enumerate(top_posts, 1):
        claps = p.get("claps")
        responses = p.get("responses")
        date_str = p["pub_date"].strftime("%b %d, %Y") if p["pub_date"] else "Unknown"
        reading = p["reading_time"] or "N/A"
        tags_str = ", ".join(p.get("all_tags", p["tags"])[:6])
        clap_str = f"{claps:,}" if claps is not None else "?"
        resp_str = str(responses) if responses is not None else "?"

        if claps is not None and claps >= 500:
            hype = "VIRAL"
        elif claps is not None and claps >= 100:
            hype = "HOT"
        elif claps is not None and claps >= 20:
            hype = "Warm"
        elif claps is not None:
            hype = "Low"
        else:
            hype = "N/A"

        lines.append(f"## {i}. {p['title']}")
        lines.append(f"- **Hype:** {hype} | **Claps:** {clap_str} | **Responses:** {resp_str}")
        lines.append(f"- **Author:** {p['author']} | **Date:** {date_str} | **Read:** {reading}")
        lines.append(f"- **Tags:** {tags_str}")
        if p.get("subtitle"):
            lines.append(f"- **Preview:** {p['subtitle']}")
        lines.append(f"- **Link:** {p['link']}")
        lines.append("")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\nSaved: {json_path}")
    print(f"Saved: {md_path}")
    return json_path, md_path


def git_commit_and_push():
    """Stage data/, commit with today's date, and push."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cwd = str(SCRIPT_DIR)

    subprocess.run(["git", "add", "data/"], cwd=cwd, check=True)

    result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=cwd)
    if result.returncode == 0:
        print("\nNo new changes to commit.")
        return

    subprocess.run(
        ["git", "commit", "-m", f"Add trending posts for {today}"],
        cwd=cwd, check=True,
    )
    subprocess.run(["git", "push"], cwd=cwd, check=True)
    print(f"\nCommitted and pushed trending data for {today}.")


def main():
    parser = argparse.ArgumentParser(description="Fetch trending Medium posts")
    parser.add_argument("--tags", nargs="+", default=DEFAULT_TAGS,
                        help="Tags to fetch (default: %(default)s)")
    parser.add_argument("--days", type=int, default=3,
                        help="Look back N days (default: 3)")
    parser.add_argument("--top", type=int, default=5,
                        help="Show top N posts (default: 5)")
    parser.add_argument("--save", action="store_true",
                        help="Save to daily files, commit and push")
    args = parser.parse_args()

    all_posts = []
    print(f"\nFetching feeds for {len(args.tags)} tags...")
    for tag in args.tags:
        print(f"  → {tag}")
        posts = fetch_feed(tag)
        all_posts.extend(posts)

    print(f"\nFetched {len(all_posts)} total items, filtering last {args.days} days...")
    recent = filter_recent(all_posts, args.days)
    print(f"Found {len(recent)} recent posts, pre-ranking...")

    # Pre-rank by feed count to pick top candidates for engagement fetch
    ranked = rank_posts(recent)

    # Fetch claps/responses for top candidates (fetch more than needed for re-ranking)
    candidates = ranked[:args.top * 3]
    fetch_engagement_batch(candidates)

    # Re-rank with engagement data
    ranked = rank_posts(recent)
    display(ranked, args.top, args.days)

    if args.save:
        save_daily(ranked, args.top, args.days)
        git_commit_and_push()


if __name__ == "__main__":
    main()
