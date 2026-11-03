#!/usr/bin/env python3
"""Threads harvest via threads-cli search. Clinical single words (depression/
anxiety/sad) return empty on this account; phrase queries (mental health,
therapy, can't sleep...) return posts. Bounded calls, sleeps between, stops
on rate limit. Output: data/threads_posts.jsonl {id, author, title:'', text, url, query}"""
import subprocess, json, time, os, sys

ACC = "17841480021852855"
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data/threads_posts.jsonl")
QUERIES = ["mental health", "therapy", "can't sleep", "feeling sad", "struggling",
           "overwhelmed", "burnout", "insomnia", "lonely", "grief", "tired of everything",
           "no motivation", "feel empty", "my anxiety journey", "mental health matters"]

def search(q, after=None):
    cmd = ["/opt/hatch/bin/threads-cli", "search", "--account-id", ACC,
           "--query", q, "--first", "50"]
    if after: cmd += ["--after", after]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if "Rate Limit" in (r.stdout + r.stderr):
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

def walk_posts(d):
    posts = []
    sr = ((d or {}).get("data") or {}).get("searchResults") or {}
    for e in sr.get("edges") or []:
        th = ((e.get("node") or {}).get("thread")) or {}
        for ti in th.get("thread_items") or []:
            p = ti.get("post") or {}
            cap = ((p.get("caption") or {}).get("text")) or ""
            user = ((p.get("user") or {}).get("username")) or ""
            code = p.get("code")
            pid = p.get("id") or p.get("pk") or code
            if cap and pid:
                posts.append({"id": f"th:{pid}", "author": user, "title": "",
                              "text": cap,
                              "url": f"https://www.threads.com/@{user}/post/{code}" if code else None})
    pi = sr.get("page_info") or {}
    return posts, (pi.get("end_cursor") if pi.get("has_next_page") else None)

def main():
    seen = set()
    if os.path.exists(OUT):
        for l in open(OUT, encoding="utf-8"):
            try: seen.add(json.loads(l)["id"])
            except Exception: pass
    total = len(seen)
    out = open(OUT, "a", encoding="utf-8")
    for q in QUERIES:
        after = None
        for page in range(2):
            d = search(q, after)
            if d is None:
                print("RATE LIMITED, stop"); out.close(); return
            posts, after = walk_posts(d)
            n0 = 0
            for p in posts:
                if p["id"] in seen: continue
                seen.add(p["id"]); p["query"] = q
                out.write(json.dumps(p, ensure_ascii=False) + "\n"); n0 += 1; total += 1
            out.flush()
            print(f"{q} page{page}: {len(posts)} posts, {n0} new (total {total})", flush=True)
            if not after: break
            time.sleep(3)
        time.sleep(3)
    out.close()
    print("THREADS HARVEST DONE", total)

if __name__ == "__main__":
    main()
