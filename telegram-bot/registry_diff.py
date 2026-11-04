#!/usr/bin/env python3
"""Compare a freshly transcribed customs-price table with the last one we posted.

Usage:
  python3 registry_diff.py data/registry-new.json            # compare with data/registry-latest.json
  python3 registry_diff.py data/registry-new.json --mark     # also write ▲/▼/new markers into the new json
  python3 registry_diff.py data/registry-new.json --accept   # after posting: make it the new registry-latest.json

Exit code 0 = prices differ (post an update), 3 = identical (don't post).
Prints the key to use with send.py: registry:<sha8 of all model/price pairs>.
"""
import argparse, hashlib, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LATEST = os.path.join(HERE, "data", "registry-latest.json")


def norm_price(p):
    return "".join(ch for ch in str(p) if ch.isdigit())


def rows(d):
    out = {}
    for g in d["groups"]:
        for r in g["rows"]:
            out[r[0].strip().lower()] = norm_price(r[1])
    return out


def key_of(d):
    items = sorted(rows(d).items())
    return "registry:" + hashlib.sha256(json.dumps(items).encode()).hexdigest()[:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new")
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("--accept", action="store_true")
    a = ap.parse_args()

    new = json.load(open(a.new, encoding="utf-8"))
    if a.accept:
        shutil.copyfile(a.new, LATEST)
        print(f"registry-latest.json <- {a.new}")
        return

    old = json.load(open(LATEST, encoding="utf-8")) if os.path.exists(LATEST) else {"groups": []}
    o, n = rows(old), rows(new)
    changes = []
    for m, p in n.items():
        if m not in o:
            changes.append((m, None, p))
        elif o[m] != p:
            changes.append((m, o[m], p))
    removed = [m for m in o if m not in n]

    for m, before, after in changes:
        print(f"CHANGED {m}: {before or 'new'} -> {after or '—'}")
    for m in removed:
        print(f"REMOVED {m}")
    print("KEY", key_of(new))

    if a.mark:
        ch = {m: (b, aft) for m, b, aft in changes}
        for g in new["groups"]:
            for r in g["rows"]:
                k = r[0].strip().lower()
                r[2:] = []
                if k in ch:
                    b, aft = ch[k]
                    if b is None:
                        r.append("new")
                    elif b and aft:
                        r.append("up" if int(aft) > int(b) else "down")
        json.dump(new, open(a.new, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sys.exit(0 if (changes or removed) else 3)


if __name__ == "__main__":
    main()
