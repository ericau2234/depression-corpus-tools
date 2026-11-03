#!/usr/bin/env python3
"""LiveJournal 'depression' community crawler (guest-public).
Phase 1: harvest entry URLs from ?skip=N listing pages.
Phase 2: fetch entries in parallel, extract entry body text.
Resumable: skips entry ids already in data/lj_posts.jsonl.
"""
import requests, re, os, json, time, html, sys
from concurrent.futures import ThreadPoolExecutor

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data/lj_posts.jsonl")
COMM = "https://depression.livejournal.com"
MAX_SKIP = int(sys.argv[1]) if len(sys.argv) > 1 else 60000

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(url, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.text
            if r.status_code == 404: return None
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    have = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: have.add(json.loads(l)["id"])
            except Exception: pass
    print("resume with", len(have), flush=True)
    # phase 1: harvest
    urls = {}
    years_done = set()
    state_f = os.path.join(BASE, "data/lj_urls.json")
    if os.path.exists(state_f):
        try:
            st = json.load(open(state_f))
            urls = {int(k): v for k, v in st["urls"].items()}
            years_done = set(st["years_done"])
            print("resume harvest state:", len(urls), "urls, years done", sorted(years_done), flush=True)
        except Exception as e:
            print("state load failed", e, flush=True)
    for year in range(2001, 2027):
        if year in years_done: continue
        for month in range(1, 13):
            if year == 2026 and month > 11: break
            txt = get(f"{COMM}/{year}/{month:02d}/")
            if not txt: continue
            ids = re.findall(r'depression\.livejournal\.com/(\d+)\.html', txt)
            for i in set(ids): urls.setdefault(i, f"{COMM}/{i}.html")
            if month == 12 or (year == 2026 and month == 11):
                print("harvest", year, "urls", len(urls), flush=True)
            time.sleep(0.3)
        years_done.add(year)
        json.dump({"urls": urls, "years_done": sorted(years_done)}, open(state_f, "w"))
    todo = [(i, u) for i, u in urls.items() if i not in have]
    print("harvested", len(urls), "to fetch", len(todo), flush=True)
    # phase 2: fetch entries
    cnt = {"n": 0}
    lock_out = open(OUT, "a", encoding="utf-8")
    def work(kv):
        eid, url = kv
        txt = get(url)
        if not txt: return
        m = re.search(r'<div class="aentry-post__text[^"]*"[^>]*>(.*?)</div>\s*<div class=" aentry-post__slot', txt, re.S) or \
            re.search(r'<div class="aentry-post__text[^"]*"[^>]*>(.*?)</div>', txt, re.S) or \
            re.search(r'<div class="entry-content"[^>]*>(.*?)</div>', txt, re.S)
        body = strip(m.group(1)) if m else ""
        tm = re.search(r"<title>(.*?)</title>", txt, re.S)
        title = strip(tm.group(1)) if tm else ""
        if len(body) >= 80:
            lock_out.write(json.dumps({"id": f"lj:{eid}", "title": title, "text": body, "url": url},
                                      ensure_ascii=False) + "\n")
            lock_out.flush(); cnt["n"] += 1
            if cnt["n"] % 500 == 0: print("fetched", cnt["n"], flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, todo))
    print("LJ DONE", cnt["n"])

if __name__ == "__main__":
    main()
