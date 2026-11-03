#!/usr/bin/env python3
"""Reddit DEEP trawl (eric 2026-11-03: 百万/千万级). Window-sharded by (sub, year, mode).
Usage: reddit_deep2.py <shard> <nshards>
Each task writes data/deep2/<mode>_<sub>_<year>.jsonl + a .done marker; workers skip
done tasks, so a killed run resumes by relaunching the same command.
"""
import json, time, os, sys
import requests
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUTDIR = os.path.join(DATA, "deep2")
os.makedirs(OUTDIR, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

SUBS = ["depression", "mentalhealth", "offmychest", "trueoffmychest", "relationship_advice",
        "antiwork", "povertyfinance", "raisedbynarcissists", "GriefSupport", "lonely",
        "confessions", "Anxiety", "vent", "self", "divorce", "breakups", "stopdrinking",
        "ChronicPain", "insomnia", "socialanxiety", "parenting", "jobs", "debtfree",
        "StudentLoans", "widowers"]
YEARS = list(range(2017, 2027))
PAGES_CAP = 2500  # 250k items per window ceiling; empty-stop ends most windows far earlier

def epoch(y, m=1):
    return int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())

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

def run_task(mode, sub, year):
    tag = f"{mode}_{sub}_{year}"
    out_path = os.path.join(OUTDIR, tag + ".jsonl")
    done_path = os.path.join(OUTDIR, tag + ".done")
    if os.path.exists(done_path):
        return
    url = f"https://arctic-shift.photon-reddit.com/api/{mode}/search"
    seen = set()
    min_seen_utc = None
    if os.path.exists(out_path):
        for l in open(out_path, encoding="utf-8"):
            try:
                d = json.loads(l); seen.add(d["id"])
                cu = d.get("created_utc")
                if cu and (min_seen_utc is None or cu < min_seen_utc): min_seen_utc = cu
            except Exception: pass
    total = len(seen)
    lo, hi = epoch(year), epoch(year + 1)
    # RESUME FIX: harvest descends newest->oldest contiguously, so everything
    # >= min_seen_utc is already captured; continue from there instead of
    # re-walking the whole window from the top.
    before = min_seen_utc if min_seen_utc else hi
    with open(out_path, "a", encoding="utf-8") as f:
        for page in range(PAGES_CAP):
            params = {"subreddit": sub, "limit": 100, "sort": "desc",
                      "after": lo, "before": before}
            rows = fetch(url, params)
            if not rows:
                # throttle-empty vs true exhaustion: confirm with slow retries
                for _ in range(3):
                    time.sleep(30)
                    rows = fetch(url, params)
                    if rows: break
                if not rows:
                    break
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
            if page % 20 == 0:
                print(tag, "page", page, "total", total, flush=True)
            if len(rows) < 100:
                break
            time.sleep(0.5)
    with open(done_path, "w") as f:
        f.write(str(total))
    print("TASK DONE", tag, total, flush=True)

def main():
    shard, nsh = int(sys.argv[1]), int(sys.argv[2])
    tasks = [(m, s, y) for s in SUBS for y in YEARS for m in ("posts", "comments")]
    mine = [t for i, t in enumerate(tasks) if i % nsh == shard]
    print(f"worker {shard}/{nsh}: {len(mine)} tasks", flush=True)
    for (m, s, y) in mine:
        run_task(m, s, y)
    print("WORKER DONE", shard, flush=True)

if __name__ == "__main__":
    main()
