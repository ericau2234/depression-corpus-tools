#!/usr/bin/env python3
"""PsychForums (phpBB-based) Clinical Depression forum: list pages -> topics -> posts (page 1)."""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
B = "https://www.psychforums.com"
LIST_PAGES = 60
MAX_TOPICS = 800

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
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
    topics = {}
    for p in range(1, LIST_PAGES + 1):
        url = f"{B}/depression/" if p == 1 else f"{B}/depression/page{p}.html"
        txt = get(url)
        if not txt:
            url = f"{B}/depression/index{p}.html"; txt = get(url)
        if not txt: break
        found = re.findall(r'href="(/[a-z0-9\-]+/topic\d+\.html)', txt)
        new = 0
        for f in found:
            tid = re.search(r"topic(\d+)", f).group(1)
            if tid not in topics: topics[tid] = B + f; new += 1
        print("list page", p, "topics", len(topics), flush=True)
        if new == 0 and p > 3: break
        time.sleep(0.4)
    items = list(topics.items())[:MAX_TOPICS]
    print("fetching", len(items), "topics", flush=True)
    cnt = {"t": 0, "p": 0}

    def work(kv):
        tid, url = kv
        txt = get(url)
        if not txt: return
        tm = re.search(r"<title>(.*?)</title>", txt, re.S)
        title = strip(tm.group(1)).split(" - ")[0] if tm else ""
        bodies = re.findall(r'<div class="content">(.*?)</div>\s*</div>', txt, re.S) or \
                 re.findall(r'<div class="content">(.*?)</div>', txt, re.S)
        rows = []
        for i, b in enumerate(bodies):
            body = strip(b)
            if len(body) >= 30:
                rows.append({"id": f"{tid}:{i+1}", "topic_id": tid, "title": title, "text": body, "url": url})
        if rows:
            with open(os.path.join(DATA, "psychforums_posts.jsonl"), "a", encoding="utf-8") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 100 == 0: print("topics", cnt["t"], "posts", cnt["p"], flush=True)

    p = os.path.join(DATA, "psychforums_posts.jsonl")
    if os.path.exists(p): os.remove(p)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, items))
    print("PSYCHFORUMS DONE", cnt)

if __name__ == "__main__":
    main()
