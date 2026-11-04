# TechHub daily Telegram poster

Posts daily cards to the Telegram channels **@techhubvpn** and **@techhub_ir** (the bot is admin in both) in the exact style of @techhub_ir. `send.py` posts each card to both channels by default.
The Telegram Bot API is reachable directly from the cloud session, so there is no relay.

## Files
- `templates/card.html`: one template, three layouts (`digest`, `registry`, `single`), with the TechHub logo, Vazirmatn font and footer bar.
- `render.js`: `node render.js data.json out.png` renders a card (Playwright/Chromium).
- `prep_image.py`: crops source watermarks off article images (`--bottom 0.13` for GSMArena).
- `send.py`: `TG_BOT_TOKEN=... python3 send.py out.png caption.html --key <id>` posts a photo plus HTML caption to every channel in `DEFAULT_CHATS` and records (key, chat) in `data/posted.json` (dedup per channel).
- `data/*.example.json`, `data/digest.caption.example.html`: reference content copied from real @techhub_ir posts.

## Daily plan (at least 5 posts)
1. **Digest card** (`digest`): Iran internet status (4 bullets) plus 4 short mobile/tech news tiles. Use the caption shape in `data/digest.caption.example.html`.
2. **Registry price card** (`registry`): customs/registry prices read from the source channels the owner listed. Never invent or estimate a price; if no source posted today, skip this card.
3. **3 or more single-news cards** (`single`): one fresh mobile/tech story each, with the article's real image as `image` (download it first, then pass the local path).

## Sources (chosen by the owner)
- **t.me/s/sabregistry**: main registry source. Its "📣 آخرین لیست قیمت گمرکی" posts carry a customs-price table **image** (dated, e.g. 1405/08/10); read the image and rebuild it as a `registry` card. Its daily "رجیستری در حال انجام" posts give register/pass service fees, and its announcements (blocked models, activation-code delays) are good news items.
- **t.me/s/figofixir**: mobile repair/unlock channel. Use only general news from it; never repost cracked software, FRP/MDM/iCloud bypass tools or their download links.
- **t.me/rezatopgsmir**: the public web preview is disabled, so it can't be read from here.
- **top-gsm.ir**: blocks connections from outside Iran (connection reset / 503), so it can't be read from here.
- Global mobile/tech news: gsmarena.com and similar (reachable; use the article's own image).
- Fetch a public channel with `curl -sS https://t.me/s/<channel>`. Telesco.pe image downloads sometimes return a 500 error; retry 2–3 times.

Rules:
- Every story must be published in the last 24–48 h. Check the date on the article itself.
- Normalize keys: `digest:YYYY-MM-DD`, `registry:YYYY-MM-DD`, `news:<domain>/<path-without-query>`. `send.py` skips keys already posted.
- Persian, simple news tone like the reference posts. Card text uses Latin digits (as in the reference images); captions use Persian digits.
- The photo caption limit for bots is 1024 visible characters; `send.py` refuses longer captions.
- **No emoji row at the top of captions** (the owner removed it). Start directly with the bold title in a blockquote, as in `data/registry-1405-08-10.caption.html`, and end with the standard footer (support @hatefstunt, bot t.me/techhublinkbot, channel t.me/techhub_ir).
- Commit `data/posted.json` after each run so the next run sees what was already posted.

## No source branding (owner's rule)
Nothing copied from a source may carry that source's promotion:
- Remove its @handles, channel or site names, links, hashtags (`#ری_اکت`, `#اطلاع_رسانی` …), "react to our posts" lines, phone numbers and its own service prices or ads.
- Rewrite the facts in TechHub's own words; never paste a source post verbatim.
- Images: never post a source's image as-is if it has a logo, watermark, @handle or URL. Crop it off with `prep_image.py` and look at the result, or pick another image. Price tables are always rebuilt as our own `registry` card, never reposted.
- Don't put a "منبع: …" line on cards or captions.
- Never repost cracked software, FRP/MDM/iCloud bypass tools or their download links.
