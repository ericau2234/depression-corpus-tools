#!/usr/bin/env python3
"""Reddit wave 3: international-language subs via Arctic-Shift (PT desabafos/desabafo, ES depresion, FR depressionfr)."""
import requests, json, os, time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
H = {"User-Agent": "research-corpus/1.0"}
SUBS = {"desabafos": 70, "desabafo": 40, "depresion": 40, "depressionfr": 25}
FIELDS = ["id", "subreddit", "author", "title", "selftext", "score", "num_comments", "created_utc", "url"]

def fetch(params, tries=6):
    for a in range(tries):
        try:
            r = requests.get(API, params=params, headers=H, timeout=60)
            if r.status_code == 200: return r.json().get("data") or []
            time.sleep(4 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def main():
    out = open(os.path.join(DATA, "reddit_wave3.jsonl"), "w", encoding="utf-8")
    total = 0
    for sub, pages in SUBS.items():
        before = None; got = 0
        for p in range(pages):
            params = {"subreddit": sub, "limit": 100, "sort": "desc"}
            if before is not None: params["before"] = before
            data = fetch(params)
            if not data: print(sub, "stop page", p, flush=True); break
            for post in data:
                out.write(json.dumps({k: post.get(k) for k in FIELDS}, ensure_ascii=False) + "\n")
            out.flush(); got += len(data); total += len(data)
            before = min(x["created_utc"] for x in data)
            print(f"{sub} page {p+1} total {got}", flush=True)
            if len(data) < 100: break
            time.sleep(1.5)
    out.close()
    print("WAVE3 DONE total", total)

if __name__ == "__main__":
    main()
