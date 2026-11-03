#!/usr/bin/env python3
"""Mastodon hashtag timelines (mastodon.social public API) + Lemmy communities.
Output: data/mastodon_posts.jsonl, data/lemmy_posts.jsonl
"""
import json, time, os, re
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

def strip(html):
    t = re.sub(r"<br\s*/?>", "\n", html or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def mastodon():
    out = []
    for tag in ["depression", "mentalhealth", "anxiety", "mentalhealthawareness"]:
        max_id = None
        for page in range(15):
            url = f"https://mastodon.social/api/v1/timelines/tag/{tag}?limit=40"
            if max_id: url += f"&max_id={max_id}"
            try:
                r = requests.get(url, headers=H, timeout=30)
                if r.status_code != 200: print("mastodon http", r.status_code, tag); break
                rows = r.json()
            except Exception as e:
                print("mastodon err", e); break
            if not rows: break
            for p in rows:
                text = strip(p.get("content"))
                if len(text) < 20: continue
                out.append({"id": p["id"], "tag": tag, "created_at": p.get("created_at"),
                            "lang": p.get("language"), "text": text, "url": p.get("url")})
            max_id = rows[-1]["id"]
            time.sleep(1.5)
        print("mastodon tag done", tag, "total", len(out))
    with open(os.path.join(DATA, "mastodon_posts.jsonl"), "w", encoding="utf-8") as f:
        for p in out: f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("MASTODON", len(out))

def lemmy():
    out = []
    for name in ["mentalhealth@lemmy.world", "depression_now@lemmy.world",
                 "mensmentalhealth@lemmy.world", "mentalhealthsupport@lemmy.world"]:
        try:
            r = requests.get("https://lemmy.world/api/v3/community", params={"name": name}, headers=H, timeout=25)
            cid = r.json()["community_view"]["community"]["id"]
        except Exception as e:
            print("lemmy resolve fail", name, e); continue
        for page in range(1, 21):
            try:
                r = requests.get("https://lemmy.world/api/v3/post/list",
                                 params={"community_id": cid, "sort": "New", "limit": 50, "page": page},
                                 headers=H, timeout=25)
                posts = r.json().get("posts") or []
            except Exception as e:
                print("lemmy list err", name, e); break
            if not posts: break
            for p in posts:
                post = p["post"]
                body = post.get("body") or ""
                out.append({"id": post["id"], "community": name, "title": post.get("name"),
                            "body": body, "score": p["counts"]["score"],
                            "comments": p["counts"]["comments"], "published": post.get("published"),
                            "url": post.get("ap_id")})
            time.sleep(1.0)
        print("lemmy done", name, "total", len(out))
    with open(os.path.join(DATA, "lemmy_posts.jsonl"), "w", encoding="utf-8") as f:
        for p in out: f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print("LEMMY", len(out))

if __name__ == "__main__":
    mastodon()
    lemmy()
