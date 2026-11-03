#!/usr/bin/env python3
"""DC Inside (Korea) galleries: depression + psychology. Guest-readable HTML.
List pages -> post ids -> view pages, 6 parallel workers. Skips notice posts.
"""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
     "Accept-Language": "ko-KR,ko;q=0.9", "Referer": "https://gall.dcinside.com/"}
GALLERIES = ["depression", "psychology"]
PAGES = 40
SKIP_SUBJ = ("안내", "공지", "필독")

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get(url, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.text
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    targets = []
    for g in GALLERIES:
        seen = set()
        for p in range(1, PAGES + 1):
            txt = get(f"https://gall.dcinside.com/board/lists/?id={g}&page={p}")
            if not txt: break
            nos = re.findall(rf'/board/view/\?id={g}&no=(\d+)', txt)
            new = [n for n in dict.fromkeys(nos) if n not in seen and n != "1"]
            seen.update(new)
            print(g, "page", p, "posts total", len(seen), flush=True)
            if not new: break
            time.sleep(0.5)
        targets += [(g, n) for n in seen]
    print("fetching", len(targets), "posts", flush=True)
    cnt = {"n": 0}

    def work(t):
        g, no = t
        txt = get(f"https://gall.dcinside.com/board/view/?id={g}&no={no}")
        if not txt: return
        sm = re.search(r'class="title_subject"[^>]*>(.*?)</', txt, re.S)
        subj = strip(sm.group(1)) if sm else ""
        if any(k in subj for k in SKIP_SUBJ): return
        bm = re.search(r'class="write_div"[^>]*>(.*?)<div class="btn_wrap', txt, re.S)
        body = strip(bm.group(1)) if bm else ""
        if len(body) < 20: return
        row = {"id": f"{g}:{no}", "gallery": g, "title": subj, "text": body,
               "url": f"https://gall.dcinside.com/board/view/?id={g}&no={no}"}
        with open(os.path.join(DATA, "dcinside_posts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        cnt["n"] += 1
        if cnt["n"] % 100 == 0: print("posts done", cnt["n"], flush=True)

    if os.path.exists(os.path.join(DATA, "dcinside_posts.jsonl")):
        os.remove(os.path.join(DATA, "dcinside_posts.jsonl"))
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, targets))
    print("DCINSIDE DONE", cnt["n"])

if __name__ == "__main__":
    main()
