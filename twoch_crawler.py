#!/usr/bin/env python3
"""2ch.hk /psy/ board (Russian): catalog.json -> thread JSON -> posts. Guest JSON API."""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
B = "https://2ch.hk/psy"

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def get_json(url, tries=3):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.json()
            time.sleep(2 * (a + 1))
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    cat = get_json(f"{B}/catalog.json")
    threads = (cat or {}).get("threads") or []
    print("threads:", len(threads), flush=True)
    cnt = {"t": 0, "p": 0}

    def work(t):
        num = t.get("num")
        j = get_json(f"{B}/res/{num}.json")
        if not j: return
        rows = []
        for th in j.get("threads") or []:
            title = strip((th.get("posts") or [{}])[0].get("subject") or "")
            for p in th.get("posts") or []:
                body = strip(p.get("comment"))
                if len(body) >= 8:
                    rows.append({"id": f"{num}:{p.get('num')}", "thread_id": str(num),
                                 "title": title, "text": body})
        if rows:
            with open(os.path.join(DATA, "twoch_posts.jsonl"), "a", encoding="utf-8") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 40 == 0: print("threads", cnt["t"], "posts", cnt["p"], flush=True)

    p = os.path.join(DATA, "twoch_posts.jsonl")
    if os.path.exists(p): os.remove(p)
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(work, threads))
    print("2CH DONE", cnt)

if __name__ == "__main__":
    main()
