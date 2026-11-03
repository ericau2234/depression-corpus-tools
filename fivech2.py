#!/usr/bin/env python3
"""5ch メンタルヘルス board (mevius.5ch.io/utu): subject.txt -> top threads -> .dat files (Shift-JIS).
One row per post. Guest access.
"""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
import sys
B = sys.argv[1] if len(sys.argv) > 1 else "https://mevius.5ch.io/utu"
TAG = B.rstrip("/").split("/")[-1]
TOP_THREADS = 160

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get_sjis(url, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.content.decode("shift_jis", errors="ignore")
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    subj = get_sjis(f"{B}/subject.txt")
    threads = []
    for line in (subj or "").splitlines():
        m = re.match(r"(\d+)\.dat<>(.*)\((\d+)\)\s*$", line.strip())
        if m:
            threads.append((m.group(1), strip(m.group(2)), int(m.group(3))))
    threads.sort(key=lambda x: x[2], reverse=True)
    print("threads on board:", len(threads), "taking top", TOP_THREADS, flush=True)
    threads = threads[:TOP_THREADS]
    cnt = {"t": 0, "p": 0}

    def work(t):
        tid, title, _ = t
        dat = get_sjis(f"{B}/dat/{tid}.dat")
        if not dat: return
        rows = []
        for i, line in enumerate(dat.splitlines()):
            parts = line.split("<>")
            if len(parts) < 4: continue
            body = strip(parts[3])
            if len(body) < 8: continue
            rows.append({"id": f"{tid}:{i+1}", "thread_id": tid, "thread_title": title,
                         "post_no": i + 1, "text": body})
        with open(os.path.join(DATA, "fivech_" + TAG + "_posts.jsonl"), "a", encoding="utf-8") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 20 == 0: print("threads", cnt["t"], "posts", cnt["p"], flush=True)

    p = os.path.join(DATA, "fivech_" + TAG + "_posts.jsonl")
    if os.path.exists(p): os.remove(p)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, threads))
    print("5CH DONE", cnt)

if __name__ == "__main__":
    main()
