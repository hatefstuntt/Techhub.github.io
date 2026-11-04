#!/usr/bin/env python3
"""Send a rendered card to the Telegram channel.

Usage:
  TG_BOT_TOKEN=... python3 send.py <image.png|jpg> <caption.html> --key <dedup-key> [--chat @techhubvpn]

- The caption is Telegram HTML (<b>, <i>, <a>, <blockquote>, <blockquote expandable>).
  Bot photo captions are limited to 1024 characters (after HTML tags are removed); this script refuses longer ones.
- --key is a normalized source id (e.g. "digest:1405-08-14", "registry:1405-08-14", "news:gsmarena.com/xyz-123").
  Keys already in data/posted.json are skipped, so the same story is never posted twice.
"""
import argparse, html, json, os, re, sys, time, urllib.request, uuid
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "posted.json")


def visible_len(caption_html: str) -> int:
    return len(html.unescape(re.sub(r"<[^>]+>", "", caption_html)))


def load_log():
    try:
        with open(LOG, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n".encode()
        out += str(v).encode("utf-8") + b"\r\n"
    for k, (name, data, ctype) in files.items():
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n").encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("caption")
    ap.add_argument("--key", required=True)
    ap.add_argument("--chat", default=os.environ.get("TG_CHAT", "@techhubvpn"))
    ap.add_argument("--force", action="store_true", help="post even if the key was already posted")
    a = ap.parse_args()

    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        sys.exit("TG_BOT_TOKEN is not set")

    log = load_log()
    if not a.force and any(r["key"] == a.key for r in log):
        print(f"SKIP already posted: {a.key}")
        return

    caption = open(a.caption, encoding="utf-8").read().strip()
    n = visible_len(caption)
    if n > 1024:
        sys.exit(f"caption too long: {n} visible chars (max 1024)")

    img = open(a.image, "rb").read()
    ctype = "image/jpeg" if a.image.lower().endswith((".jpg", ".jpeg")) else "image/png"
    body, ct = multipart({"chat_id": a.chat, "caption": caption, "parse_mode": "HTML"},
                         {"photo": (os.path.basename(a.image), img, ctype)})

    for attempt in range(3):
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
                                         headers={"Content-Type": ct})
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.load(r)
            break
        except urllib.error.HTTPError as e:
            res = json.load(e)
            break
        except Exception as e:  # network hiccup: retry
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))

    if not res.get("ok"):
        sys.exit(f"Telegram error: {res}")

    mid = res["result"]["message_id"]
    log.append({"key": a.key, "chat": a.chat, "message_id": mid,
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    with open(LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    print(f"OK posted message_id={mid} key={a.key} caption_chars={n}")


if __name__ == "__main__":
    main()
