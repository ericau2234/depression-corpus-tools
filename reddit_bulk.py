#!/usr/bin/env python3
"""Reddit bulk via Arctic-Shift listing (no query param - full-text query times out server-side).
Pages backwards with before=<oldest created_utc>. Local filtering happens in analysis.
Appends to data/reddit_bulk.jsonl, dedups vs data/reddit_posts.jsonl ids.
"""
import json, time, os
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
SUBS = ["depression", "mentalhealth"]
PAGES = 25          # 25 x 100 = up to 2500 posts per sub
LIMIT = 100

def fetch(params, tries=4):
    for a in range(tries):
        try:
            r = requests.get(API, params=params, headers=H, timeout=60)
            if r.status_code == 200:
                return (r.json() or {}).get("data") or []
            print("http", r.status_code)
        except Exception as e:
            print("net retry", a, type(e).__name__)
        time.sleep(5 * (a + 1))
    return []

def main():
    seen = set()
    for fn in ["reddit_posts.jsonl"]:
        p = os.path.join(DATA, fn)
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                try: seen.add(json.loads(l)["id"])
                except Exception: pass
    total = 0
    with open(os.path.join(DATA, "reddit_bulk.jsonl"), "w", encoding="utf-8") as f:
        for sub in SUBS:
            before = None
            for page in range(PAGES):
                params = {"subreddit": sub, "limit": LIMIT, "sort": "desc"}
                if before: params["before"] = before
                rows = fetch(params)
                if not rows:
                    print(sub, "page", page, "empty, stop"); break
                kept = 0
                for p in rows:
                    pid = p.get("id")
                    if not pid or pid in seen: continue
                    seen.add(pid)
                    f.write(json.dumps({"id": pid, "subreddit": sub, "author": p.get("author"),
                                        "title": p.get("title"), "selftext": p.get("selftext"),
                                        "score": p.get("score"), "num_comments": p.get("num_comments"),
                                        "created_utc": p.get("created_utc"),
                                        "url": "https://www.reddit.com" + (p.get("permalink") or "")},
                                       ensure_ascii=False) + "\n")
                    kept += 1; total += 1
                before = min((p.get("created_utc") or 0) for p in rows)
                print(sub, "page", page, "fetched", len(rows), "kept", kept, "total", total, "before", before)
                f.flush()
                time.sleep(3)
    print("BULK POSTS", total)

if __name__ == "__main__":
    main()
