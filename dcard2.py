#!/usr/bin/env python3
"""Dcard top-up (was run inline 2026-11-03; archived for reproducibility).
Forum feeds (mood/relationships/job/health) -> local keyword filter -> full post fetch.
Added 295 posts (total Dcard 360)."""
import requests, json, time, os
from concurrent.futures import ThreadPoolExecutor

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
API = "https://www.dcard.tw/service/api/v2"
BASE = os.path.dirname(os.path.abspath(__file__))
KEEP = ("憂鬱", "抑郁", "焦慮", "想死", "失眠", "情緒", "崩潰", "吃藥", "看醫生", "心理", "壓力", "活著", "人生", "低落")

def get(path, params=None, tries=3):
    for a in range(tries):
        try:
            r = requests.get(API + path, params=params, headers=H, timeout=25)
            if r.status_code == 200: return r.json()
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    cand = {}
    for forum in ["mood", "relationships", "job", "health"]:
        before = None
        for rnd in range(50):
            params = {"popular": "false", "limit": 30}
            if before: params["before"] = before
            items = get(f"/forums/{forum}/posts", params)
            if not items: break
            for it in items:
                blob = (it.get("title") or "") + " " + (it.get("excerpt") or "")
                pid = it.get("id")
                if pid and pid not in cand and any(k in blob for k in KEEP):
                    cand[pid] = {"id": pid, "title": it.get("title"), "forum": forum, "created": it.get("createdAt")}
            before = items[-1].get("id")
            if len(items) < 30: break
            time.sleep(0.3)
    have = set()
    p = os.path.join(BASE, "data/dcard_posts.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            try: have.add(json.loads(l)["id"])
            except Exception: pass
    todo = [c for c in cand.values() if c["id"] not in have][:600]
    cnt = {"n": 0}
    def work(c):
        j = get(f"/posts/{c['id']}")
        if not j: return
        content = (j.get("content") or "").strip()
        if len(content) < 30: return
        row = dict(c); row["text"] = content
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        cnt["n"] += 1
    with ThreadPoolExecutor(max_workers=6) as ex: list(ex.map(work, todo))
    print("DCARD2 DONE added", cnt["n"])

if __name__ == "__main__":
    main()
