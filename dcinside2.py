#!/usr/bin/env python3
"""DC Inside v2: low concurrency (2 workers + delay) — v1's 6-way burst got every
view request refused (list phase is sequential and worked; regex verified fine manually).
Logs failure status codes instead of swallowing them."""
import requests, re, os, json, time, html, threading
from concurrent.futures import ThreadPoolExecutor

BASE = "https://gall.dcinside.com"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Referer": "https://gall.dcinside.com/"}
GALLERIES = ["depression", "psychology"]
PAGES = 40
lock = threading.Lock()
cnt = {"n": 0, "fail": {}}

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or ""); t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(url, tries=5):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.text
            with lock: cnt["fail"][r.status_code] = cnt["fail"].get(r.status_code, 0) + 1
            time.sleep(3 * (a + 1))
        except Exception as e:
            with lock: cnt["fail"][type(e).__name__] = cnt["fail"].get(type(e).__name__, 0) + 1
            time.sleep(3 * (a + 1))
    return None

def main():
    posts = []
    for gal in GALLERIES:
        seen = set()
        for page in range(1, PAGES + 1):
            txt = get(f"{BASE}/board/lists/?id={gal}&page={page}")
            if not txt: break
            for m in re.finditer(r'board/view/\?id=' + gal + r'&no=(\d+)', txt):
                no = m.group(1)
                if no in seen: continue
                seen.add(no)
                tm = re.search(r'<a href="[^"]*no=' + no + r'[^"]*"[^>]*>(.*?)</a>', txt, re.S)
                title = strip(tm.group(1)) if tm else ""
                if any(k in title for k in ("안내", "공지", "필독")): continue
                posts.append((gal, no, title))
            print(gal, "page", page, "posts total", len(posts), flush=True)
            time.sleep(0.4)
    print("fetching", len(posts), "posts", flush=True)

    def work(item):
        gal, no, title = item
        txt = get(f"{BASE}/board/view/?id={gal}&no={no}")
        if not txt: return
        m = re.search(r'class="write_div"[^>]*>(.*?)<div class="comment_wrap', txt, re.S) or \
            re.search(r'<div class="write_div"[^>]*>(.*?)</div>\s*</div>', txt, re.S)
        if not m: return
        body = strip(m.group(1))
        if len(body) < 30: return
        row = {"id": f"{gal}:{no}", "gallery": gal, "title": title, "text": body,
               "url": f"{BASE}/board/view/?id={gal}&no={no}"}
        with lock:
            with open(os.path.join(DATA, "dcinside_posts.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            cnt["n"] += 1
            if cnt["n"] % 100 == 0: print("fetched", cnt["n"], "fails", cnt["fail"], flush=True)
        time.sleep(0.25)

    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, posts))
    print("DCINSIDE2 DONE", cnt["n"], "fails", cnt["fail"])

if __name__ == "__main__":
    main()
