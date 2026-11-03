#!/usr/bin/env python3
"""Patient.info topic fetch, parallel version (resumes from patient_posts.jsonl).
6 workers, per-request 429-aware exponential backoff. Appends new posts.
"""
import json, os, re, time, threading
import requests
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
B = "https://community.patient.info"
WORKERS = 6
lock = threading.Lock()
counter = {"done": 0, "posts": 0}

def strip(html):
    t = re.sub(r"<br\s*/?>", "\n", html or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def get_json(url, tries=6):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code in (429, 502, 503): time.sleep(min(30, 2 ** a * 2)); continue
            return None
        except Exception:
            time.sleep(2 * (a + 1))
    return None

def main():
    topics = [json.loads(l) for l in open(os.path.join(DATA, "patient_topics.jsonl"), encoding="utf-8")]
    done = set()
    ppath = os.path.join(DATA, "patient_posts.jsonl")
    if os.path.exists(ppath):
        for l in open(ppath, encoding="utf-8"):
            try: done.add(json.loads(l)["topic_id"])
            except Exception: pass
    todo = [t for t in topics if t["id"] not in done]
    print("topics total", len(topics), "already done", len(done), "todo", len(todo), flush=True)
    out = open(ppath, "a", encoding="utf-8")

    def work(t):
        j = get_json(f"{B}/t/{t['id']}.json")
        rows = []
        if j:
            for p in (j.get("post_stream") or {}).get("posts") or []:
                text = strip(p.get("cooked"))
                if len(text) >= 10:
                    rows.append({"topic_id": t["id"], "topic_title": t["title"],
                                 "username": p.get("username"), "post_number": p.get("post_number"),
                                 "created_at": p.get("created_at"), "text": text})
        with lock:
            for r in rows: out.write(json.dumps(r, ensure_ascii=False) + "\n")
            out.flush()
            counter["done"] += 1; counter["posts"] += len(rows)
            if counter["done"] % 50 == 0:
                print("done", counter["done"], "posts", counter["posts"], flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))
    out.close()
    print("PARALLEL DONE, new posts", counter["posts"])

if __name__ == "__main__":
    main()
