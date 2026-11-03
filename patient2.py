#!/usr/bin/env python3
"""Patient.info wave2: whole 'Mental health' Discourse category (id 25,
37,593 topics / 305,246 posts at probe time). Phase 1 paginates /c/25.json
topic lists; phase 2 fetches /t/<id>.json posts, 6-parallel, resumable.
Cap via argv[1] (default 12000 topics, most recently active first)."""
import json, os, re, time, sys
import requests
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
B = "https://community.patient.info"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
CAP = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
OUT = os.path.join(DATA, "patient2_posts.jsonl")

def strip(t):
    t = re.sub(r"<br\s*/?>", "\n", t or "")
    t = re.sub(r"<[^>]+>", " ", t)
    import html as H2
    return re.sub(r"\s+", " ", H2.unescape(t)).strip()

def get_json(url, tries=6):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=40)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(10 * (a + 1)); continue
            time.sleep(3 * (a + 1))
        except Exception:
            time.sleep(3 * (a + 1))
    return None

def main():
    done = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: done.add(json.loads(l)["topic_id"])
            except Exception: pass
    print("resume done topics:", len(done), flush=True)
    topics = []
    page = 0
    while len(topics) < CAP:
        j = get_json(f"{B}/c/mental-health/25.json?page={page}")
        if not j: break
        tl = (j.get("topic_list") or {}).get("topics") or []
        if not tl: break
        for t in tl:
            topics.append({"id": t["id"], "title": t.get("title")})
        page += 1
        if page % 20 == 0: print("topics listed", len(topics), flush=True)
        time.sleep(0.3)
    todo = [t for t in topics if t["id"] not in done]
    print("topics total", len(topics), "todo", len(todo), flush=True)
    out = open(OUT, "a", encoding="utf-8")
    cnt = {"t": 0, "p": 0}
    def work(t):
        j = get_json(f"{B}/t/{t['id']}.json")
        if not j: return
        posts = ((j.get("post_stream") or {}).get("posts")) or []
        rows = []
        for p in posts:
            body = strip(p.get("cooked"))
            if len(body) >= 30:
                rows.append({"id": f"{t['id']}:{p.get('post_number')}", "topic_id": t["id"],
                             "title": t["title"], "text": body})
        if rows:
            for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
        cnt["t"] += 1; cnt["p"] += len(rows)
        if cnt["t"] % 500 == 0: print("topics done", cnt["t"], "posts", cnt["p"], flush=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, todo))
    print("PATIENT2 DONE", cnt)

if __name__ == "__main__":
    main()
