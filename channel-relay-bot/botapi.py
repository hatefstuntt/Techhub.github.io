"""Minimal async Telegram Bot API client for publishing (supports expandable blockquotes and albums)."""
from __future__ import annotations

import json
import os

import httpx

MAX_UPLOAD = 49 * 1024 * 1024  # Bot API upload limit is 50 MB


class BotAPI:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20))

    async def call(self, method: str, data: dict | None = None, files: dict | None = None) -> dict:
        r = await self.http.post(self.base + method, data=data, files=files)
        try:
            res = r.json()
        except ValueError:
            return {"ok": False, "description": f"HTTP {r.status_code}"}
        return res

    async def check_no_webhook(self) -> str | None:
        """This bot must not have a webhook (another service would steal its updates)."""
        info = await self.call("getWebhookInfo")
        url = (info.get("result") or {}).get("url")
        return url or None

    async def send_post(self, chat: str, caption: str, media: list[dict], reply_markup: dict | None = None) -> dict:
        """media: [{"path": ..., "kind": "photo"|"video"|"document"}]. Caption is Telegram HTML."""
        media = [m for m in media if os.path.getsize(m["path"]) <= MAX_UPLOAD]
        base = {"chat_id": chat, "parse_mode": "HTML"}
        if reply_markup:
            base["reply_markup"] = json.dumps(reply_markup)
        if not media:
            return await self.call("sendMessage", {**base, "text": caption, "link_preview_options": json.dumps({"is_disabled": True})})
        if len(media) == 1:
            m = media[0]
            method = {"photo": "sendPhoto", "video": "sendVideo"}.get(m["kind"], "sendDocument")
            field = {"photo": "photo", "video": "video"}.get(m["kind"], "document")
            data = {**base, "caption": caption}
            if m["kind"] == "video":
                data["supports_streaming"] = "true"
            with open(m["path"], "rb") as f:
                return await self.call(method, data, {field: (os.path.basename(m["path"]), f)})
        # album: up to 10 items, caption on the first; inline buttons are not allowed on albums
        items, files = [], {}
        for i, m in enumerate(media[:10]):
            kind = m["kind"] if m["kind"] in ("photo", "video") else "document"
            item = {"type": kind, "media": f"attach://f{i}"}
            if i == 0:
                item.update(caption=caption, parse_mode="HTML")
            items.append(item)
            files[f"f{i}"] = (os.path.basename(m["path"]), open(m["path"], "rb"))
        try:
            return await self.call("sendMediaGroup", {"chat_id": chat, "media": json.dumps(items)}, files)
        finally:
            for _, fh in files.values():
                fh.close()

    async def get_updates(self, offset: int, timeout: int = 50) -> list[dict]:
        try:
            r = await self.http.post(self.base + "getUpdates", data={
                "offset": offset, "timeout": timeout,
                "allowed_updates": json.dumps(["message", "callback_query"])},
                timeout=timeout + 15)
            res = r.json()
        except (httpx.HTTPError, ValueError):
            return []
        return res.get("result", []) if res.get("ok") else []
