# TechHub daily Telegram poster

Posts daily cards to the Telegram channel **@techhubvpn** in the exact style of @techhub_ir.
The Telegram Bot API is reachable directly from the cloud session, so there is no relay.

## Files
- `templates/card.html`: one template, three layouts (`digest`, `registry`, `single`), with the TechHub logo, Vazirmatn font and footer bar.
- `render.js`: `node render.js data.json out.png` renders a card (Playwright/Chromium).
- `send.py`: `TG_BOT_TOKEN=... python3 send.py out.png caption.html --key <id>` posts a photo plus HTML caption and records the key in `data/posted.json` (dedup).
- `data/*.example.json`, `data/digest.caption.example.html`: reference content copied from real @techhub_ir posts.

## Daily plan (at least 5 posts)
1. **Digest card** (`digest`): Iran internet status (4 bullets) plus 4 short mobile/tech news tiles. Use the caption shape in `data/digest.caption.example.html`.
2. **Registry price card** (`registry`): customs/registry prices read from the source channels the owner listed. Never invent or estimate a price; if no source posted today, skip this card.
3. **3 or more single-news cards** (`single`): one fresh mobile/tech story each, with the article's real image as `image` (download it first, then pass the local path).

Rules:
- Every story must be published in the last 24–48 h. Check the date on the article itself.
- Normalize keys: `digest:YYYY-MM-DD`, `registry:YYYY-MM-DD`, `news:<domain>/<path-without-query>`. `send.py` skips keys already posted.
- Persian, simple news tone like the reference posts. Card text uses Latin digits (as in the reference images); captions use Persian digits.
- The photo caption limit for bots is 1024 visible characters; `send.py` refuses longer captions.
- Captions start with the emoji row `🦎🦎🦎🌄🌄🌄🌄🌄` (`🦎🦎🦎🎆🎆🎆🎆🎆` for price posts) and end with the standard footer (support @hatefstunt, bot t.me/techhublinkbot, channel t.me/techhub_ir).
- Commit `data/posted.json` after each run so the next run sees what was already posted.
