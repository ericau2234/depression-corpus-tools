#!/usr/bin/env python3
"""Hilferuf.de (German XenForo self-help forum): public node listings -> thread first posts.
Nodes: ich(72), trauer/grief(70), therapie(85), leben(84), familie(63).
"""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
B = "https://www.hilferuf.de"
NODES = ["ich.72", "trauer.70", "therapie.85", "leben.84", "familie.63"]
PAGES = 8
MAX_THREADS = 500

def get(url, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=25)
            if r.status_code == 200: return r.text
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def main():
    threads = {}
    for node in NODES:
        for p in range(1, PAGES + 1):
            url = f"{B}/forums/{node}/" + (f"page-{p}" if p > 1 else "")
            txt = get(url)
            if not txt: break
            found = re.findall(r'href="(/thema/[^"]+?\.\d+/)"', txt)
            new = 0
            for f in found:
                tid = f.rsplit(".", 1)[-1].strip("/")
                if tid not in threads:
                    threads[tid] = (node, B + f); new += 1
            print(node, "page", p, "threads total", len(threads), flush=True)
            if new == 0: break
            time.sleep(0.6)
    items = list(threads.items())[:MAX_THREADS]
    print("fetching", len(items), "threads", flush=True)
    out = open(os.path.join(DATA, "hilferuf_posts.jsonl"), "w", encoding="utf-8")
    cnt = {"n": 0}

    def work(kv):
        tid, (node, url) = kv
        txt = get(url)
        if not txt: return
        title_m = re.search(r"<title>(.*?)</title>", txt, re.S)
        title = strip(title_m.group(1)).replace(" | Hilferuf", "") if title_m else ""
        bodies = re.findall(r'<div class="bbWrapper">(.*?)</div>', txt, re.S)
        posts = [strip(b) for b in bodies if len(strip(b)) >= 30]
        if not posts: return
        row = {"id": tid, "node": node, "title": title, "text": posts[0],
               "replies_text": posts[1:4], "url": url}
        with open(os.path.join(DATA, "hilferuf_posts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        cnt["n"] += 1
        if cnt["n"] % 50 == 0: print("threads done", cnt["n"], flush=True)

    out.close()
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, items))
    print("HILFERUF DONE", cnt["n"])

if __name__ == "__main__":
    main()
