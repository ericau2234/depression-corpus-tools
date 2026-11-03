#!/usr/bin/env python3
"""Reddit corpus via Arctic-Shift public archive API (no account / no OAuth).

Live-proven 2026-11-03: https://arctic-shift.photon-reddit.com/api/posts/search
Reddit's own .json endpoints return 403 from this network; the archive mirrors
Pushshift-style data. Rate limits: keep >=2.5s between calls, small pages.
Stores: data/reddit_posts.jsonl  (fields trimmed to research-relevant ones)
"""
import json, time, os
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
API = "https://arctic-shift.photon-reddit.com/api/posts/search"

QUERIES = [
    ("depression", "why am I depressed"),
    ("depression", "what caused your depression"),
    ("depression", "depressed for no reason"),
    ("depression", "my depression started"),
    ("depression", "childhood trauma depression"),
    ("mentalhealth", "what caused your depression"),
    ("depression", "lost my job depressed"),
    ("depression", "lonely depressed"),
]
LIMIT = 100  # per query

def fetch(params, tries=5):
    for a in range(tries):
        try:
            r = requests.get(API, params=params, headers=H, timeout=45)
            if r.status_code == 200:
                return (r.json() or {}).get("data") or []
            print("http", r.status_code, r.text[:120])
        except Exception as e:
            print("net retry", a, type(e).__name__)
        time.sleep(4 * (a + 1))
    return []

def main():
    seen, total = set(), 0
    with open(os.path.join(DATA, "reddit_posts.jsonl"), "w", encoding="utf-8") as f:
        for sub, q in QUERIES:
            rows = fetch({"subreddit": sub, "query": q, "limit": LIMIT})
            kept = 0
            for p in rows:
                pid = p.get("id")
                if not pid or pid in seen: continue
                seen.add(pid)
                rec = {"id": pid, "subreddit": sub, "query": q, "author": p.get("author"),
                       "title": p.get("title"), "selftext": p.get("selftext"),
                       "score": p.get("score"), "num_comments": p.get("num_comments"),
                       "created_utc": p.get("created_utc"), "url": "https://www.reddit.com" + (p.get("permalink") or "")}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1; total += 1
            print(f"query done r/{sub} '{q}': fetched={len(rows)} kept={kept} total={total}")
            time.sleep(3)
    print("POSTS", total)

if __name__ == "__main__":
    main()
