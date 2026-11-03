#!/usr/bin/env python3
"""Reddit BROAD wave (eric 2026-11-03: any subreddit, any emotional problem, trace money roots).
Usage: reddit_broad.py <shard> <nshards> <posts|comments>
Arctic-Shift listing pagination (before=oldest created_utc, sort=desc), sequential within
a sub, subs sharded across workers. Dedups against ids already in data/reddit_broad_*.jsonl.
"""
import json, time, os, sys
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

SUBS = [
    # mental-health core
    "depression", "mentalhealth", "Anxiety", "PTSD", "socialanxiety", "bipolar", "BPD",
    "schizophrenia", "insomnia", "ChronicPain", "chronicillness", "GriefSupport", "widowers",
    "emotionalneglect", "AdultChildren", "raisedbynarcissists", "estrangedadultkids",
    # venting / confession / loneliness
    "offmychest", "trueoffmychest", "confessions", "vent", "rant", "self", "MMFB",
    "lonely", "ForeverAlone", "socialskills", "KindVoice", "Advice", "needadvice",
    # work / money circumstances
    "antiwork", "jobs", "povertyfinance", "debtfree", "StudentLoans", "homeless",
    "almosthomeless", "disability", "CaregiverSupport",
    # relationships / family / life events
    "divorce", "breakups", "relationship_advice", "parenting",
    # addiction
    "stopdrinking", "AlAnon", "problemgambling",
    # school
    "college", "GradSchool",
    # non-English emotion subs
    "desabafos", "desabafo", "depresion", "depressionfr",
]
COMMENT_SUBS = ["depression", "mentalhealth", "offmychest", "trueoffmychest",
                "relationship_advice", "antiwork", "povertyfinance", "raisedbynarcissists",
                "GriefSupport", "lonely", "confessions", "Anxiety"]
POST_PAGES = 60      # up to 6,000 posts per sub
COMMENT_PAGES = 150  # up to 15,000 comments per sub

def fetch(url, params, tries=4):
    for a in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=60)
            if r.status_code == 200:
                return (r.json() or {}).get("data") or []
            print("http", r.status_code, flush=True)
        except Exception as e:
            print("net retry", a, type(e).__name__, flush=True)
        time.sleep(5 * (a + 1))
    return []

def main():
    shard, nsh, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    subs_all = SUBS if mode == "posts" else COMMENT_SUBS
    subs = [s for i, s in enumerate(subs_all) if i % nsh == shard]
    pages_cap = POST_PAGES if mode == "posts" else COMMENT_PAGES
    url = f"https://arctic-shift.photon-reddit.com/api/{mode}/search"
    out_path = os.path.join(DATA, f"reddit_broad_{mode}_{shard}.jsonl")
    seen = set()
    if os.path.exists(out_path):
        for l in open(out_path, encoding="utf-8"):
            try: seen.add(json.loads(l)["id"])
            except Exception: pass
    total = len(seen)
    print(f"shard {shard} mode {mode} subs {subs} resume {total}", flush=True)
    with open(out_path, "a", encoding="utf-8") as f:
        for sub in subs:
            before = None
            for page in range(pages_cap):
                params = {"subreddit": sub, "limit": 100, "sort": "desc"}
                if before: params["before"] = before
                rows = fetch(url, params)
                if not rows:
                    print(sub, "page", page, "empty stop", flush=True); break
                kept = 0
                for p in rows:
                    pid = p.get("id")
                    if not pid or pid in seen: continue
                    seen.add(pid)
                    if mode == "posts":
                        rec = {"id": pid, "subreddit": sub, "author": p.get("author"),
                               "title": p.get("title"), "selftext": p.get("selftext"),
                               "score": p.get("score"), "num_comments": p.get("num_comments"),
                               "created_utc": p.get("created_utc"),
                               "url": "https://www.reddit.com" + (p.get("permalink") or "")}
                    else:
                        rec = {"id": pid, "subreddit": sub, "author": p.get("author"),
                               "body": p.get("body"), "score": p.get("score"),
                               "link_id": p.get("link_id"), "created_utc": p.get("created_utc")}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n"); kept += 1; total += 1
                f.flush()
                before = min((p.get("created_utc") or 0) for p in rows)
                print(sub, "page", page, "kept", kept, "total", total, flush=True)
                time.sleep(1)
    print("SHARD DONE", shard, mode, total, flush=True)

if __name__ == "__main__":
    main()
