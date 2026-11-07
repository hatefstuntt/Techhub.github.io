#!/usr/bin/env python3
"""Send a rendered card to the Telegram channel.

Usage:
  TG_BOT_TOKEN=... python3 send.py <image.png|jpg> <caption.html> --key <dedup-key> [--chat @a --chat @b]
  Without --chat it posts to every channel in DEFAULT_CHATS.

- The caption is Telegram HTML (<b>, <i>, <a>, <blockquote>, <blockquote expandable>).
  Bot photo captions are limited to 1024 characters (after HTML tags are removed); this script refuses longer ones.
- --key is a normalized source id (e.g. "digest:1405-08-14", "registry:1405-08-14", "news:gsmarena.com/xyz-123").
  A (key, chat) pair already in data/posted.json is skipped, so the same story is never posted twice in one channel.
"""
import argparse, html, json, os, re, sys, time, urllib.request, uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "data", "posted.json")
DEFAULT_CHATS = ["@techhubvpn", "@techhub_ir"]


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
    ap.add_argument("--chat", action="append", help="repeatable; default: all DEFAULT_CHATS")
    ap.add_argument("--force", action="store_true", help="post even if the key was already posted")
    ap.add_argument("--source-post", type=int, help="registry: id of the source channel post the table came from")
    ap.add_argument("--registry-json", help="registry: the table json, stored compressed in the hidden marker as the next diff baseline")
    a = ap.parse_args()

    token = os.environ.get("TG_BOT_TOKEN")
    if not token:
        sys.exit("TG_BOT_TOKEN is not set")

    chats = a.chat or DEFAULT_CHATS
    log = load_log()
    caption = state.add_marker(open(a.caption, encoding="utf-8").read().strip(), a.key, a.source_post,
                               json.load(open(a.registry_json, encoding="utf-8")) if a.registry_json else None)
    n = visible_len(caption)
    if n > 1024:
        sys.exit(f"caption too long: {n} visible chars (max 1024)")
    img = open(a.image, "rb").read()
    ctype = "image/jpeg" if a.image.lower().endswith((".jpg", ".jpeg")) else "image/png"

    failed = False
    for chat in chats:
        # the channel itself is the source of truth (scheduled runs can't push posted.json)
        if not a.force and (state.already_posted(chat, a.key)
                            or any(r["key"] == a.key and r.get("chat") == chat for r in log)):
            print(f"SKIP already posted in {chat}: {a.key}")
            continue
        res = send_photo(token, chat, img, ctype, os.path.basename(a.image), caption)
        if not res.get("ok"):
            print(f"FAIL {chat}: {res}")
            failed = True
            continue
        mid = res["result"]["message_id"]
        urls = [e.get("url", "") for e in res["result"].get("caption_entities", [])]
        if not any(f"k={state.key_hash(a.key)}" in u for u in urls):
            print(f"WARN {chat}: hidden dedup marker missing in the sent caption; check the footer")
        log.append({"key": a.key, "chat": chat, "message_id": mid,
                    "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        with open(LOG, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)
        print(f"OK {chat} message_id={mid} key={a.key} caption_chars={n}")
    if failed:
        sys.exit(1)


def send_photo(token, chat, img, ctype, name, caption):
    body, ct = multipart({"chat_id": chat, "caption": caption, "parse_mode": "HTML"},
                         {"photo": (name, img, ctype)})
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
                                         headers={"Content-Type": ct})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return json.load(e)
        except Exception:  # network hiccup: retry
            if attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


if __name__ == "__main__":
    main()
