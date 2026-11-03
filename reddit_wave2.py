#!/usr/bin/env python3
"""Reddit wave 2: more depression-adjacent subreddits via Arctic-Shift listing pagination.
Sequential (archive server times out under concurrency). Resumable per subreddit page cap.
Output: reddit_wave2.jsonl
"""
import requests, json, os, time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
API = "https://arctic-shift.photon-reddit.com/api/posts/search"
H = {"User-Agent": "research-corpus/1.0"}
SUBS = {"socialanxiety": 80, "lonely": 80, "insomnia": 60, "GriefSupport": 60,
        "ptsd": 60, "CPTSD": 60, "mentalhealthsupport": 60, "bipolar": 50,
        "BPD": 40, "depression_memes": 0, "Anxietyhelp": 40, "selfharm": 0}
FIELDS = ["id", "subreddit", "author", "title", "selftext", "score", "num_comments", "created_utc", "url"]

def fetch(params, tries=6):
    for a in range(tries):
        try:
            r = requests.get(API, params=params, headers=H, timeout=60)
            if r.status_code == 200:
                return (r.json().get("data") or [])
            time.sleep(4 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def main():
    import sys
    shard = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    nshards = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    items = list(SUBS.items())[shard::nshards]
    suffix = f"_{shard}" if nshards > 1 else ""
    out = open(os.path.join(DATA, f"reddit_wave2{suffix}.jsonl"), "w", encoding="utf-8")
    total = 0
    for sub, pages in items:
        if pages == 0: continue
        before = None; got = 0
        for p in range(pages):
            params = {"subreddit": sub, "limit": 100, "sort": "desc"}
            if before is not None: params["before"] = before
            data = fetch(params)
            if not data: print(sub, "stop page", p, flush=True); break
            for post in data:
                out.write(json.dumps({k: post.get(k) for k in FIELDS}, ensure_ascii=False) + "\n")
            out.flush()
            got += len(data); total += len(data)
            before = min(x["created_utc"] for x in data)
            print(f"{sub} page {p+1} total {got}", flush=True)
            if len(data) < 100: break
            time.sleep(1.5)
    out.close()
    print("WAVE2 REDDIT DONE total", total)

if __name__ == "__main__":
    main()
