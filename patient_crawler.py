#!/usr/bin/env python3
"""Patient.info community (Discourse) - Mental health category, public JSON API.
Lists category topics, keeps depression-relevant ones by title keywords,
fetches full topic posts (HTML stripped). Output: data/patient_topics.jsonl,
data/patient_posts.jsonl. Category id 25, ~37.6k topics total.
"""
import json, time, os, re
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
B = "https://community.patient.info"
LIST_PAGES = 120        # 30 topics/page -> 3600 topics scanned
MAX_TOPICS = 1600       # full-thread fetches cap
DEP_KW = ["depress", "low mood", "anhedonia", "sertraline", "fluoxetine", "citalopram",
          "venlafaxine", "mirtazapine", "prozac", "zoloft", "lexapro", "antidepressant"]

def get_json(url, tries=4):
    for a in range(tries):
        try:
            r = requests.get(url, headers=H, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code == 429: time.sleep(10 * (a + 1)); continue
        except Exception: pass
        time.sleep(3 * (a + 1))
    return None

def strip(html):
    t = re.sub(r"<br\s*/?>", "\n", html or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def main():
    topics = []
    for page in range(LIST_PAGES):
        j = get_json(f"{B}/c/25.json?page={page}")
        if not j: print("list stop", page); break
        ts = (j.get("topic_list") or {}).get("topics") or []
        if not ts: break
        for t in ts:
            title = (t.get("title") or "").lower()
            if any(k in title for k in DEP_KW):
                topics.append({"id": t["id"], "title": t.get("title"), "posts_count": t.get("posts_count"),
                               "views": t.get("views"), "created_at": t.get("created_at"),
                               "url": f"{B}/t/{t['id']}"})
        if page % 20 == 0: print("list page", page, "kept topics", len(topics))
        time.sleep(0.8)
    topics = topics[:MAX_TOPICS]
    with open(os.path.join(DATA, "patient_topics.jsonl"), "w", encoding="utf-8") as f:
        for t in topics: f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print("TOPICS", len(topics))
    nposts = 0
    with open(os.path.join(DATA, "patient_posts.jsonl"), "w", encoding="utf-8") as f:
        for i, t in enumerate(topics):
            j = get_json(f"{B}/t/{t['id']}.json")
            if not j: continue
            for p in (j.get("post_stream") or {}).get("posts") or []:
                text = strip(p.get("cooked"))
                if len(text) < 10: continue
                f.write(json.dumps({"topic_id": t["id"], "topic_title": t["title"],
                                    "username": p.get("username"), "post_number": p.get("post_number"),
                                    "created_at": p.get("created_at"), "text": text},
                                   ensure_ascii=False) + "\n")
                nposts += 1
            if i % 100 == 0: print("topic", i, "posts", nposts)
            time.sleep(0.6)
    print("POSTS", nposts)

if __name__ == "__main__":
    main()
