"""Channel-based state: the channel itself is the source of truth for what was already posted.

Scheduled runs can't push to git, so data/posted.json is NOT reliable across runs.
Every caption carries a hidden marker in its footer link: https://t.me/techhub_ir?k=<hash>[&s=<registry source post id>]
and we read it back from the public preview at https://t.me/s/<channel>.
"""
import base64, hashlib, html, json, re, urllib.parse, urllib.request, zlib
from datetime import datetime, timezone, timedelta

TEHRAN = timezone(timedelta(hours=3, minutes=30))
FOOTER_PLAIN = "<blockquote>t.me/techhub_ir</blockquote>"


def key_hash(key: str) -> str:
    return hashlib.sha1(key.strip().encode()).hexdigest()[:10]


def pack_prices(registry: dict) -> str:
    rows = {r[0].strip().lower(): "".join(ch for ch in str(r[1]) if ch.isdigit())
            for g in registry["groups"] for r in g["rows"]}
    return base64.urlsafe_b64encode(zlib.compress(json.dumps(rows, separators=(",", ":")).encode(), 9)).decode().rstrip("=")


def unpack_prices(packed: str) -> dict:
    packed += "=" * (-len(packed) % 4)
    return json.loads(zlib.decompress(base64.urlsafe_b64decode(packed)))


def add_marker(caption: str, key: str, source_post: int | None = None, registry: dict | None = None) -> str:
    q = f"k={key_hash(key)}" + (f"&amp;s={source_post}" if source_post else "")
    if registry:
        q += f"&amp;p={pack_prices(registry)}"
    link = f'<blockquote><a href="https://t.me/techhub_ir?{q}">t.me/techhub_ir</a></blockquote>'
    if FOOTER_PLAIN not in caption:
        raise SystemExit("caption must end with the standard footer line " + FOOTER_PLAIN)
    return caption.replace(FOOTER_PLAIN, link)


def fetch_recent(chat: str, pages: int = 3):
    """Newest-last list of {id, time (Tehran), text, hrefs} from the channel's public preview."""
    name = chat.lstrip("@")
    posts, before = {}, None
    for _ in range(pages):
        url = f"https://t.me/s/{name}" + (f"?before={before}" if before else "")
        page = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "ignore")
        chunks = page.split('class="tgme_widget_message_wrap')[1:]
        if not chunks:
            break
        for c in chunks:
            m = re.search(r'data-post="[^/]+/(\d+)"', c)
            d = re.search(r'datetime="([^"]+)"', c)
            if not m:
                continue
            t = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', c, re.S)
            raw = t.group(1) if t else ""
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", "\n", raw)))
            posts[int(m.group(1))] = {
                "id": int(m.group(1)),
                "time": datetime.fromisoformat(d.group(1)).astimezone(TEHRAN) if d else None,
                "text": re.sub(r"[ \t]+", " ", text).strip(),
                "hrefs": [html.unescape(h) for h in re.findall(r'href="([^"]+)"', raw)],
            }
        before = min(p for p in posts)
    return [posts[k] for k in sorted(posts)]


def already_posted(chat: str, key: str) -> bool:
    h = f"k={key_hash(key)}"
    return any(h in href for p in fetch_recent(chat) for href in p["hrefs"])


def last_registry_source_id(chat: str = "@techhubvpn") -> int:
    ids = [int(m.group(1)) for p in fetch_recent(chat, pages=8) for href in p["hrefs"]
           for m in [re.search(r"[?&]s=(\d+)", href)] if m]
    return max(ids) if ids else 0


def last_registry_prices(chat: str = "@techhubvpn"):
    """Prices of the newest registry card we posted, read back from its hidden p= marker (or None)."""
    for p in reversed(fetch_recent(chat, pages=8)):
        for href in p["hrefs"]:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if "p" in q:
                return unpack_prices(q["p"][0])
    return None
