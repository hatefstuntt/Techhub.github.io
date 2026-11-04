#!/usr/bin/env python3
"""Cheap first step of every hourly run: decide whether this run has work to do.

Prints a summary and a final line:  DUE posts=<n> registry=<yes|no>
  posts    = how many posts this run must publish now (0 = exit immediately, nothing to do)
  registry = yes when a registry source has a new, not-yet-seen price-table post

Schedule: 2 posts every 2 hours (09:07, 11:07 … 21:07 Tehran) = 14 a day. If earlier runs were missed
(usage limit, errors), the deficit is caught up at the next run, up to MAX_PER_RUN per run.
"""
import json, os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TEHRAN = timezone(timedelta(hours=3, minutes=30))  # Iran has no DST since 2022
DAILY_TARGET = 14
MAX_PER_RUN = 3
CHANNEL = "@techhubvpn"  # count posts in the main channel (both channels get the same posts)
REGISTRY_SOURCES = ["sabregistry"]
SEEN = os.path.join(HERE, "data", "registry-seen.json")


def expected_by(now):
    if now.hour < 9:
        return 0
    return min(DAILY_TARGET, 2 * ((now.hour - 9) // 2) + 2)


def posted_today(now):
    """Count today's posts in the channel itself (git-independent)."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return sum(1 for p in state.fetch_recent(CHANNEL) if p["time"] and p["time"] >= start)


def new_registry_posts():
    """Return [(channel, post_id)] of price-table posts (photo + 'قیمت گمرکی') not in registry-seen.json."""
    seen = json.load(open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {}
    # the newest source post we already turned into a card is recorded in our own channel (s=<id>)
    seen["sabregistry"] = max(seen.get("sabregistry", 0), state.last_registry_source_id(CHANNEL))
    found = []
    for ch in REGISTRY_SOURCES:
        try:
            html = urllib.request.urlopen(f"https://t.me/s/{ch}", timeout=30).read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"WARN cannot read {ch}: {e}")
            continue
        for p in html.split('class="tgme_widget_message_wrap')[1:]:
            m = re.search(r'data-post="[^/]+/(\d+)"', p)
            if not m or "photo_wrap" not in p:
                continue
            text = re.sub(r"<[^>]+>", "", p)
            if "قیمت گمرکی" in text or "لیست قیمت" in text:
                pid = int(m.group(1))
                if pid > seen.get(ch, 0):
                    found.append((ch, pid))
    return found


def main():
    now = datetime.now(TEHRAN)
    exp, done = expected_by(now), posted_today(now)
    deficit = max(0, exp - done)
    reg = new_registry_posts()
    posts = min(MAX_PER_RUN, deficit)
    if reg and posts == 0:
        posts = 1  # a new price table is always worth a post
    print(f"tehran={now:%Y-%m-%d %H:%M} expected={exp} posted_today={done} deficit={deficit}")
    for ch, pid in reg:
        print(f"NEW REGISTRY POST https://t.me/{ch}/{pid}")
    print(f"DUE posts={posts} registry={'yes' if reg else 'no'}")


if __name__ == "__main__":
    main()
