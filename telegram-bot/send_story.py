#!/usr/bin/env python3
"""Render a 1080x1920 story from a posted card and send it to the owner's private chat,
so the owner can share it as a channel story (bots can't post channel stories).

Usage: TG_BOT_TOKEN=... python3 send_story.py <card.jpg> "<title>" "<tag>" "<one-line note for the owner>"
"""
import json, os, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from send import multipart

OWNER_CHAT = "1010355565"  # @Hatefstunt, creator of @techhubvpn and @techhub_ir

card, title, tag = sys.argv[1:4]
note = sys.argv[4] if len(sys.argv) > 4 else ""
here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "out", "story-" + os.path.basename(card))
subprocess.run(["node", os.path.join(here, "story.js"), card, out, title, tag], check=True)
caption = f"📲 استوری آماده: {title}\n{note}\nبرای استوری: عکس را باز کنید ← Share ← Story".strip()
body, ct = multipart({"chat_id": OWNER_CHAT, "caption": caption},
                     {"photo": (os.path.basename(out), open(out, "rb").read(), "image/jpeg")})
req = urllib.request.Request(f"https://api.telegram.org/bot{os.environ['TG_BOT_TOKEN']}/sendPhoto",
                             data=body, headers={"Content-Type": ct})
try:
    r = json.load(urllib.request.urlopen(req, timeout=60))
except urllib.error.HTTPError as e:
    r = json.load(e)
print("STORY OK" if r.get("ok") else f"STORY FAIL {r}")
sys.exit(0 if r.get("ok") else 1)
