"""Turn a source post into a caption in the owner's channel format.

clean_text()   strips the source's branding: @handles, links, hashtags and ad/"join us" lines.
build_caption() lays the cleaned text out as: bold title in a blockquote, body in an
               expandable blockquote, then the owner's footer (all Telegram HTML).
rewrite_with_claude() optionally rewrites the cleaned text in the owner's tone.
"""
from __future__ import annotations

import html
import re

URL_RE = re.compile(r"(?:https?://|www\.)\S+|(?<![\w@])t\.me/\S+|telegram\.me/\S+", re.I)
HANDLE_RE = re.compile(r"(?<![\w.])@[A-Za-z][A-Za-z0-9_]{3,}")
HASHTAG_RE = re.compile(r"#[\w‌]+")
# a line made only of emoji, symbols, punctuation and spaces (after cleaning)
JUNK_LINE_RE = re.compile(r"^[\W_\s‌‎‏]*$")

DEFAULT_AD_PATTERNS = [
    "ری_اکت", "ری‌اکت", "ریاکت", "react", "عضو شو", "عضو بشید", "join", "تبلیغ", "کانال ما",
    "پشتیبانی ما", "جهت ثبت سفارش", "خرید اشتراک", "لینک دانلود", "کد تخفیف", "🆔", "follow",
]

CAPTION_LIMIT = 1024


def clean_text(text: str, ad_patterns: list[str] | None = None) -> str:
    """Remove the source's branding and ads; keep the news itself."""
    patterns = [p.lower() for p in (ad_patterns if ad_patterns is not None else DEFAULT_AD_PATTERNS)]
    out = []
    for line in (text or "").splitlines():
        low = line.lower()
        if any(p in low for p in patterns):
            continue
        had_link = bool(URL_RE.search(line))
        line = URL_RE.sub("", line)
        if had_link and line.strip().endswith((":", "：")) and len(line.strip()) < 25:
            continue  # "Details:" left over after its link was removed
        line = HANDLE_RE.sub("", line)
        line = HASHTAG_RE.sub("", line)
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        if JUNK_LINE_RE.match(line):
            line = ""
        out.append(line)
    cleaned = "\n".join(out)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def split_title_body(text: str) -> tuple[str, str]:
    lines = [l for l in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return "", ""
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    return title, body


def _visible_len(s: str) -> int:
    return len(html.unescape(re.sub(r"<[^>]+>", "", s)))


def build_caption(title: str, body: str, fmt: dict) -> str:
    """Build the owner's caption. fmt keys: title_emoji, body_label, footer (list of HTML lines)."""
    emoji = fmt.get("title_emoji", "📌")
    label = fmt.get("body_label", "")
    footer = "\n".join(fmt.get("footer", []))

    def render(b: str) -> str:
        parts = []
        if title:
            parts.append(f"<blockquote>{emoji} <b>{html.escape(title)}</b></blockquote>")
        if b:
            if label:
                parts.append(label)
            parts.append(f"<blockquote expandable>{html.escape(b)}</blockquote>")
        cap = "\n".join(parts)
        return cap + ("\n" + footer if footer else "")

    cap = render(body)
    if _visible_len(cap) <= CAPTION_LIMIT:
        return cap
    # trim the body (never the title or footer) to fit Telegram's caption limit
    overflow = _visible_len(cap) - CAPTION_LIMIT
    keep = len(body) - overflow - 1
    while keep > 20:
        trimmed = body[:keep].rsplit(" ", 1)[0].rstrip("،,.;: ") + "…"
        cap = render(trimmed)
        if _visible_len(cap) <= CAPTION_LIMIT:
            return cap
        keep -= 20
    return render("")


REWRITE_SYSTEM = """You rewrite Telegram news posts for the owner's channel.
Rules:
- Write in simple, clear Persian (unless the source is in another language and the owner asked otherwise), in your own words. Keep every fact exactly as in the source; never add facts, numbers or claims.
- Remove anything that promotes the source: channel names, @handles, links, hashtags, "join/react" lines, ads, the source's own prices or services.
- If the post is a rumor or unconfirmed, say so.
- Output plain text only: the first line is a short headline (max ~70 characters, starting with a Persian word); then the body in 1-4 short sentences. No emojis, no HTML, no markdown.
- If the post is only an advertisement or has no news value, output exactly: SKIP"""


async def rewrite_with_claude(client, text: str, cfg: dict) -> str | None:
    """Rewrite cleaned text with Claude. Returns new text, "" to skip the post, or None on failure."""
    import anthropic

    style = cfg.get("style_notes", "")
    example = cfg.get("example_post", "")
    user = "Rewrite this post.\n\n"
    if style:
        user += f"Owner's style notes:\n{style}\n\n"
    if example:
        user += f"Example of a post in the owner's style:\n<example>\n{example}\n</example>\n\n"
    user += f"<post>\n{text}\n</post>"
    kwargs = dict(
        model=cfg.get("model", "claude-opus-5-5"),
        max_tokens=4000,
        system=REWRITE_SYSTEM,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": cfg.get("effort", "low")},
    )
    try:
        if cfg.get("fallbacks", True):
            # server-side refusal fallback: on a policy decline the API retries on a fallback model
            resp = await client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        else:
            resp = await client.messages.create(**kwargs)
    except anthropic.RateLimitError:
        return None
    except anthropic.APIStatusError as e:
        print(f"[rewrite] API error {e.status_code}: {e.message}")
        return None
    except anthropic.APIConnectionError:
        print("[rewrite] network error")
        return None
    if resp.stop_reason == "refusal":
        return None
    out = "".join(b.text for b in resp.content if b.type == "text").strip()
    if out == "SKIP":
        return ""
    return out or None
