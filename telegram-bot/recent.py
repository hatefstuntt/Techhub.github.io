#!/usr/bin/env python3
"""Print the channel's recent posts (Tehran time + first lines) to avoid repeating a story or topic.
Usage: python3 recent.py [@techhubvpn] [count]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state
chat = sys.argv[1] if len(sys.argv) > 1 else "@techhubvpn"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
for p in state.fetch_recent(chat)[-n:]:
    first = " | ".join(l.strip() for l in p["text"].splitlines() if l.strip())[:150]
    print(f'{p["id"]} {p["time"]:%m-%d %H:%M} {first}')
