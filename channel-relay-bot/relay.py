#!/usr/bin/env python3
"""Channel relay bot: watches the Telegram channels you list, downloads their posts (text, photos,
videos, albums), turns them into your channel's format and publishes them in your channel.

Reading uses YOUR Telegram account (Telethon, api_id/api_hash from my.telegram.org), so it can read
any channel you have joined. Publishing and approval buttons use a bot (Bot API) that is admin in
your channel. Run:  python3 relay.py config.yaml
"""
from __future__ import annotations

import asyncio
import html
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import yaml
from telethon import TelegramClient, events

from botapi import BotAPI
from formatter import build_caption, clean_text, rewrite_with_claude, split_title_body, DEFAULT_AD_PATTERNS
from media import brand_image
from store import Store

TEHRAN = timezone(timedelta(hours=3, minutes=30))


def log(*a):
    print(datetime.now(TEHRAN).strftime("%m-%d %H:%M:%S"), *a, flush=True)


class Relay:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        os.makedirs(cfg.get("data_dir", "data"), exist_ok=True)
        self.dir = cfg.get("data_dir", "data")
        self.store = Store(os.path.join(self.dir, "relay.db"))
        tg = cfg["telegram"]
        self.client = TelegramClient(os.path.join(self.dir, "user"), int(tg["api_id"]), tg["api_hash"])
        self.bot = BotAPI(tg["bot_token"])
        self.owner = int(tg["owner_id"])
        self.targets = cfg["targets"]
        self.sources = {s["channel"].lstrip("@").lower(): s for s in cfg["sources"]}
        self.sched = cfg.get("schedule", {})
        self.fmt = cfg.get("format", {})
        self.filters = cfg.get("filters", {})
        self.rw = cfg.get("rewrite", {})
        self.claude = None
        if self.rw.get("enabled"):
            import anthropic
            self.claude = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY
        self.approval = bool(self.sched.get("approval", True))
        self.lock = asyncio.Lock()

    # ---------------- collecting ----------------
    def _source_for(self, chat) -> dict | None:
        name = (getattr(chat, "username", None) or "").lower()
        return self.sources.get(name)

    def _passes_filters(self, text: str, src: dict) -> bool:
        f = {**self.filters, **src.get("filters", {})}
        low = text.lower()
        if len(text.strip()) < int(f.get("min_text_length", 0)):
            return False
        inc = [k.lower() for k in f.get("include_keywords", [])]
        if inc and not any(k in low for k in inc):
            return False
        exc = [k.lower() for k in f.get("exclude_keywords", [])]
        return not any(k in low for k in exc)

    async def handle(self, chat, messages: list):
        src = self._source_for(chat)
        if not src:
            return
        first = messages[0]
        key = f"{src['channel'].lstrip('@').lower()}:{first.grouped_id or first.id}"
        async with self.lock:
            if self.store.seen(key):
                return
            self.store.mark_seen(key)
        if self.filters.get("skip_forwards", True) and first.fwd_from:
            return log("skip forward", key)
        raw = next((m.message for m in messages if m.message), "") or ""
        if not self._passes_filters(raw, src):
            return log("skip filtered", key)
        text = clean_text(raw, self.filters.get("ad_patterns", DEFAULT_AD_PATTERNS))
        if self.claude and text:
            new = await rewrite_with_claude(self.claude, text, self.rw)
            if new == "":
                return log("skip (Claude: ad / no news)", key)
            if new:
                text = new
        if not text and self.filters.get("require_text", True):
            return log("skip empty text", key)
        if self.store.duplicate_text(text):
            return log("skip duplicate story", key)
        media = await self._download(messages, src, key)
        if self.filters.get("require_media", False) and not media:
            return log("skip no media", key)
        title, body = split_title_body(text)
        caption = build_caption(title, body, self.fmt)
        qid = self.store.enqueue(src["channel"], key, title, body, caption, media)
        log(f"queued #{qid} from {key} ({len(media)} media)")
        if self.approval:
            await self._send_preview(qid)

    async def _download(self, messages, src, key) -> list[dict]:
        out, folder = [], os.path.join(self.dir, "media", key.replace(":", "_"))
        os.makedirs(folder, exist_ok=True)
        max_mb = float(self.filters.get("max_video_mb", 49))
        for m in messages:
            try:
                if m.photo:
                    p = await self.client.download_media(m, file=os.path.join(folder, f"{m.id}_src.jpg"))
                    dst = os.path.join(folder, f"{m.id}.jpg")
                    brand = {**self.cfg.get("branding", {}), **src.get("branding", {})}
                    brand_image(p, dst, brand.get("crop_top", 0), brand.get("crop_bottom", 0),
                                brand.get("logo"), brand.get("logo_corner", "bottom-left"),
                                brand.get("logo_width", 0.18), brand.get("logo_opacity", 0.9))
                    out.append({"path": dst, "kind": "photo"})
                elif m.video or (m.document and (m.document.mime_type or "").startswith("video/")):
                    if m.document.size > max_mb * 1024 * 1024:
                        log(f"skip video over {max_mb} MB in {key}")
                        continue
                    p = await self.client.download_media(m, file=os.path.join(folder, f"{m.id}.mp4"))
                    out.append({"path": p, "kind": "video"})
            except Exception as e:  # one bad file must not drop the post
                log("download failed", key, m.id, e)
        return out

    # ---------------- approval ----------------
    async def _send_preview(self, qid: int):
        row = self.store.get(qid)
        media = json.loads(row["media"])
        res = await self.bot.send_post(str(self.owner), row["caption"], media)
        if not res.get("ok"):
            log("preview failed", res)
        buttons = {"inline_keyboard": [[{"text": "✅ انتشار", "callback_data": f"ok:{qid}"},
                                        {"text": "❌ رد", "callback_data": f"no:{qid}"}]]}
        await self.bot.call("sendMessage", {"chat_id": self.owner, "reply_markup": json.dumps(buttons),
                                            "text": f"پست #{qid} از {row['source']} — منتشر بشه؟"})

    async def updates_loop(self):
        offset = int(self.store.kv_get("offset", 0))
        while True:
            for u in await self.bot.get_updates(offset):
                offset = u["update_id"] + 1
                self.store.kv_set("offset", offset)
                try:
                    await self._on_update(u)
                except Exception as e:
                    log("update error", e)

    async def _on_update(self, u: dict):
        if "callback_query" in u:
            cq = u["callback_query"]
            if cq["from"]["id"] != self.owner:
                return await self.bot.call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "اجازه ندارید"})
            act, qid = cq["data"].split(":")
            status = "approved" if act == "ok" else "rejected"
            self.store.set_status(int(qid), status)
            note = "✅ تأیید شد؛ در نوبت انتشار" if act == "ok" else "❌ رد شد"
            await self.bot.call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": note})
            m = cq.get("message") or {}
            if m:
                await self.bot.call("editMessageText", {"chat_id": m["chat"]["id"], "message_id": m["message_id"],
                                                        "text": f"پست #{qid}: {note}"})
            if act == "ok" and self.sched.get("publish_on_approve", False):
                await self.publish(int(qid))
            return
        msg = u.get("message") or {}
        if (msg.get("from") or {}).get("id") != self.owner:
            return
        cmd = (msg.get("text") or "").strip().split()[0] if msg.get("text") else ""
        reply = None
        if cmd == "/status":
            c = self.store.counts()
            paused = self.store.kv_get("paused", "0") == "1"
            reply = (f"وضعیت: {'متوقف' if paused else 'فعال'}\n"
                     f"امروز منتشر شده: {self.store.posted_since(self._day_start())} از {self.sched.get('posts_per_day', 1)}\n"
                     f"صف: {json.dumps(c, ensure_ascii=False)}")
        elif cmd == "/pause":
            self.store.kv_set("paused", 1); reply = "⏸ انتشار متوقف شد."
        elif cmd == "/resume":
            self.store.kv_set("paused", 0); reply = "▶️ انتشار ادامه پیدا کرد."
        elif cmd == "/now":
            row = self.store.next_ready(self._ready_statuses())
            reply = "پستی آماده نیست." if not row else None
            if row:
                await self.publish(row["id"])
        elif cmd in ("/start", "/help"):
            reply = "/status وضعیت\n/pause توقف انتشار\n/resume ادامه\n/now انتشار پست بعدی همین الان"
        if reply:
            await self.bot.call("sendMessage", {"chat_id": self.owner, "text": reply})

    # ---------------- publishing ----------------
    def _ready_statuses(self):
        return ("approved",) if self.approval else ("pending",)

    def _day_start(self) -> float:
        now = datetime.now(TEHRAN)
        return now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

    def slots_due(self, now: datetime) -> int:
        """How many posts should be out by now: posts_per_day spread evenly from start_hour to end_hour."""
        n = int(self.sched.get("posts_per_day", 1))
        start, end = int(self.sched.get("start_hour", 12)), int(self.sched.get("end_hour", 12))
        if n <= 0:
            return 0
        times = [start + (end - start) * i / max(1, n - 1) for i in range(n)] if n > 1 else [start]
        hour = now.hour + now.minute / 60
        return sum(1 for t in times if hour >= t)

    async def publish(self, qid: int):
        row = self.store.get(qid)
        if not row or row["status"] == "posted":
            return
        media = [m for m in json.loads(row["media"]) if os.path.exists(m["path"])]
        results, ok = [], True
        for chat in self.targets:
            res = await self.bot.send_post(chat, row["caption"], media)
            ok = ok and res.get("ok", False)
            results.append({chat: res.get("ok"), "error": res.get("description")})
        self.store.set_status(qid, "posted" if ok else "failed", json.dumps(results, ensure_ascii=False))
        log(f"publish #{qid}:", results)
        if not ok:
            await self.bot.call("sendMessage", {"chat_id": self.owner,
                                                "text": f"⚠️ انتشار پست #{qid} ناموفق بود: {html.escape(str(results))[:500]}"})

    async def scheduler_loop(self):
        max_age = float(self.sched.get("max_age_hours", 24)) * 3600
        while True:
            try:
                if self.store.kv_get("paused", "0") != "1":
                    now = datetime.now(TEHRAN)
                    if self.store.posted_since(self._day_start()) < self.slots_due(now):
                        row = self.store.next_ready(self._ready_statuses())
                        while row and time.time() - row["created"] > max_age:
                            self.store.set_status(row["id"], "rejected", "too old")
                            row = self.store.next_ready(self._ready_statuses())
                        if row:
                            await self.publish(row["id"])
            except Exception as e:
                log("scheduler error", e)
            await asyncio.sleep(30)

    # ---------------- startup ----------------
    async def backfill(self):
        n = int(self.cfg.get("backfill_per_source", 5))
        for name, src in self.sources.items():
            try:
                ent = await self.client.get_entity(name)
                msgs = await self.client.get_messages(ent, limit=n)
            except Exception as e:
                log(f"cannot read @{name}: {e}")
                continue
            groups: dict = {}
            for m in reversed(msgs):
                groups.setdefault(m.grouped_id or m.id, []).append(m)
            for g in groups.values():
                await self.handle(ent, g)

    async def run(self):
        hook = await self.bot.check_no_webhook()
        if hook:
            sys.exit(f"This bot has a webhook ({hook}). Use a separate bot just for this relay, "
                     "otherwise approval buttons and commands can't reach it.")
        await self.client.start()  # first run asks for your phone number and login code
        chats = list(self.sources)

        @self.client.on(events.NewMessage(chats=chats))
        async def on_new(ev):
            if ev.message.grouped_id:
                return  # albums arrive through events.Album
            await self.handle(await ev.get_chat(), [ev.message])

        @self.client.on(events.Album(chats=chats))
        async def on_album(ev):
            await self.handle(await ev.get_chat(), list(ev.messages))

        await self.backfill()
        log(f"watching {len(chats)} channels → {', '.join(self.targets)}; "
            f"{self.sched.get('posts_per_day', 1)} post(s)/day; approval={'on' if self.approval else 'off'}")
        await asyncio.gather(self.client.run_until_disconnected(), self.scheduler_loop(), self.updates_loop())


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    asyncio.run(Relay(cfg).run())


if __name__ == "__main__":
    main()
