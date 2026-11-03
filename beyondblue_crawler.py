#!/usr/bin/env python3
"""Beyond Blue forums (Australia, Khoros) via public LiQL API (api/2.0/search).
Boards: Depression c1-sc2-b2, Anxiety c1-sc2-b1, PTSD c1-sc2-b3, Grief c1-sc4-b4,
Relationship/family c1-sc3-b3, Treatments c1-sc3-b2. (Suicidal-thoughts board excluded by scope.)
"""
import requests, re, os, json, time, html
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
API = "https://forums.beyondblue.org.au/api/2.0/search"
BOARDS = {"c1-sc2-b2": 20000, "c1-sc2-b1": 10000, "c1-sc2-b3": 6000,
          "c1-sc4-b4": 4000, "c1-sc3-b3": 4000, "c1-sc3-b2": 4000}
PAGE = 500

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def query(qstr, tries=4):
    for a in range(tries):
        try:
            r = requests.get(API, params={"q": qstr}, headers=H, timeout=40)
            if r.status_code == 200:
                j = r.json()
                if j.get("status") == "success":
                    return (j.get("data") or {}).get("items") or []
            time.sleep(3 * (a + 1))
        except Exception:
            time.sleep(3 * (a + 1))
    return None

def run(board, cap):
    out, offset = [], 0
    while len(out) < cap:
        q = (f"SELECT id, subject, body, post_time FROM messages "
             f"WHERE board.id = '{board}' LIMIT {PAGE} OFFSET {offset}")
        items = query(q)
        if not items: break
        for m in items:
            body = strip(m.get("body"))
            if len(body) >= 20:
                out.append({"id": f"bb:{m.get('id')}", "board": board,
                            "title": strip(m.get("subject")), "text": body,
                            "created": m.get("post_time")})
        offset += len(items)
        print(board, "fetched", len(out), flush=True)
        if len(items) < PAGE: break
        time.sleep(0.4)
    return out

def main():
    total = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(run, b, c): b for b, c in BOARDS.items()}
        for f in futs:
            total.extend(f.result())
    with open(os.path.join(DATA, "beyondblue_posts.jsonl"), "w", encoding="utf-8") as fo:
        for r in total: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("BEYOND BLUE DONE", len(total))

if __name__ == "__main__":
    main()
