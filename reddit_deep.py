#!/usr/bin/env python3
"""Reddit deep paging via Arctic-Shift listing. Continues from the oldest
created_utc already stored per subreddit, pages further back in time.
Subs: depression +150p, mentalhealth +150p, depression_help +60p, anxiety +60p.
Output: data/reddit_deep.jsonl (deduped against all prior reddit files).
"""
import json, time, os
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
PLAN = {"depression": 150, "mentalhealth": 150, "depression_help": 60, "anxiety": 60}
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
    seen, oldest = set(), {}
    for fn in os.listdir(DATA):
        if fn.startswith("reddit") and fn.endswith(".jsonl"):
            for l in open(os.path.join(DATA, fn), encoding="utf-8"):
                try:
                    p = json.loads(l); seen.add(p["id"])
                    sub = p.get("subreddit"); ts = p.get("created_utc") or 0
                    if sub and ts: oldest[sub] = min(oldest.get(sub, ts), ts)
                except Exception: pass
    print("start oldest:", oldest, "seen:", len(seen))
    total = 0
    with open(os.path.join(DATA, "reddit_deep.jsonl"), "w", encoding="utf-8") as f:
        for sub, pages in PLAN.items():
            before = oldest.get(sub)
            for page in range(pages):
                params = {"subreddit": sub, "limit": LIMIT, "sort": "desc"}
                if before: params["before"] = before
                rows = fetch(params)
                if not rows: print(sub, "page", page, "empty stop"); break
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
                if page % 10 == 0: print(sub, "page", page, "total", total, "before", before)
                f.flush(); time.sleep(3)
            print(sub, "done, total", total)
    print("DEEP POSTS", total)

if __name__ == "__main__":
    main()
