#!/usr/bin/env python3
"""PsychForums snowball deep pass (was run inline 2026-11-03; archived for reproducibility).
Seeds = topics from psychforums_posts.jsonl; fetches every topic's pages + harvests
related topic links. NOTE: PF serves page-1 content for every page number to guests,
so the 4,108 raw rows contained only 189 unique posts (exposed by cleaning dedup)."""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
B = "https://www.psychforums.com"
BASE = os.path.dirname(os.path.abspath(__file__))

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or ""); t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(url, tries=4):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.text
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    seeds = {}
    for l in open(os.path.join(BASE, "data/psychforums_posts.jsonl"), encoding="utf-8"):
        d = json.loads(l); seeds[d["topic_id"]] = d["url"]
    seen = set(seeds); queue = list(seeds.items())
    cnt = {"t": 0, "p": 0}
    def fetch_topic(tid, url):
        rows = []; links = set()
        base = url.rsplit(".html", 1)[0]
        for p in range(1, 31):
            u = url if p == 1 else f"{base}/page{p}.html"
            txt = get(u)
            if not txt: break
            for m in re.findall(r'href="(/[a-z0-9\-]+/topic(\d+)\.html)', txt):
                links.add((m[1], B + m[0]))
            bodies = re.findall(r'<div class="content">(.*?)</div>\s*</div>', txt, re.S) or \
                     re.findall(r'<div class="content">(.*?)</div>', txt, re.S)
            got = 0
            for b in bodies:
                body = strip(b)
                if len(body) >= 30:
                    rows.append({"id": f"{tid}:p{p}:{got}", "topic_id": tid, "title": "", "text": body, "url": u}); got += 1
            if got == 0 and p > 1: break
            time.sleep(0.15)
        return rows, links
    out = open(os.path.join(BASE, "data/psychforums_deep.jsonl"), "w", encoding="utf-8")
    while queue and cnt["t"] < 400:
        batch, queue = queue[:24], queue[24:]
        with ThreadPoolExecutor(max_workers=5) as ex:
            for rows, links in ex.map(lambda kv: fetch_topic(*kv), batch):
                for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
                out.flush(); cnt["p"] += len(rows)
                for tid2, url2 in links:
                    if tid2 not in seen: seen.add(tid2); queue.append((tid2, url2))
        cnt["t"] += len(batch)
        print("topics done", cnt["t"], "posts", cnt["p"], "queued", len(queue), flush=True)
    out.close(); print("PF DEEP DONE", cnt)

if __name__ == "__main__":
    main()
