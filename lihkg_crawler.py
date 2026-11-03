#!/usr/bin/env python3
"""LIHKG (連登) via public api_v2 (guest, unsigned worked 2026-11-03).
Search depression keywords -> thread ids -> all pages' posts.
"""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Referer": "https://lihkg.com/"}
API = "https://lihkg.com/api_v2"
KEYWORDS = ["抑鬱", "抑鬱症", "情緒病", "焦慮症", "抑郁"]
MAX_THREADS = 400

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(path, params=None, tries=3):
    for a in range(tries):
        try:
            r = requests.get(API + path, params=params, headers=H, timeout=25)
            if r.status_code == 200:
                j = r.json()
                if j.get("success") == 1: return j.get("response") or {}
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    threads = {}
    for kw in KEYWORDS:
        for page in range(1, 11):
            resp = get("/thread/search", {"q": kw, "page": page, "count": 50, "sort": "desc_create_time"})
            items = (resp or {}).get("items") or []
            if not items: break
            for it in items:
                tid = it.get("thread_id")
                if tid and tid not in threads:
                    threads[tid] = {"title": it.get("title"), "total_page": it.get("total_page") or 1,
                                    "kw": kw, "reply_count": it.get("no_of_reply")}
            print(kw, "page", page, "threads", len(threads), flush=True)
            time.sleep(0.4)
    items = list(threads.items())[:MAX_THREADS]
    print("fetching", len(items), "threads", flush=True)
    cnt = {"t": 0, "p": 0}

    def work(kv):
        tid, meta = kv
        rows = []
        for p in range(1, min(meta["total_page"], 40) + 1):
            resp = get(f"/thread/{tid}/page/{p}")
            if not resp: break
            for m in resp.get("item_data") or resp.get("items") or []:
                body = strip(m.get("msg"))
                if len(body) >= 4:
                    rows.append({"id": f"{tid}:{m.get('post_id')}", "thread_id": tid,
                                 "title": meta["title"], "post_no": m.get("msg_num"),
                                 "text": body, "kw": meta["kw"]})
            time.sleep(0.15)
        if rows:
            with open(os.path.join(DATA, "lihkg_posts.jsonl"), "a", encoding="utf-8") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 40 == 0: print("threads", cnt["t"], "posts", cnt["p"], flush=True)

    p = os.path.join(DATA, "lihkg_posts.jsonl")
    if os.path.exists(p): os.remove(p)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, items))
    print("LIHKG DONE", cnt)

if __name__ == "__main__":
    main()
