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


def expected_by(now, target=None, start=9, end=22):
    """Posts that should be out by this hour: the daily target spread evenly over start..end."""
    target = DAILY_TARGET if target is None else target
    if target <= 0 or now.hour < start:
        return 0
    if now.hour >= end:
        return target
    import math
    return min(target, math.ceil(target * (now.hour - start + 1) / (end - start + 1)))


def posted_today(now, chat=None):
    """Count today's posts in the channel itself (git-independent)."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return sum(1 for p in state.fetch_recent(chat or CHANNEL) if p["time"] and p["time"] >= start)


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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="append", help="channel(s) to check; repeatable")
    ap.add_argument("--target", type=int, action="append", help="daily target per --chat, same order")
    ap.add_argument("--start", type=int, default=9)
    ap.add_argument("--end", type=int, default=22)
    ap.add_argument("--max-per-run", type=int, default=MAX_PER_RUN)
    ap.add_argument("--no-registry", action="store_true")
    a = ap.parse_args()
    chats = a.chat or [CHANNEL]
    targets = a.target or [DAILY_TARGET] * len(chats)
    now = datetime.now(TEHRAN)
    reg = [] if a.no_registry else new_registry_posts()
    owed = {}
    for chat, target in zip(chats, targets):
        exp, done = expected_by(now, target, a.start, a.end), posted_today(now, chat)
        owed[chat] = min(a.max_per_run, max(0, exp - done))
        print(f"{chat} tehran={now:%Y-%m-%d %H:%M} target={target} expected={exp} posted_today={done} owed={owed[chat]}")
    for ch, pid in reg:
        print(f"NEW REGISTRY POST https://t.me/{ch}/{pid}")
    posts = max(owed.values()) if owed else 0
    if reg and posts == 0:
        posts = 1
    print("POST_TO " + " ".join(f"--chat {c}" for c, n in owed.items() if n > 0 or (reg and n == 0)))
    print(f"DUE posts={posts} registry={'yes' if reg else 'no'}")


if __name__ == "__main__":
    main()
