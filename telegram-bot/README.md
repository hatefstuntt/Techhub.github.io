# TechHub daily Telegram poster

Posts daily cards to the Telegram channels **@techhubvpn** and **@techhub_ir** (the bot is admin in both) in the exact style of @techhub_ir. `send.py` posts each card to both channels by default.
The Telegram Bot API is reachable directly from the cloud session, so there is no relay.

## Files
- `templates/card.html`: one template, three layouts (`digest`, `registry`, `single`), with the TechHub logo, Vazirmatn font and footer bar.
- Single cards without a usable source photo can use `"graphic": {"label", "icons": [idcard|plane|star], "chips"}` instead of `image` (see data/news-fragment-kyc.json). Add new icons to `GFX` in the template when needed.
- `render.js`: `node render.js data.json out.png` renders a card (Playwright/Chromium).
- `prep_image.py`: crops source watermarks off article images (`--bottom 0.13` for GSMArena).
- `send.py`: `TG_BOT_TOKEN=... python3 send.py out.png caption.html --key <id>` posts a photo plus HTML caption to every channel in `DEFAULT_CHATS` and records (key, chat) in `data/posted.json` (dedup per channel).
- `data/*.example.json`, `data/digest.caption.example.html`: reference content copied from real @techhub_ir posts.

## Daily plan (12–15 posts, one per hourly run 09:07–22:07 Tehran)
- 10:07 → **digest** card (`digest`): Iran internet status (4 bullets) plus 4 short mobile/tech news tiles. Use the caption shape in `data/digest.caption.example.html`.
- 15:07 and 20:07 → **registry** price card (`registry`) if a source has posted a new customs-price table, otherwise a single-news card. Never invent or estimate a price.
- Every other hour → **single** news card (`single`): one fresh story each, with the article's real image as `image` or a `graphic` hero.
- Variety: check the last ~10 entries of `data/posted.json` and don't post two cards in a row about the same company or topic. Mix phones, Iran mobile market/registry, Telegram/apps, internet/security and AI.
- Quality over quantity: if there's no fresh, verified story, skip that hour. 12 good posts beat 14 weak ones.

## Sources (chosen by the owner)
- **t.me/s/sabregistry**: main registry source. Its "📣 آخرین لیست قیمت گمرکی" posts carry a customs-price table **image** (dated, e.g. 1405/08/10); read the image and rebuild it as a `registry` card. Its daily "رجیستری در حال انجام" posts give register/pass service fees, and its announcements (blocked models, activation-code delays) are good news items.
- **t.me/s/figofixir**: mobile repair/unlock channel. Use only general news from it; never repost cracked software, FRP/MDM/iCloud bypass tools or their download links.
- **t.me/rezatopgsmir**: the public web preview is disabled, so it can't be read from here.
- **top-gsm.ir**: blocks connections from outside Iran (connection reset / 503), so it can't be read from here.
- **t.me/s/iaghapour**: Persian tech/internet news (Telegram, Windows, apps). Usable after rewriting; its images carry its branding, so use the original article's image or a `graphic` hero instead.
- **t.me/s/asrnovin_ir**: Persian tech/security news and Iran internet outage reports (good for the digest's internet section). Skip its VPN tutorials and YouTube promos.
- **t.me/s/MatinSenPaii**: Persian AI/tech news. Usable after rewriting.
- **t.me/s/mammadturkgsm**: almost all cracked unlock tools (UnlockTool, TSM, XRY cracks). Do not use those posts; only general repair news, if any.
- **t.me/haji_part1**: only invite links, no news content. Not usable.
- Telegram-channel news is second-hand: confirm the fact with an original or reputable report (web search) before posting, and mark unofficial items as unofficial or "شایعه".
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
