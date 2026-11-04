# TechHub daily Telegram poster

Posts daily cards to the Telegram channels **@techhubvpn** and **@techhub_ir** (the bot is admin in both) in the exact style of @techhub_ir. `send.py` posts each card to both channels by default.
The Telegram Bot API is reachable directly from the cloud session, so there is no relay.

## Files
- `templates/card.html`: one template, three layouts (`digest`, `registry`, `single`), with the TechHub logo, Vazirmatn font and footer bar.
- Single cards without a usable source photo can use `"graphic": {"label", "icons": [idcard|plane|star], "chips"}` instead of `image` (see data/news-fragment-kyc.json). Add new icons to `GFX` in the template when needed.
- `render.js`: `node render.js data.json out.png` renders a card (Playwright/Chromium).
- `prep_image.py`: crops source watermarks off article images (`--bottom 0.13` for GSMArena).
- `registry_diff.py`: compares a newly transcribed price table with `data/registry-latest.json`, marks ▲/▼/جدید rows, prints the dedup key and accepts the posted table as the new latest.
- `send_story.py`: `python3 send_story.py out/card.jpg "<title>" "<tag>" "<note>"` renders a 1080x1920 story (story.js + templates/story.html) and sends it to the owner's PV (chat 1010355565). The owner shares it as a channel story manually, since bots can't post channel stories. Never delete or change the bot's webhook (telemob.ir): another service uses this bot.
- `send.py`: `TG_BOT_TOKEN=... python3 send.py out.png caption.html --key <id>` posts a photo plus HTML caption to every channel in `DEFAULT_CHATS` and records (key, chat) in `data/posted.json` (dedup per channel).
- `data/*.example.json`, `data/digest.caption.example.html`: reference content copied from real @techhub_ir posts.

## Daily plan (12–15 posts, one per hourly run 09:07–22:07 Tehran)
- 10:07 → **digest** card (`digest`): Iran internet status (4 bullets) plus 4 short mobile/tech news tiles. Use the caption shape in `data/digest.caption.example.html`.
- 15:07 and 20:07 → **registry** price card (`registry`) if a source has posted a new customs-price table, otherwise a single-news card. Never invent or estimate a price.
- Every other hour → **single** news card (`single`): one fresh story each, with the article's real image as `image` or a `graphic` hero.
- Variety: check the last ~10 entries of `data/posted.json` and don't post two cards in a row about the same company or topic. Mix phones, Iran mobile market/registry, Telegram/apps, internet/security and AI.
- Quality over quantity: if there's no fresh, verified story, skip that hour. 12 good posts beat 14 weak ones.

## Stories (sent to the owner's PV)
- After every registry price update post: `send_story.py` with tag "به‌روزرسانی قیمت" and title "لیست جدید قیمت گمرکی".
- Plus about 3 a day for the most interesting news posts, best picked at the 12:07, 17:07 and 21:07 runs, with tag "خبر داغ" and a short (max ~30 chars) Persian title.
- Send the story only after the channel post succeeded.

## Registry watch (every run, before anything else)
The owner wants the price list updated whenever any source posts a table that differs from our last one, even in a single model, at any hour.
1. Check t.me/s/sabregistry and every other registry source in this file for customs-price table images posted since `data/registry-latest.json` was last accepted (see its `pills` date and the git log).
2. Transcribe the newest table into `data/registry-<jalali-date>[-HHMM].json` (same shape as registry-latest.json). Download and upscale the image and double-check every row. Never guess a price.
3. Run `python3 registry_diff.py <new.json> --mark`. Exit code 3 means identical, so do nothing. Exit code 0 means prices changed: render it, add the note line "▲ گران‌تر / ▼ ارزان‌تر نسبت به لیست قبل", caption as in data/registry-1405-08-10.caption.html with a line saying how many models changed, send with `--key` = the printed KEY, then run `python3 registry_diff.py <new.json> --accept` and commit.
4. A price update replaces that hour's planned post (still one post per run).

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
### World sources: scan them all every run (all tested as reachable from the cloud session)
Don't limit yourself to the owner's channels. On each run, skim the latest items from these and pick the most important, freshest story that fits the channel and isn't posted yet:
- **Phones**: gsmarena.com/rss-news-reviews.php3, androidauthority.com/feed/, 9to5google.com/feed/, 9to5mac.com/feed/, macrumors.com (follow the redirect), gizmochina.com/feed/, notebookcheck.net/News.152.100.html
- **General tech**: theverge.com/rss/index.xml, techcrunch.com/feed/, engadget.com/rss.xml, feeds.arstechnica.com/arstechnica/index, wired.com/feed/rss
- **Official newsrooms**: apple.com/newsroom/rss-feed.rss, news.samsung.com/global/feed, blog.google/rss/, telegram.org/blog
- **Persian / Iran** (Iranian websites block foreign connections, so use their Telegram previews): t.me/s/digiato (tech), t.me/s/khabaronline_ir and t.me/s/irna_1313 (official Iran news: customs/registry rules, telecom decisions; take only tech/mobile/internet items), feeds.bbci.co.uk/persian/rss.xml, techrasa.com/feed/
- **Internet status in Iran** (for the digest): t.me/s/netblocks and netblocks.org/reports, plus t.me/s/asrnovin_ir outage reports
- **Search**: use web search for breaking news and to confirm anything taken from a Telegram channel.
- Blocked from here (don't waste time): zoomit.ir, digiato.com, isna/irna websites, sammobile, phonearena, bleepingcomputer, reuters, xda, androidpolice, radar.cloudflare.com.
- Stay on topic: technology, phones, internet, apps and AI only. Never post political news, even from news agencies.
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
