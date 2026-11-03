#!/usr/bin/env python3
"""Dcard (Taiwan) via public service API v2: search posts by keyword, local filter, fetch full content."""
import requests, os, json, time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
API = "https://www.dcard.tw/service/api/v2"
QUERIES = ["憂鬱症", "憂鬱", "焦慮症", "想死", "失眠"]
KEEP = ("憂鬱", "抑郁", "焦慮", "想死", "失眠", "情緒", "压力", "壓力", "崩潰", "藥物", "看醫生", "心理")
MAX_KEEP = 900

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
    for q in QUERIES:
        before = None
        for rnd in range(12):
            params = {"query": q, "limit": 30}
            if before: params["before"] = before
            items = get("/search/posts", params)
            if not items: break
            new = 0
            for it in items:
                pid = it.get("id")
                blob = (it.get("title") or "") + " " + (it.get("excerpt") or "")
                if pid and pid not in cand and any(k in blob for k in KEEP):
                    cand[pid] = {"id": pid, "title": it.get("title"), "forum": (it.get("forumAlias") or ""),
                                 "excerpt": it.get("excerpt"), "created": it.get("createdAt")}
                    new += 1
            print(q, "round", rnd, "candidates", len(cand), flush=True)
            before = items[-1].get("id")
            if len(items) < 30: break
            time.sleep(0.4)
    items = list(cand.values())[:MAX_KEEP]
    print("fetching content for", len(items), flush=True)
    cnt = {"n": 0}

    def work(c):
        j = get(f"/posts/{c['id']}")
        if not j: return
        content = (j.get("content") or "").strip()
        if len(content) < 30: return
        row = dict(c); row["text"] = content
        with open(os.path.join(DATA, "dcard_posts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        cnt["n"] += 1
        if cnt["n"] % 100 == 0: print("done", cnt["n"], flush=True)

    p = os.path.join(DATA, "dcard_posts.jsonl")
    if os.path.exists(p): os.remove(p)
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, items))
    print("DCARD DONE", cnt["n"])

if __name__ == "__main__":
    main()
