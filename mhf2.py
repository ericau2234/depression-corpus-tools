#!/usr/bin/env python3
"""MentalHealthForum.net (XenForo) Depression forum .366: 973 list pages; take first 120.
Thread page 1 posts via bbWrapper extraction."""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
B = "https://www.mentalhealthforum.net"
LIST_PAGES = 120

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
    threads = {}
    for p in range(1, LIST_PAGES + 1):
        url = f"{B}/forum/forums/depression-forum.366/" if p == 1 else f"{B}/forum/forums/depression-forum.366/page-{p}"
        txt = get(url)
        if not txt: break
        found = re.findall(r'href="(/forum/threads/[^"]+?\.(\d+)/)"', txt)
        for path, tid in found:
            if tid not in threads: threads[tid] = B + path
        print("list page", p, "threads", len(threads), flush=True)
        time.sleep(0.3)
    items = list(threads.items())
    print("fetching", len(items), "threads", flush=True)
    cnt = {"t": 0, "p": 0}

    def work(kv):
        tid, url = kv
        txt = get(url)
        if not txt: return
        tm = re.search(r"<title>(.*?)</title>", txt, re.S)
        title = strip(tm.group(1)).replace(" | Mental Health Forum", "") if tm else ""
        bodies = re.findall(r'<div class="bbWrapper">(.*?)</div>', txt, re.S)
        rows = []
        for i, b in enumerate(bodies):
            body = strip(b)
            if len(body) >= 30:
                rows.append({"id": f"{tid}:{i+1}", "thread_id": tid, "title": title, "text": body, "url": url})
        if rows:
            with open(os.path.join(DATA, "mhf_posts.jsonl"), "a", encoding="utf-8") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 100 == 0: print("threads", cnt["t"], "posts", cnt["p"], flush=True)

    p = os.path.join(DATA, "mhf_posts.jsonl")
    have = set()
    if os.path.exists(p):
        for l in open(p, encoding="utf-8"):
            try: have.add(json.loads(l)["thread_id"])
            except Exception: pass
    print("resume skip threads:", len(have), flush=True)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, [kv for kv in items if kv[0] not in have]))
    print("MHF DONE", cnt)

if __name__ == "__main__":
    main()
