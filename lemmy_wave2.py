#!/usr/bin/env python3
"""Lemmy wave 2: depression communities on other instances (lemmy.ml, beehaw, lemmy.world)."""
import requests, json, os, time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "research-corpus/1.0"}
TARGETS = [("https://lemmy.ml", "depression"), ("https://lemmy.world", "depression"),
           ("https://beehaw.org", "mentalhealth"), ("https://beehaw.org", "depression"),
           ("https://lemmy.world", "mentalhealthsupport")]
PAGES = 25

def fetch_posts(inst, cid):
    rows, page = [], 1
    while page <= PAGES:
        try:
            r = requests.get(f"{inst}/api/v3/post/list",
                             params={"community_id": cid, "sort": "New", "limit": 50, "page": page},
                             headers=H, timeout=30)
            if r.status_code != 200: break
            posts = r.json().get("posts") or []
            if not posts: break
            for p in posts:
                post = p["post"]
                rows.append({"id": post.get("id"), "instance": inst,
                             "community": post.get("ap_id", ""), "title": post.get("name"),
                             "body": post.get("body") or "", "published": post.get("published"),
                             "url": post.get("ap_id")})
            page += 1; time.sleep(0.7)
        except Exception:
            break
    return rows

def run(t):
    inst, name = t
    try:
        r = requests.get(f"{inst}/api/v3/community", params={"name": name}, headers=H, timeout=25)
        if r.status_code != 200: return []
        cid = r.json()["community_view"]["community"]["id"]
        return fetch_posts(inst, cid)
    except Exception:
        return []

def main():
    total = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        for rows in ex.map(run, TARGETS):
            total.extend(rows)
            print("target done, cumulative", len(total), flush=True)
    with open(os.path.join(DATA, "lemmy_wave2.jsonl"), "w", encoding="utf-8") as f:
        for x in total: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("LEMMY WAVE2 DONE", len(total))

if __name__ == "__main__":
    main()
