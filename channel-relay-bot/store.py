"""SQLite state: seen source posts, the post queue, and daily counters."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time

SCHEMA = """
create table if not exists seen (key text primary key, at real);
create table if not exists textsig (sig text primary key, at real);
create table if not exists queue (
  id integer primary key autoincrement,
  source text, key text unique, title text, body text, caption text,
  media text,            -- json list of {"path","kind"}
  status text,           -- pending | approved | posted | rejected | failed
  created real, posted real, result text
);
create table if not exists kv (k text primary key, v text);
"""


def text_signature(text: str) -> str:
    """Same news from two channels -> same signature (letters/digits only, first 300 chars)."""
    norm = re.sub(r"[\W_]+", "", (text or "").lower())[:300]
    return hashlib.sha1(norm.encode()).hexdigest() if len(norm) >= 40 else ""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    # dedup
    def seen(self, key: str) -> bool:
        return self.db.execute("select 1 from seen where key=?", (key,)).fetchone() is not None

    def mark_seen(self, key: str):
        self.db.execute("insert or ignore into seen values (?,?)", (key, time.time()))
        self.db.commit()

    def duplicate_text(self, text: str) -> bool:
        sig = text_signature(text)
        if not sig:
            return False
        if self.db.execute("select 1 from textsig where sig=?", (sig,)).fetchone():
            return True
        self.db.execute("insert into textsig values (?,?)", (sig, time.time()))
        self.db.commit()
        return False

    # queue
    def enqueue(self, source, key, title, body, caption, media, status="pending") -> int:
        cur = self.db.execute(
            "insert or ignore into queue (source,key,title,body,caption,media,status,created) values (?,?,?,?,?,?,?,?)",
            (source, key, title, body, caption, json.dumps(media), status, time.time()))
        self.db.commit()
        return cur.lastrowid

    def get(self, qid: int):
        return self.db.execute("select * from queue where id=?", (qid,)).fetchone()

    def set_status(self, qid: int, status: str, result: str = ""):
        posted = time.time() if status == "posted" else None
        self.db.execute("update queue set status=?, result=?, posted=coalesce(?,posted) where id=?",
                        (status, result, posted, qid))
        self.db.commit()

    def next_ready(self, statuses=("pending",)):
        q = "select * from queue where status in (%s) order by created desc limit 1" % ",".join("?" * len(statuses))
        return self.db.execute(q, statuses).fetchone()

    def posted_since(self, ts: float) -> int:
        return self.db.execute("select count(*) from queue where status='posted' and posted>=?", (ts,)).fetchone()[0]

    def counts(self) -> dict:
        return {r["status"]: r["n"] for r in self.db.execute("select status, count(*) n from queue group by status")}

    # small key/value (last update offset, paused flag)
    def kv_get(self, k, default=None):
        r = self.db.execute("select v from kv where k=?", (k,)).fetchone()
        return r["v"] if r else default

    def kv_set(self, k, v):
        self.db.execute("insert into kv values (?,?) on conflict(k) do update set v=excluded.v", (k, str(v)))
        self.db.commit()
